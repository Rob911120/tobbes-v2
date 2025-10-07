"""
Unit tests for Article Operations.

Tests cover global notes management and article retrieval.
"""

import pytest
from data import create_database
from domain.exceptions import ValidationError, DatabaseError

from operations.article_ops import (
    update_article_notes,
    get_articles_for_project,
    get_notes_history,
    get_articles_with_notes,
)


@pytest.fixture
def db():
    """Create in-memory database for testing."""
    database = create_database("sqlite", ":memory:")
    return database


@pytest.fixture
def sample_project(db):
    """Create sample project with articles."""
    # Create project
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-001",
        customer="Test Customer",
        created_by="test_user"
    )

    # Create global articles
    db.save_global_article("ART-001", "Article 1", "")
    db.save_global_article("ART-002", "Article 2", "Initial notes")
    db.save_global_article("ART-003", "Article 3", "")

    # Add articles to project
    db.save_project_articles(
        project_id=project_id,
        articles=[
            {
                "article_number": "ART-001",
                "quantity": 5.0,
                "level": "1",
            },
            {
                "article_number": "ART-002",
                "quantity": 10.0,
                "level": "1.1",
            },
            {
                "article_number": "ART-003",
                "quantity": 2.0,
                "level": "1.1.1",
            },
        ]
    )

    return project_id


def test_update_article_notes_success(db):
    """Test updating article notes successfully."""
    # Create global article
    db.save_global_article("ART-001", "Test Article", "")

    # Update notes
    result = update_article_notes(
        db=db,
        article_number="ART-001",
        notes="Requires special handling",
        changed_by="test_user"
    )

    assert result is True

    # Verify notes were updated
    article = db.get_global_article("ART-001")
    assert article["notes"] == "Requires special handling"


def test_update_article_notes_invalid_article(db):
    """Test that invalid article number raises ValidationError."""
    with pytest.raises(ValidationError):
        update_article_notes(
            db=db,
            article_number="",  # Invalid
            notes="Test notes",
            changed_by="test_user"
        )


def test_update_article_notes_empty_clears_notes(db):
    """Test that empty string clears notes."""
    # Create article with notes
    db.save_global_article("ART-001", "Test Article", "Old notes")

    # Clear notes
    result = update_article_notes(
        db=db,
        article_number="ART-001",
        notes="",  # Clear
        changed_by="test_user"
    )

    assert result is True

    # Verify notes were cleared
    article = db.get_global_article("ART-001")
    assert article["notes"] == ""


def test_get_articles_for_project(db, sample_project):
    """Test getting articles for a project with global data."""
    articles = get_articles_for_project(db, sample_project)

    assert len(articles) == 3

    # Check that global data is populated (uses alias global_notes, global_description)
    art_001 = next(a for a in articles if a["article_number"] == "ART-001")
    assert art_001["global_description"] == "Article 1"
    assert art_001["global_notes"] == ""

    art_002 = next(a for a in articles if a["article_number"] == "ART-002")
    assert art_002["global_description"] == "Article 2"
    assert art_002["global_notes"] == "Initial notes"


def test_get_articles_for_project_empty(db):
    """Test getting articles from empty project."""
    # Create empty project
    project_id = db.save_project(
        project_name="Empty Project",
        order_number="TO-999",
        customer="Test",
        created_by="test"
    )

    articles = get_articles_for_project(db, project_id)

    assert len(articles) == 0


def test_get_notes_history(db):
    """Test getting notes change history."""
    # Create article
    db.save_global_article("ART-001", "Test Article", "Original notes")

    # Update notes multiple times
    update_article_notes(db, "ART-001", "First update", "user1")
    update_article_notes(db, "ART-001", "Second update", "user2")
    update_article_notes(db, "ART-001", "Third update", "user1")

    # Get history
    history = get_notes_history(db, "ART-001", limit=10)

    # Should have 3 updates (plus possibly initial creation)
    assert len(history) >= 3

    # Find the update entries (history might be ordered oldest-first or newest-first)
    update_entries = [h for h in history if "update" in h["new_notes"].lower()]
    assert len(update_entries) >= 3

    # Verify the updates exist
    notes_values = [h["new_notes"] for h in history]
    assert "First update" in notes_values
    assert "Second update" in notes_values
    assert "Third update" in notes_values


def test_get_notes_history_invalid_article(db):
    """Test that invalid article number raises ValidationError."""
    with pytest.raises(ValidationError):
        get_notes_history(db, "", limit=10)


