"""
Unit tests for Import Operations.

Tests cover nivålista and lagerlogg import functionality.
"""

import pytest
import pandas as pd
from pathlib import Path

from operations.import_ops import (
    import_nivalista,
    import_lagerlogg,
    validate_import_file,
    get_import_summary,
    _convert_depth_to_path,  # Test depth-to-path conversion
)
from domain.exceptions import ImportValidationError, ValidationError


@pytest.fixture
def nivalista_file(tmp_path):
    """Create a test nivålista Excel file with depth integers (like real Excel files)."""
    file_path = tmp_path / "nivalista.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", "ART-002", "ART-003"],
        "Benämning": ["Artikel 1", "Artikel 2", "Artikel 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": [0, 1, 2],  # Depth integers: 0=top, 1=child, 2=grandchild
    })
    df.to_excel(file_path, index=False)
    return file_path


@pytest.fixture
def lagerlogg_file(tmp_path):
    """Create a test lagerlogg Excel file."""
    file_path = tmp_path / "lagerlogg.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", "ART-002", "ART-001"],
        "Chargenummer": ["CHARGE-A", "CHARGE-B", "CHARGE-C"],
        "Antal": [100.0, 50.0, 75.0],
        "Plats": ["Lager A", "Lager B", "Lager A"],
        "Batch": ["BATCH-1", "BATCH-2", "BATCH-3"],
    })
    df.to_excel(file_path, index=False)
    return file_path


def test_import_nivalista_success(nivalista_file):
    """Test successful nivålista import."""
    articles = import_nivalista(nivalista_file)

    assert len(articles) == 3
    assert articles[0]["article_number"] == "ART-001"
    assert articles[0]["description"] == "Artikel 1"
    assert articles[0]["quantity"] == 5.0
    assert articles[0]["level"] == "1"  # Depth 0 → path "1"
    assert articles[0]["parent_article"] is None  # Top-level has no parent
    assert articles[1]["level"] == "1.1"  # Depth 1 → path "1.1"
    assert articles[2]["level"] == "1.1.1"  # Depth 2 → path "1.1.1"


def test_import_nivalista_validates_file_exists(tmp_path):
    """Test that import validates file existence."""
    non_existent = tmp_path / "missing.xlsx"

    with pytest.raises(ValidationError):
        import_nivalista(non_existent)


def test_import_nivalista_validates_extension(tmp_path):
    """Test that import validates file extension."""
    wrong_extension = tmp_path / "file.txt"
    wrong_extension.touch()

    with pytest.raises(ValidationError):
        import_nivalista(wrong_extension)


def test_import_nivalista_skips_invalid_rows(tmp_path):
    """Test that invalid rows are skipped with warning."""
    file_path = tmp_path / "invalid_rows.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", "", "ART-003"],  # Empty article number
        "Benämning": ["Art 1", "Art 2", "Art 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": [0, 1, 1],  # Depth integers
    })
    df.to_excel(file_path, index=False)

    articles = import_nivalista(file_path)

    # Should skip the empty article number row
    assert len(articles) == 2
    assert articles[0]["article_number"] == "ART-001"
    assert articles[1]["article_number"] == "ART-003"


def test_import_nivalista_raises_if_no_valid_articles(tmp_path):
    """Test that import raises error if no valid articles found."""
    file_path = tmp_path / "all_invalid.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["", "", ""],
        "Benämning": ["Art 1", "Art 2", "Art 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": ["1", "2", "3"],
    })
    df.to_excel(file_path, index=False)

    with pytest.raises(ImportValidationError) as exc_info:
        import_nivalista(file_path)

    assert "Inga giltiga artiklar" in str(exc_info.value)


def test_import_lagerlogg_success(lagerlogg_file):
    """Test successful lagerlogg import."""
    inventory = import_lagerlogg(lagerlogg_file)

    assert len(inventory) == 3
    assert inventory[0]["article_number"] == "ART-001"
    assert inventory[0]["charge_number"] == "CHARGE-A"
    assert inventory[0]["quantity"] == 100.0
    assert inventory[0]["location"] == "Lager A"
    assert inventory[0]["batch_id"] == "BATCH-1"


