"""
Unit tests for Update Operations.

Tests cover project update functionality - comparing and applying changes.
"""

import pytest
from data import create_database
from domain.models import ArticleUpdate
from domain.exceptions import ValidationError, DatabaseError

from operations.update_ops import (
    compare_articles_for_update,
    apply_updates,
    get_update_summary,
    filter_updates_by_field,
    get_articles_with_updates,
)


@pytest.fixture
def db():
    """Create in-memory database for testing."""
    database = create_database("sqlite", ":memory:")
    return database


@pytest.fixture
def project_with_articles(db):
    """Create project with sample articles."""
    # Create project
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-001",
        customer="Test Customer",
        created_by="test_user"
    )

    # Create global articles
    db.save_global_article("ART-001", "Article 1", "")
    db.save_global_article("ART-002", "Article 2", "")
    db.save_global_article("ART-003", "Article 3", "")

    # Add to project
    db.save_project_articles(
        project_id=project_id,
        articles=[
            {
                "article_number": "ART-001",
                "description": "Article 1",
                "quantity": 10.0,
                "level": "1",
                "charge_number": "CHARGE-A",
            },
            {
                "article_number": "ART-002",
                "description": "Article 2",
                "quantity": 20.0,
                "level": "1.1",
                "charge_number": "CHARGE-B",
            },
            {
                "article_number": "ART-003",
                "description": "Article 3",
                "quantity": 5.0,
                "level": "1.1.1",
            },
        ]
    )

    return project_id


def test_compare_articles_lagerlogg_charge_change(db, project_with_articles):
    """Test detecting charge_number changes from lagerlogg."""
    # Get current articles
    current = db.get_project_articles_with_global_data(project_with_articles)

    # New lagerlogg data with different charge
    new_data = [
        {"article_number": "ART-001", "charge_number": "CHARGE-NEW"},
        {"article_number": "ART-002", "charge_number": "CHARGE-B"},  # Same
    ]

    updates = compare_articles_for_update(current, new_data, "lagerlogg")

    # Should find 1 update (ART-001 charge changed)
    assert len(updates) == 1
    assert updates[0].article_number == "ART-001"
    assert updates[0].field_name == "charge_number"
    assert updates[0].old_value == "CHARGE-A"
    assert updates[0].new_value == "CHARGE-NEW"
    assert updates[0].affects_certificates is True


def test_compare_articles_nivalista_quantity_change(db, project_with_articles):
    """Test detecting quantity changes from nivålista."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    # New nivålista with different quantities
    new_data = [
        {"article_number": "ART-001", "quantity": 15.0, "level": "1"},  # Changed
        {"article_number": "ART-002", "quantity": 20.0, "level": "1.1"},  # Same
    ]

    updates = compare_articles_for_update(current, new_data, "nivalista")

    # Find quantity update
    qty_updates = [u for u in updates if u.field_name == "quantity"]
    assert len(qty_updates) == 1
    assert qty_updates[0].article_number == "ART-001"
    assert qty_updates[0].old_value == 10.0
    assert qty_updates[0].new_value == 15.0
    assert qty_updates[0].affects_certificates is False


def test_compare_articles_nivalista_level_change(db, project_with_articles):
    """Test detecting level changes from nivålista."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    new_data = [
        {"article_number": "ART-001", "quantity": 10.0, "level": "2"},  # Level changed
    ]

    updates = compare_articles_for_update(current, new_data, "nivalista")

    level_updates = [u for u in updates if u.field_name == "level"]
    assert len(level_updates) == 1
    assert level_updates[0].old_value == "1"
    assert level_updates[0].new_value == "2"


def test_compare_articles_nivalista_description_change(db, project_with_articles):
    """Test detecting description changes."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    new_data = [
        {"article_number": "ART-001", "description": "Article 1 Updated", "quantity": 10.0},
    ]

    updates = compare_articles_for_update(current, new_data, "nivalista")

    desc_updates = [u for u in updates if u.field_name == "description"]
    assert len(desc_updates) == 1
    assert desc_updates[0].old_value == "Article 1"
    assert desc_updates[0].new_value == "Article 1 Updated"


def test_compare_articles_invalid_update_type(db, project_with_articles):
    """Test that invalid update_type raises error."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    with pytest.raises(ValidationError):
        compare_articles_for_update(current, [], "invalid_type")


