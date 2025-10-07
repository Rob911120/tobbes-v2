"""
Unit tests for Process Operations.

Tests cover matching logic for articles and inventory charges.
"""

import pytest
from domain.models import Article, InventoryItem, MatchResult

from operations.process_ops import (
    match_articles_with_charges,
    apply_charge_selection,
    get_matching_summary,
    get_unmatched_articles,
    get_articles_needing_manual_selection,
)


@pytest.fixture
def sample_articles():
    """Sample articles for testing."""
    return [
        {
            "article_number": "ART-001",
            "description": "Article 1",
            "quantity": 5.0,
            "level": "1",
        },
        {
            "article_number": "ART-002",
            "description": "Article 2",
            "quantity": 10.0,
            "level": "1.1",
        },
        {
            "article_number": "ART-003",
            "description": "Article 3",
            "quantity": 2.0,
            "level": "1.1.1",
        },
    ]


@pytest.fixture
def sample_inventory():
    """Sample inventory with charges."""
    return [
        {
            "article_number": "ART-001",
            "charge_number": "CHARGE-A",
            "quantity": 100.0,
        },
        {
            "article_number": "ART-002",
            "charge_number": "CHARGE-B",
            "quantity": 50.0,
        },
        {
            "article_number": "ART-002",
            "charge_number": "CHARGE-C",
            "quantity": 30.0,
        },
        # ART-003 has no inventory
    ]


def test_match_articles_single_charge_auto_match(sample_articles, sample_inventory):
    """Test auto-matching when single charge is available."""
    results = match_articles_with_charges(
        articles=sample_articles,
        inventory_items=sample_inventory,
        auto_match_single=True,
    )

    # ART-001 should be auto-matched (only one charge)
    art_001_result = next(r for r in results if r.article.article_number == "ART-001")
    assert art_001_result.is_matched is True
    assert art_001_result.selected_charge == "CHARGE-A"
    assert art_001_result.auto_matched is True
    assert len(art_001_result.available_charges) == 1


def test_match_articles_multiple_charges_needs_manual(sample_articles, sample_inventory):
    """Test that multiple charges require manual selection (or auto-select best)."""
    results = match_articles_with_charges(
        articles=sample_articles,
        inventory_items=sample_inventory,
        auto_match_single=True,
    )

    # ART-002 has two charges
    art_002_result = next(r for r in results if r.article.article_number == "ART-002")
    assert len(art_002_result.available_charges) == 2
    assert "CHARGE-B" in art_002_result.available_charges
    assert "CHARGE-C" in art_002_result.available_charges

    # Should auto-select best match (most recent = last in list)
    assert art_002_result.is_matched is True
    assert art_002_result.selected_charge == "CHARGE-C"  # Last/most recent


def test_match_articles_no_charges_unmatched(sample_articles, sample_inventory):
    """Test that articles without inventory remain unmatched."""
    results = match_articles_with_charges(
        articles=sample_articles,
        inventory_items=sample_inventory,
        auto_match_single=True,
    )

    # ART-003 has no inventory
    art_003_result = next(r for r in results if r.article.article_number == "ART-003")
    assert art_003_result.is_matched is False
    assert art_003_result.selected_charge is None
    assert len(art_003_result.available_charges) == 0
    assert art_003_result.match_status == "no_charges"


def test_match_articles_auto_match_disabled():
    """Test matching with auto-match disabled."""
    articles = [{"article_number": "ART-001", "quantity": 5.0}]
    inventory = [{"article_number": "ART-001", "charge_number": "CHARGE-A", "quantity": 100.0}]

    results = match_articles_with_charges(
        articles=articles,
        inventory_items=inventory,
        auto_match_single=False,  # Disable auto-match
    )

    # Should NOT be auto-matched
    assert results[0].is_matched is False
    assert results[0].selected_charge is None
    assert results[0].auto_matched is False
    assert len(results[0].available_charges) == 1


def test_apply_charge_selection_valid():
    """Test applying manual charge selection."""
    # Create a match result with multiple charges
    article = Article(
        project_id=1,
        article_number="ART-001",
        description="Test",
        quantity=5.0,
    )

    match_result = MatchResult(
        article=article,
        available_charges=["CHARGE-A", "CHARGE-B", "CHARGE-C"],
        selected_charge=None,
        auto_matched=False,
    )

    # Apply manual selection
    updated = apply_charge_selection(match_result, "CHARGE-B")

    assert updated.selected_charge == "CHARGE-B"
    assert updated.article.charge_number == "CHARGE-B"
    assert updated.auto_matched is False
    assert updated.is_matched is True