def test_import_lagerlogg_validates_file_exists(tmp_path):
    """Test that lagerlogg import validates file existence."""
    non_existent = tmp_path / "missing.xlsx"

    with pytest.raises(ValidationError):
        import_lagerlogg(non_existent)


def test_import_lagerlogg_skips_invalid_rows(tmp_path):
    """Test that invalid rows are skipped."""
    file_path = tmp_path / "invalid_inventory.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", "", "ART-003"],  # Empty article
        "Chargenummer": ["CHG-A", "CHG-B", ""],  # Empty charge (allowed for admin posts)
        "Antal": [100.0, 50.0, 75.0],
        "Plats": ["A", "B", "C"],
        "Batch": ["1", "2", "3"],
    })
    df.to_excel(file_path, index=False)

    inventory = import_lagerlogg(file_path)

    # Should skip rows with missing article but allow empty charges
    assert len(inventory) == 2
    assert inventory[0]["article_number"] == "ART-001"
    assert inventory[0]["charge_number"] == "CHG-A"
    assert inventory[1]["article_number"] == "ART-003"
    assert inventory[1]["charge_number"] == ""  # Empty charge allowed


def test_import_lagerlogg_raises_if_no_valid_items(tmp_path):
    """Test that import raises error if no valid items found."""
    file_path = tmp_path / "all_invalid.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["", "", ""],
        "Chargenummer": ["", "", ""],
        "Antal": [100.0, 50.0, 75.0],
    })
    df.to_excel(file_path, index=False)

    with pytest.raises(ImportValidationError) as exc_info:
        import_lagerlogg(file_path)

    assert "Inga giltiga lagerloggar" in str(exc_info.value)


def test_validate_import_file_nivalista_success(nivalista_file):
    """Test validating a correct nivålista file."""
    result = validate_import_file(nivalista_file, expected_type="nivålista")
    assert result is True


def test_validate_import_file_lagerlogg_success(lagerlogg_file):
    """Test validating a correct lagerlogg file."""
    result = validate_import_file(lagerlogg_file, expected_type="lagerlogg")
    assert result is True


def test_get_import_summary_articles_only():
    """Test getting summary for articles only."""
    articles = [
        {"article_number": "ART-001", "quantity": 5.0, "level": "1"},
        {"article_number": "ART-002", "quantity": 10.0, "level": "1.1"},
        {"article_number": "ART-001", "quantity": 2.0, "level": "2"},
    ]

    summary = get_import_summary(articles=articles)

    assert summary["article_count"] == 3
    assert summary["unique_articles"] == 2  # ART-001, ART-002
    assert summary["total_quantity"] == 17.0
    assert summary["articles_with_level"] == 3


def test_get_import_summary_inventory_only():
    """Test getting summary for inventory only."""
    inventory = [
        {"article_number": "ART-001", "charge_number": "CHG-A", "quantity": 100.0},
        {"article_number": "ART-002", "charge_number": "CHG-B", "quantity": 50.0},
        {"article_number": "ART-001", "charge_number": "CHG-C", "quantity": 75.0},
    ]

    summary = get_import_summary(inventory=inventory)

    assert summary["inventory_count"] == 3
    assert summary["unique_charges"] == 3  # CHG-A, CHG-B, CHG-C
    assert summary["unique_articles_in_inventory"] == 2  # ART-001, ART-002
    assert summary["total_inventory_quantity"] == 225.0


def test_get_import_summary_both():
    """Test getting summary for both articles and inventory."""
    articles = [{"article_number": "ART-001", "quantity": 5.0, "level": "1"}]
    inventory = [{"article_number": "ART-001", "charge_number": "CHG-A", "quantity": 100.0}]

    summary = get_import_summary(articles=articles, inventory=inventory)

    assert "article_count" in summary
    assert "inventory_count" in summary


def test_import_nivalista_cleans_whitespace(tmp_path):
    """Test that import cleans whitespace from article data."""
    file_path = tmp_path / "whitespace.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["  ART-001  ", "ART-002"],
        "Benämning": ["  Artikel 1  ", "Artikel 2"],
        "Antal": [5.0, 10.0],
        "Nivå": [0, 1],  # Depth integers
    })
    df.to_excel(file_path, index=False)

    articles = import_nivalista(file_path)

    assert articles[0]["article_number"] == "ART-001"  # Trimmed
    assert articles[0]["description"] == "Artikel 1"  # Trimmed
    assert articles[0]["level"] == "1"  # Depth 0 → path "1"