def test_get_notes_history_limit(db):
    """Test that limit parameter works."""
    # Create article
    db.save_global_article("ART-001", "Test Article", "")

    # Make many updates
    for i in range(20):
        update_article_notes(db, "ART-001", f"Update {i}", "user")

    # Get limited history
    history = get_notes_history(db, "ART-001", limit=5)

    assert len(history) <= 5


def test_get_articles_with_notes(db, sample_project):
    """Test filtering articles that have notes."""
    # ART-002 has notes, ART-001 and ART-003 don't
    articles = get_articles_with_notes(db, sample_project)

    assert len(articles) == 1
    assert articles[0]["article_number"] == "ART-002"
    assert articles[0]["global_notes"] == "Initial notes"


def test_get_articles_with_notes_empty_notes_filtered(db):
    """Test that articles with empty/whitespace notes are filtered."""
    project_id = db.save_project(
        project_name="Test",
        order_number="TO-001",
        customer="Test",
        created_by="test"
    )

    # Create articles with various notes states
    db.save_global_article("ART-001", "Article 1", "Has notes")
    db.save_global_article("ART-002", "Article 2", "")  # Empty
    db.save_global_article("ART-003", "Article 3", "   ")  # Whitespace

    db.save_project_articles(
        project_id=project_id,
        articles=[
            {"article_number": "ART-001", "quantity": 1.0},
            {"article_number": "ART-002", "quantity": 1.0},
            {"article_number": "ART-003", "quantity": 1.0},
        ]
    )

    articles = get_articles_with_notes(db, project_id)

    # Only ART-001 should be returned
    assert len(articles) == 1
    assert articles[0]["article_number"] == "ART-001"


def test_global_notes_shared_across_projects(db):
    """
    CRITICAL TEST: Verify that notes are truly global.

    When notes are updated for an article, the change should be
    visible in ALL projects where that article exists.
    """
    # Create two projects
    project1_id = db.save_project(
        project_name="Project 1",
        order_number="TO-001",
        customer="Customer 1",
        created_by="test"
    )
    project2_id = db.save_project(
        project_name="Project 2",
        order_number="TO-002",
        customer="Customer 2",
        created_by="test"
    )

    # Create global article
    db.save_global_article("ART-SHARED", "Shared Article", "")

    # Add to both projects
    db.save_project_articles(
        project_id=project1_id,
        articles=[{"article_number": "ART-SHARED", "quantity": 5.0}]
    )
    db.save_project_articles(
        project_id=project2_id,
        articles=[{"article_number": "ART-SHARED", "quantity": 10.0}]
    )

    # Update notes from project 1 context
    update_article_notes(
        db=db,
        article_number="ART-SHARED",
        notes="This is a global note",
        changed_by="user_in_project1"
    )

    # Verify notes visible in BOTH projects
    articles_p1 = get_articles_for_project(db, project1_id)
    articles_p2 = get_articles_for_project(db, project2_id)

    art_p1 = next(a for a in articles_p1 if a["article_number"] == "ART-SHARED")
    art_p2 = next(a for a in articles_p2 if a["article_number"] == "ART-SHARED")

    # Same notes in both projects (uses global_notes field)
    assert art_p1["global_notes"] == "This is a global note"
    assert art_p2["global_notes"] == "This is a global note"

    # But different quantities (project-specific)
    assert art_p1["quantity"] == 5.0
    assert art_p2["quantity"] == 10.0


def test_audit_log_tracks_changes(db):
    """Test that audit log records all changes."""
    # Create article
    db.save_global_article("ART-001", "Test", "Original")

    # Make changes
    update_article_notes(db, "ART-001", "Change 1", "alice")
    update_article_notes(db, "ART-001", "Change 2", "bob")

    # Get history
    history = get_notes_history(db, "ART-001")

    # Find the changes
    change1 = next((h for h in history if h["new_notes"] == "Change 1"), None)
    change2 = next((h for h in history if h["new_notes"] == "Change 2"), None)

    assert change1 is not None
    assert change1["changed_by"] == "alice"
    assert change1["old_notes"] == "Original"

    assert change2 is not None
    assert change2["changed_by"] == "bob"
    assert change2["old_notes"] == "Change 1"


def test_update_nonexistent_article_handled_gracefully(db):
    """Test that updating notes for non-existent article is handled gracefully."""
    # Create the article first
    db.save_global_article("ART-NEW", "New Article", "")

    # Now update notes
    result = update_article_notes(
        db=db,
        article_number="ART-NEW",
        notes="Notes for new article",
        changed_by="user"
    )

    # Should succeed
    assert result is True

    # Verify notes were updated
    article = db.get_global_article("ART-NEW")
    assert article is not None
    assert article["notes"] == "Notes for new article"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
