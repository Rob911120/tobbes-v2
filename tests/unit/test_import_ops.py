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
)
from domain.exceptions import ImportValidationError, ValidationError


@pytest.fixture
def nivalista_file(tmp_path):
    """Create a test nivålista Excel file."""
    file_path = tmp_path / "nivalista.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", "ART-002", "ART-003"],
        "Benämning": ["Artikel 1", "Artikel 2", "Artikel 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": ["1", "1.1", "1.1.1"],
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
    assert articles[0]["level"] == "1"


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
        "Nivå": ["1", "2", "3"],
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


def test_validate_import_file_missing_columns(tmp_path):
    """Test validation fails for file with missing columns."""
    file_path = tmp_path / "invalid.xlsx"
    df = pd.DataFrame({"WrongColumn": [1, 2, 3]})
    df.to_excel(file_path, index=False)

    with pytest.raises(ImportValidationError) as exc_info:
        validate_import_file(file_path, expected_type="nivålista")

    assert "saknar obligatoriska kolumner" in str(exc_info.value)


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
        "Nivå": ["1", "1.1"],  # Excel may convert to float
    })
    df.to_excel(file_path, index=False)

    articles = import_nivalista(file_path)

    assert articles[0]["article_number"] == "ART-001"  # Trimmed
    assert articles[0]["description"] == "Artikel 1"  # Trimmed
    assert articles[0]["level"] in ["1", "1.0"]  # Excel may convert to float


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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