def test_import_lagerlogg_cleans_whitespace(tmp_path):
    """Test that lagerlogg import cleans whitespace."""
    file_path = tmp_path / "whitespace.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["  ART-001  "],
        "Chargenummer": ["  CHG-A  "],
        "Antal": [100.0],
    })
    df.to_excel(file_path, index=False)

    inventory = import_lagerlogg(file_path)

    assert inventory[0]["article_number"] == "ART-001"  # Trimmed
    assert inventory[0]["charge_number"] == "CHG-A"  # Trimmed


def test_import_nivalista_preserves_sort_order(tmp_path):
    """Test that import preserves original row order from Excel file."""
    file_path = tmp_path / "ordered.xlsx"
    # Create DataFrame with specific order (NOT alphabetical)
    df = pd.DataFrame({
        "Artikelnummer": ["ZZZ-999", "AAA-001", "MMM-500", "BBB-002"],
        "Benämning": ["Last", "First", "Middle", "Second"],
        "Antal": [1.0, 2.0, 3.0, 4.0],
        "Nivå": [0, 1, 1, 1],  # Depth integers: 0=top, rest are children
    })
    df.to_excel(file_path, index=False)

    articles = import_nivalista(file_path)

    # Verify articles are in EXACT order from Excel, NOT sorted alphabetically
    assert len(articles) == 4
    assert articles[0]["article_number"] == "ZZZ-999"
    assert articles[0]["sort_order"] == 0
    assert articles[1]["article_number"] == "AAA-001"
    assert articles[1]["sort_order"] == 1
    assert articles[2]["article_number"] == "MMM-500"
    assert articles[2]["sort_order"] == 2
    assert articles[3]["article_number"] == "BBB-002"
    assert articles[3]["sort_order"] == 3


