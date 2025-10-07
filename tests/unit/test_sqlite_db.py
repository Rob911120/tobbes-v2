"""
Unit tests for SQLite database implementation.

Tests cover basic CRUD operations for all database entities.
"""

import pytest
import tempfile
from pathlib import Path

from data import create_database
from domain.exceptions import DatabaseError


@pytest.fixture
def db():
    """Create a temporary in-memory database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    database = create_database("sqlite", db_path)
    yield database
    database.close()

    # Cleanup
    Path(db_path).unlink(missing_ok=True)


def test_create_database():
    """Test database creation and migrations."""
    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        db = create_database("sqlite", f.name)
        assert db is not None
        db.close()


def test_save_and_get_project(db):
    """Test saving and retrieving a project."""
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-001",
        customer="Test Customer",
        created_by="test_user",
        description="Test description",
    )

    assert project_id > 0

    project = db.get_project(project_id)
    assert project is not None
    assert project["project_name"] == "Test Project"
    assert project["order_number"] == "TO-001"
    assert project["customer"] == "Test Customer"


def test_duplicate_order_number_raises_error(db):
    """Test that duplicate order numbers are rejected."""
    db.save_project(
        project_name="Project 1",
        order_number="TO-001",
        customer="Customer A",
        created_by="user",
    )

    with pytest.raises(DatabaseError) as exc_info:
        db.save_project(
            project_name="Project 2",
            order_number="TO-001",  # Duplicate
            customer="Customer B",
            created_by="user",
        )

    assert "already exists" in str(exc_info.value)


def test_list_projects(db):
    """Test listing projects with pagination."""
    # Create multiple projects
    for i in range(5):
        db.save_project(
            project_name=f"Project {i}",
            order_number=f"TO-{i:03d}",
            customer=f"Customer {i}",
            created_by="test_user",
        )

    projects = db.list_projects(limit=3)
    assert len(projects) == 3

    all_projects = db.list_projects()
    assert len(all_projects) == 5


def test_global_article_operations(db):
    """Test global article save and retrieval."""
    db.save_global_article(
        article_number="ART-001",
        description="Test Article",
        notes="Test notes",
        changed_by="test_user",
    )

    article = db.get_global_article("ART-001")
    assert article is not None
    assert article["article_number"] == "ART-001"
    assert article["description"] == "Test Article"
    assert article["notes"] == "Test notes"


def test_update_article_notes_with_audit(db):
    """Test that updating notes creates audit log."""
    # Create article
    db.save_global_article(
        article_number="ART-002",
        description="Article 2",
        notes="Initial notes",
        changed_by="user1",
    )

    # Update notes
    db.update_article_notes(
        article_number="ART-002",
        notes="Updated notes",
        changed_by="user2",
    )

    # Check updated notes
    article = db.get_global_article("ART-002")
    assert article["notes"] == "Updated notes"

    # Check audit log
    history = db.get_notes_history("ART-002")
    assert len(history) >= 2  # INSERT + UPDATE = 2 entries

    # Find the update entry
    update_entry = next((h for h in history if h["new_notes"] == "Updated notes"), None)
    assert update_entry is not None
    assert update_entry["changed_by"] == "user2"
    assert update_entry["old_notes"] == "Initial notes"


def test_project_articles_with_global_data(db):
    """Test saving project articles and joining with global data."""
    # Create project
    project_id = db.save_project(
        project_name="Test",
        order_number="TO-100",
        customer="Customer",
        created_by="user",
    )

    # Save project articles
    articles = [
        {
            "article_number": "ART-100",
            "description": "Article 100",
            "quantity": 5.0,
            "level": "1",
        },
        {
            "article_number": "ART-101",
            "description": "Article 101",
            "quantity": 3.0,
            "level": "1.1",
        },
    ]
    db.save_project_articles(project_id, articles)

    # Add global notes
    db.update_article_notes("ART-100", "Global note for ART-100", "user")

    # Get articles with global data
    result = db.get_project_articles_with_global_data(project_id)
    assert len(result) == 2

    # Find ART-100
    art_100 = next(a for a in result if a["article_number"] == "ART-100")
    assert art_100["global_notes"] == "Global note for ART-100"


def test_inventory_and_charges(db):
    """Test inventory items and charge lookups."""
    # Create project
    project_id = db.save_project(
        project_name="Test",
        order_number="TO-200",
        customer="Customer",
        created_by="user",
    )

    # Save inventory items
    inventory = [
        {
            "article_number": "ART-200",
            "charge_number": "CHARGE-A",
            "quantity": 10.0,
        },
        {
            "article_number": "ART-200",
            "charge_number": "CHARGE-B",
            "quantity": 5.0,
        },
    ]
    db.save_inventory_items(project_id, inventory)

    # Get available charges
    charges = db.get_available_charges(project_id, "ART-200")
    assert len(charges) == 2
    assert "CHARGE-A" in charges
    assert "CHARGE-B" in charges


def test_certificate_operations(db):
    """Test certificate CRUD operations."""
    # Create project
    project_id = db.save_project(
        project_name="Test",
        order_number="TO-300",
        customer="Customer",
        created_by="user",
    )

    # Save certificate
    cert_id = db.save_certificate(
        project_id=project_id,
        article_number="ART-300",
        certificate_type="Materialintyg",
        file_path="certs/cert1.pdf",
        original_filename="materialintyg.pdf",
        page_count=3,
    )

    assert cert_id > 0

    # Get certificates for article
    certs = db.get_certificates_for_article(project_id, "ART-300")
    assert len(certs) == 1
    assert certs[0]["certificate_type"] == "Materialintyg"

    # Delete certificate
    result = db.delete_certificate(cert_id)
    assert result is True

    certs = db.get_certificates_for_article(project_id, "ART-300")
    assert len(certs) == 0


def test_certificate_types(db):
    """Test certificate type management."""
    # Get default global types (from migration)
    types = db.get_certificate_types()
    assert "Materialintyg" in types
    assert "Svetslogg" in types

    # Add new global type
    db.add_certificate_type("Custom Type")
    types = db.get_certificate_types()
    assert "Custom Type" in types

    # Add project-specific type
    project_id = db.save_project(
        project_name="Test",
        order_number="TO-400",
        customer="Customer",
        created_by="user",
    )
    db.add_certificate_type("Project Specific", project_id)

    # Get types for project (should include both global and project-specific)
    project_types = db.get_certificate_types(project_id)
    assert "Custom Type" in project_types
    assert "Project Specific" in project_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