def test_compare_articles_no_changes(db, project_with_articles):
    """Test when nothing has changed."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    # Same data as current
    new_data = [
        {"article_number": "ART-001", "charge_number": "CHARGE-A"},
        {"article_number": "ART-002", "charge_number": "CHARGE-B"},
    ]

    updates = compare_articles_for_update(current, new_data, "lagerlogg")

    assert len(updates) == 0


def test_compare_articles_new_article_ignored(db, project_with_articles):
    """Test that new articles (not in project) are ignored."""
    current = db.get_project_articles_with_global_data(project_with_articles)

    new_data = [
        {"article_number": "ART-999", "charge_number": "CHARGE-X"},  # New, not in project
    ]

    updates = compare_articles_for_update(current, new_data, "lagerlogg")

    # Should ignore new article
    assert len(updates) == 0


def test_apply_updates_charge_change(db, project_with_articles):
    """Test applying charge_number update."""
    update = ArticleUpdate(
        article_number="ART-001",
        field_name="charge_number",
        old_value="CHARGE-A",
        new_value="CHARGE-NEW",
        update_type="lagerlogg",
        affects_certificates=False,  # No certs to remove in this test
    )

    result = apply_updates(db, project_with_articles, [update])

    assert result["applied_count"] == 1
    assert result["certificates_removed"] == 0
    assert len(result["errors"]) == 0

    # Verify charge was updated
    articles = db.get_project_articles_with_global_data(project_with_articles)
    art_001 = next(a for a in articles if a["article_number"] == "ART-001")
    assert art_001["charge_number"] == "CHARGE-NEW"


def test_apply_updates_description_change(db, project_with_articles):
    """Test applying description update (global)."""
    update = ArticleUpdate(
        article_number="ART-001",
        field_name="description",
        old_value="Article 1",
        new_value="Article 1 Updated",
        update_type="nivalista",
        affects_certificates=False,
    )

    result = apply_updates(db, project_with_articles, [update])

    assert result["applied_count"] == 1

    # Verify description was updated globally
    global_article = db.get_global_article("ART-001")
    assert global_article["description"] == "Article 1 Updated"


def test_apply_updates_removes_certificates_on_charge_change(db, project_with_articles):
    """Test that certificates are removed when charge changes."""
    # Add a certificate first
    db.save_certificate(
        project_id=project_with_articles,
        article_number="ART-001",
        certificate_type="Materialintyg",
        file_path="/path/to/cert.pdf",
        original_filename="cert.pdf",
    )

    # Verify cert exists
    certs_before = db.get_certificates_for_article(project_with_articles, "ART-001")
    assert len(certs_before) == 1

    # Apply charge update
    update = ArticleUpdate(
        article_number="ART-001",
        field_name="charge_number",
        old_value="CHARGE-A",
        new_value="CHARGE-NEW",
        update_type="lagerlogg",
        affects_certificates=True,
    )

    result = apply_updates(db, project_with_articles, [update])

    assert result["applied_count"] == 1
    assert result["certificates_removed"] == 1

    # Verify cert was removed
    certs_after = db.get_certificates_for_article(project_with_articles, "ART-001")
    assert len(certs_after) == 0


def test_apply_updates_multiple(db, project_with_articles):
    """Test applying multiple updates at once."""
    updates = [
        ArticleUpdate(
            article_number="ART-001",
            field_name="charge_number",
            old_value="CHARGE-A",
            new_value="CHARGE-NEW",
            update_type="lagerlogg",
            affects_certificates=False,
        ),
        ArticleUpdate(
            article_number="ART-002",
            field_name="charge_number",
            old_value="CHARGE-B",
            new_value="CHARGE-NEW2",
            update_type="lagerlogg",
            affects_certificates=False,
        ),
    ]

    result = apply_updates(db, project_with_articles, updates)

    assert result["applied_count"] == 2
    assert len(result["errors"]) == 0


def test_get_update_summary():
    """Test getting summary statistics."""
    updates = [
        ArticleUpdate(
            article_number="ART-001",
            field_name="charge_number",
            old_value="A",
            new_value="B",
            update_type="lagerlogg",
            affects_certificates=True,
        ),
        ArticleUpdate(
            article_number="ART-001",
            field_name="quantity",
            old_value=10.0,
            new_value=15.0,
            update_type="nivalista",
            affects_certificates=False,
        ),
        ArticleUpdate(
            article_number="ART-002",
            field_name="charge_number",
            old_value="C",
            new_value="D",
            update_type="lagerlogg",
            affects_certificates=True,
        ),
    ]

    summary = get_update_summary(updates)

    assert summary["total_count"] == 3
    assert summary["affects_certificates_count"] == 2
    assert summary["unique_articles"] == 2
    assert summary["by_field"]["charge_number"] == 2
    assert summary["by_field"]["quantity"] == 1


def test_filter_updates_by_field():
    """Test filtering updates by field name."""
    updates = [
        ArticleUpdate("ART-001", "charge_number", "A", "B", "lagerlogg", False),
        ArticleUpdate("ART-002", "quantity", 10.0, 15.0, "nivalista", False),
        ArticleUpdate("ART-003", "charge_number", "C", "D", "lagerlogg", False),
    ]

    charge_updates = filter_updates_by_field(updates, "charge_number")

    assert len(charge_updates) == 2
    assert all(u.field_name == "charge_number" for u in charge_updates)


def test_get_articles_with_updates():
    """Test getting unique article numbers."""
    updates = [
        ArticleUpdate("ART-001", "charge_number", "A", "B", "lagerlogg", False),
        ArticleUpdate("ART-001", "quantity", 10.0, 15.0, "nivalista", False),
        ArticleUpdate("ART-002", "charge_number", "C", "D", "lagerlogg", False),
    ]

    articles = get_articles_with_updates(updates)

    assert articles == ["ART-001", "ART-002"]  # Sorted, unique


def test_empty_updates():
    """Test operations with empty update list."""
    summary = get_update_summary([])
    assert summary["total_count"] == 0

    filtered = filter_updates_by_field([], "charge_number")
    assert filtered == []

    articles = get_articles_with_updates([])
    assert articles == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