def test_apply_charge_selection_invalid_charge():
    """Test that invalid charge selection raises error."""
    article = Article(
        project_id=1,
        article_number="ART-001",
        description="Test",
        quantity=5.0,
    )

    match_result = MatchResult(
        article=article,
        available_charges=["CHARGE-A", "CHARGE-B"],
        selected_charge=None,
        auto_matched=False,
    )

    # Try to select charge not in available list
    with pytest.raises(ValueError) as exc_info:
        apply_charge_selection(match_result, "CHARGE-INVALID")

    assert "not in available charges" in str(exc_info.value)


def test_get_matching_summary():
    """Test getting matching statistics."""
    articles = [
        {"article_number": "ART-001", "quantity": 5.0},
        {"article_number": "ART-002", "quantity": 10.0},
        {"article_number": "ART-003", "quantity": 2.0},
        {"article_number": "ART-004", "quantity": 3.0},
    ]

    inventory = [
        {"article_number": "ART-001", "charge_number": "CHARGE-A", "quantity": 100.0},
        {"article_number": "ART-002", "charge_number": "CHARGE-B", "quantity": 50.0},
        {"article_number": "ART-002", "charge_number": "CHARGE-C", "quantity": 30.0},
        # ART-003 and ART-004 have no inventory
    ]

    results = match_articles_with_charges(articles, inventory, auto_match_single=True)
    summary = get_matching_summary(results)

    assert summary["total_count"] == 4
    assert summary["matched_count"] == 2  # ART-001, ART-002
    assert summary["auto_matched_count"] == 2
    assert summary["no_charges_count"] == 2  # ART-003, ART-004
    assert summary["match_rate"] == 50.0


def test_get_unmatched_articles():
    """Test getting list of unmatched articles."""
    articles = [
        {"article_number": "ART-001", "quantity": 5.0},
        {"article_number": "ART-002", "quantity": 10.0},
    ]

    inventory = [
        {"article_number": "ART-001", "charge_number": "CHARGE-A", "quantity": 100.0},
        # ART-002 has no inventory
    ]

    results = match_articles_with_charges(articles, inventory)
    unmatched = get_unmatched_articles(results)

    assert len(unmatched) == 1
    assert unmatched[0].article_number == "ART-002"


def test_get_articles_needing_manual_selection():
    """Test getting articles that need manual charge selection."""
    articles = [
        {"article_number": "ART-001", "quantity": 5.0},
        {"article_number": "ART-002", "quantity": 10.0},
    ]

    inventory = [
        {"article_number": "ART-001", "charge_number": "CHARGE-A", "quantity": 100.0},
        {"article_number": "ART-002", "charge_number": "CHARGE-B", "quantity": 50.0},
        {"article_number": "ART-002", "charge_number": "CHARGE-C", "quantity": 30.0},
    ]

    results = match_articles_with_charges(
        articles,
        inventory,
        auto_match_single=False  # Disable auto-match
    )

    needs_manual = get_articles_needing_manual_selection(results)

    # ART-002 has multiple charges and needs manual selection
    assert len(needs_manual) == 1
    assert needs_manual[0].article.article_number == "ART-002"
    assert len(needs_manual[0].available_charges) == 2


def test_match_preserves_article_data():
    """Test that matching preserves original article data."""
    articles = [
        {
            "article_number": "ART-001",
            "description": "Test Article",
            "quantity": 5.0,
            "level": "1.1.1",
        }
    ]

    inventory = [
        {"article_number": "ART-001", "charge_number": "CHARGE-A", "quantity": 100.0}
    ]

    results = match_articles_with_charges(articles, inventory)

    # Check that article data is preserved
    result = results[0]
    assert result.article.article_number == "ART-001"
    assert result.article.description == "Test Article"
    assert result.article.quantity == 5.0
    assert result.article.level == "1.1.1"


def test_empty_inputs():
    """Test matching with empty inputs."""
    # Empty articles
    results = match_articles_with_charges([], [{"article_number": "ART-001", "charge_number": "CHG-A", "quantity": 100.0}])
    assert len(results) == 0

    # Empty inventory
    results = match_articles_with_charges([{"article_number": "ART-001", "quantity": 5.0}], [])
    assert len(results) == 1
    assert results[0].is_matched is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