class TestConvertDepthToPath:
    """Test depth-to-path conversion for Excel hierarchy."""

    def test_single_top_level_article(self):
        """Test converting single top-level article (depth 0 → path 1)."""
        articles = [
            {"article_number": "TOP-001", "level": "0"}
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 1
        assert result[0]["level"] == "1"  # Excel depth 0 → path "1"

    def test_two_level_hierarchy(self):
        """Test converting 2-level hierarchy (0, 1 → 1, 1.1)."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD", "level": "1"},
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 2
        assert result[0]["level"] == "1"      # Excel 0 → "1"
        assert result[1]["level"] == "1.1"    # Excel 1 → "1.1"

    def test_three_level_hierarchy(self):
        """Test converting 3-level hierarchy (0, 1, 2 → 1, 1.1, 1.1.1)."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD", "level": "1"},
            {"article_number": "GRANDCHILD", "level": "2"},
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 3
        assert result[0]["level"] == "1"        # Excel 0 → "1"
        assert result[1]["level"] == "1.1"      # Excel 1 → "1.1"
        assert result[2]["level"] == "1.1.1"    # Excel 2 → "1.1.1"

    def test_four_level_hierarchy(self):
        """Test converting 4-level hierarchy (0, 1, 2, 3 → 1, 1.1, 1.1.1, 1.1.1.1)."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD", "level": "1"},
            {"article_number": "GRAND", "level": "2"},
            {"article_number": "GREAT", "level": "3"},
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 4
        assert result[0]["level"] == "1"          # Excel 0 → "1"
        assert result[1]["level"] == "1.1"        # Excel 1 → "1.1"
        assert result[2]["level"] == "1.1.1"      # Excel 2 → "1.1.1"
        assert result[3]["level"] == "1.1.1.1"    # Excel 3 → "1.1.1.1"

    def test_multiple_children_same_level(self):
        """Test multiple children at same depth get different counters."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD1", "level": "1"},
            {"article_number": "CHILD2", "level": "1"},
            {"article_number": "CHILD3", "level": "1"},
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 4
        assert result[0]["level"] == "1"      # Top
        assert result[1]["level"] == "1.1"    # First child
        assert result[2]["level"] == "1.2"    # Second child
        assert result[3]["level"] == "1.3"    # Third child

    def test_branching_hierarchy(self):
        """Test branching hierarchy with multiple sub-branches."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD1", "level": "1"},
            {"article_number": "GRAND1", "level": "2"},
            {"article_number": "GRAND2", "level": "2"},
            {"article_number": "CHILD2", "level": "1"},
            {"article_number": "GRAND3", "level": "2"},
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 6
        assert result[0]["level"] == "1"        # TOP
        assert result[1]["level"] == "1.1"      # CHILD1
        assert result[2]["level"] == "1.1.1"    # GRAND1 (child of CHILD1)
        assert result[3]["level"] == "1.1.2"    # GRAND2 (child of CHILD1)
        assert result[4]["level"] == "1.2"      # CHILD2
        assert result[5]["level"] == "1.2.1"    # GRAND3 (child of CHILD2)

    def test_returns_to_lower_level(self):
        """Test hierarchy that returns to lower level after deep nesting."""
        articles = [
            {"article_number": "TOP", "level": "0"},
            {"article_number": "CHILD1", "level": "1"},
            {"article_number": "GRAND1", "level": "2"},
            {"article_number": "GREAT1", "level": "3"},
            {"article_number": "CHILD2", "level": "1"},  # Back to level 1
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 5
        assert result[0]["level"] == "1"          # TOP
        assert result[1]["level"] == "1.1"        # CHILD1
        assert result[2]["level"] == "1.1.1"      # GRAND1
        assert result[3]["level"] == "1.1.1.1"    # GREAT1
        assert result[4]["level"] == "1.2"        # CHILD2 (sibling of CHILD1)

    def test_already_path_notation_unchanged(self):
        """Test that articles already in path notation (with dots) are unchanged."""
        articles = [
            {"article_number": "ART1", "level": "1.5"},     # Path notation (has dot)
            {"article_number": "ART2", "level": "1.5.2"},   # Path notation (has dots)
            {"article_number": "ART3", "level": "2.3.4.5"}, # Path notation (has dots)
        ]

        result = _convert_depth_to_path(articles)

        # Should remain unchanged since they already have dots (path notation)
        assert len(result) == 3
        assert result[0]["level"] == "1.5"
        assert result[1]["level"] == "1.5.2"
        assert result[2]["level"] == "2.3.4.5"

    def test_mixed_depth_and_path_notation(self):
        """Test handling mixed depth integers and path notation.

        NOTE: This is an edge case - normally Excel files have consistent formatting.
        But function should handle it gracefully.
        """
        articles = [
            {"article_number": "TOP", "level": "0"},      # Depth integer
            {"article_number": "CHILD", "level": "1.2"},  # Already path (skipped)
            {"article_number": "GRAND", "level": "1"},    # Depth integer (continues from depth 0)
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 3
        assert result[0]["level"] == "1"      # Converted from depth 0
        assert result[1]["level"] == "1.2"    # Unchanged (already has dot)
        assert result[2]["level"] == "1.1"    # Converted from depth 1 (continues sequentially)

    def test_real_world_structure(self):
        """Test conversion with real-world Excel structure (like the actual file)."""
        # Simulates actual Excel file structure: 0, 1, 2, 3 depths
        articles = [
            {"article_number": "619E1B100357421RES", "level": "0"},  # Main assembly
            {"article_number": "619E1B100359572", "level": "1"},      # Lifting Yoke
            {"article_number": "619E1B100359507", "level": "2"},      # Plate
            {"article_number": "30-100041", "level": "3"},            # Material
            {"article_number": "619E1B100359541", "level": "2"},      # Another Plate
            {"article_number": "619E1B100361485", "level": "1"},      # Lever
        ]

        result = _convert_depth_to_path(articles)

        assert len(result) == 6
        assert result[0]["level"] == "1"          # Main assembly (depth 0 → "1")
        assert result[1]["level"] == "1.1"        # Lifting Yoke (depth 1 → "1.1")
        assert result[2]["level"] == "1.1.1"      # Plate (depth 2 → "1.1.1")
        assert result[3]["level"] == "1.1.1.1"    # Material (depth 3 → "1.1.1.1")
        assert result[4]["level"] == "1.1.2"      # Another Plate (depth 2 → "1.1.2")
        assert result[5]["level"] == "1.2"        # Lever (depth 1 → "1.2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
