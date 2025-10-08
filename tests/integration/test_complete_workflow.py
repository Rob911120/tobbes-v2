"""
Integration tests for complete workflow.

Tests the end-to-end flow from project creation to report generation.
"""

import pytest
from pathlib import Path
from datetime import datetime

from data import create_database
from domain.models import Project
from operations import (
    import_nivalista,
    import_lagerlogg,
    match_articles_with_charges,
    apply_charge_selection,
)
from operations.article_ops import get_articles_for_project, update_article_notes
from operations.report_ops import (
    generate_material_specification_html,
    get_report_summary,
)
from config.app_context import create_app_context


# ==================== Fixtures ====================


@pytest.fixture
def test_db():
    """Create in-memory database for testing."""
    db = create_database("sqlite", path=":memory:")
    yield db
    # Cleanup not needed for in-memory db


@pytest.fixture
def app_context(test_db, tmp_path):
    """Create application context for testing."""
    from config.settings import Settings

    settings = Settings(
        database_path=Path(":memory:"),
        # NOTE: Reports and certificates are now stored per-project in projects/{project_id}/
        # Use config.paths module for project-specific paths
    )

    return create_app_context(database=test_db, settings=settings)


@pytest.fixture
def sample_nivalista_data():
    """Sample nivålista data for testing."""
    return [
        {
            "article_number": "ART-001",
            "description": "Test Article 1",
            "quantity": 10.0,
            "level": "1",
        },
        {
            "article_number": "ART-002",
            "description": "Test Article 2",
            "quantity": 5.0,
            "level": "2",
        },
        {
            "article_number": "ART-003",
            "description": "Test Article 3",
            "quantity": 15.0,
            "level": "1",
        },
    ]


@pytest.fixture
def sample_lagerlogg_data():
    """Sample lagerlogg data for testing."""
    return [
        {
            "article_number": "ART-001",
            "charge_number": "CHARGE-001",
            "quantity": 20.0,
        },
        {
            "article_number": "ART-002",
            "charge_number": "CHARGE-002",
            "quantity": 10.0,
        },
        {
            "article_number": "ART-002",
            "charge_number": "CHARGE-003",
            "quantity": 5.0,
        },
    ]


# ==================== Workflow Tests ====================


def test_complete_workflow_end_to_end(
    app_context,
    sample_nivalista_data,
    sample_lagerlogg_data,
):
    """Test complete workflow from project creation to report generation."""
    db = app_context.database

    # Step 1: Create project
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer AB",
        created_by="test_user",
    )

    assert project_id is not None

    # Update context with project
    app_context = app_context.with_project(project_id)

    # Step 2: Import nivålista (simulated - we use dict data instead of Excel)
    for article_data in sample_nivalista_data:
        db.save_global_article(
            article_number=article_data["article_number"],
            description=article_data["description"],
        )

    db.save_project_articles(project_id, sample_nivalista_data)

    # Verify articles imported
    articles = db.get_project_articles(project_id)
    assert len(articles) == 3

    # Step 3: Import lagerlogg (simulated)
    db.save_inventory_items(project_id, sample_lagerlogg_data)

    # Verify inventory imported
    inventory = db.get_inventory_items(project_id)
    assert len(inventory) == 3

    # Step 4: Match articles with charges
    articles_list = get_articles_for_project(db, project_id)
    match_results = match_articles_with_charges(
        articles_list,
        inventory,
        auto_match_single=True,
    )

    assert len(match_results) == 3

    # ART-001 should auto-match to CHARGE-001 (only one available)
    # MatchResult.article might be Article object or dict
    art001_result = next(
        r for r in match_results
        if (hasattr(r.article, 'article_number') and r.article.article_number == "ART-001")
        or (isinstance(r.article, dict) and r.article.get("article_number") == "ART-001")
    )
    assert art001_result.selected_charge == "CHARGE-001"

    # ART-002 should have multiple charges available
    # With auto_match_single=True, it will auto-select even with multiple charges
    art002_result = next(
        r for r in match_results
        if (hasattr(r.article, 'article_number') and r.article.article_number == "ART-002")
        or (isinstance(r.article, dict) and r.article.get("article_number") == "ART-002")
    )
    assert len(art002_result.available_charges) == 2
    # Auto-match picks first available charge
    assert art002_result.selected_charge in ["CHARGE-002", "CHARGE-003"]

    # Step 5: Verify matching worked correctly
    # Charges are assigned via apply_charge_selection in real UI
    # For this test, we verify the match_results are correct
    assert art001_result.auto_matched is True
    assert art002_result.auto_matched is True

    # Step 6: Add global notes to article
    update_article_notes(
        db=db,
        article_number="ART-001",
        notes="This article requires special handling",
        changed_by="test_user",
    )

    # Verify notes saved
    articles_with_notes = get_articles_for_project(db, project_id)
    art001_with_notes = next(a for a in articles_with_notes if a["article_number"] == "ART-001")
    assert art001_with_notes["global_notes"] == "This article requires special handling"

    # Step 7: Generate report HTML
    project = db.get_project(project_id)
    certificates = db.get_certificates_for_project(project_id)

    html = generate_material_specification_html(
        project=project,
        articles=articles_with_notes,
        certificates=certificates,
        include_watermark=True,
    )

    # Verify HTML contains expected data
    assert "Test Project" in html
    assert "TO-2024-001" in html
    assert "ART-001" in html
    assert "ART-002" in html
    # Charges might not be in HTML if not saved to DB yet
    assert "<!DOCTYPE html>" in html
    assert "Materialspecifikation" in html

    # Step 8: Get report summary
    summary = get_report_summary(articles_with_notes, certificates)

    assert summary["article_count"] == 3
    # Charges weren't saved to DB in this test,  so all are without_charge
    assert summary["articles_without_charge"] == 3
    assert summary["certificate_count"] == 0


def test_workflow_with_certificate_upload(app_context, sample_nivalista_data, tmp_path):
    """Test workflow with certificate upload."""
    from services.certificate_service import create_certificate_service

    db = app_context.database

    # Create project and import articles
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer",
        created_by="test_user",
    )

    db.save_project_articles(project_id, sample_nivalista_data)

    # Create certificate file
    cert_file = tmp_path / "test_cert.pdf"
    cert_file.write_text("PDF certificate content")

    # Upload certificate via CertificateService (matches production code)
    cert_service = create_certificate_service()
    result = cert_service.process_certificate(
        original_path=cert_file,
        article_num="ART-001",
        cert_type="Materialintyg",
        project_id=project_id,
        db=db
    )

    assert result['success'] is True
    cert_data = result['data']
    assert cert_data['id'] is not None

    # Verify certificate was saved
    certs = db.get_certificates_for_article(project_id, "ART-001")
    assert len(certs) == 1
    # Database returns dicts
    assert certs[0]["certificate_type"] == "Materialintyg"
    assert certs[0]["original_name"] == "test_cert.pdf"


def test_workflow_article_update_removes_certificates(
    app_context,
    sample_nivalista_data,
    tmp_path,
):
    """Test that updating article charge removes certificates."""
    from services.certificate_service import create_certificate_service

    db = app_context.database

    # Create project
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer",
        created_by="test_user",
    )

    # Import articles with charge
    articles = sample_nivalista_data.copy()
    articles[0]["charge_number"] = "CHARGE-001"

    db.save_project_articles(project_id, articles)

    # Upload certificate via CertificateService (matches production code)
    cert_file = tmp_path / "cert.pdf"
    cert_file.write_text("PDF content")

    cert_service = create_certificate_service()
    result = cert_service.process_certificate(
        original_path=cert_file,
        article_num="ART-001",
        cert_type="Materialintyg",
        project_id=project_id,
        db=db
    )

    assert result['success'] is True

    # Verify certificate exists
    certs_before = db.get_certificates_for_article(project_id, "ART-001")
    assert len(certs_before) == 1

    # Update article charge (should remove certificates)
    from operations.update_ops import apply_updates
    from domain.models import ArticleUpdate

    updates = [
        ArticleUpdate(
            article_number="ART-001",
            field_name="charge_number",
            old_value="CHARGE-001",
            new_value="CHARGE-002",
            update_type="lagerlogg",
            affects_certificates=True,
        )
    ]

    apply_updates(db, project_id, updates)

    # Verify certificates were removed
    certs_after = db.get_certificates_for_article(project_id, "ART-001")
    assert len(certs_after) == 0


def test_workflow_multiple_projects_share_global_notes(app_context):
    """Test that global notes are shared across projects."""
    db = app_context.database

    # Create two projects
    project1_id = db.save_project(
        project_name="Project 1",
        order_number="TO-2024-001",
        customer="Customer 1",
        created_by="user1",
    )

    project2_id = db.save_project(
        project_name="Project 2",
        order_number="TO-2024-002",
        customer="Customer 2",
        created_by="user2",
    )

    # Add same article to both projects
    article_data = {
        "article_number": "ART-SHARED",
        "description": "Shared Article",
        "quantity": 10.0,
    }

    db.save_global_article("ART-SHARED", "Shared Article")
    db.save_project_articles(project1_id, [article_data])
    db.save_project_articles(project2_id, [article_data])

    # Add notes to article from project 1
    update_article_notes(
        db=db,
        article_number="ART-SHARED",
        notes="Global note - visible in all projects",
        changed_by="user1",
    )

    # Verify notes visible in both projects
    project1_articles = get_articles_for_project(db, project1_id)
    project2_articles = get_articles_for_project(db, project2_id)

    assert project1_articles[0]["global_notes"] == "Global note - visible in all projects"
    assert project2_articles[0]["global_notes"] == "Global note - visible in all projects"


# ==================== Error Handling Tests ====================


def test_workflow_handles_missing_charge_gracefully(
    app_context,
    sample_nivalista_data,
):
    """Test that workflow handles articles without charges."""
    db = app_context.database

    # Create project with articles
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer",
        created_by="test_user",
    )

    db.save_project_articles(project_id, sample_nivalista_data)

    # Don't import any inventory (no charges available)

    # Match should still work
    articles_list = get_articles_for_project(db, project_id)
    inventory = db.get_inventory_items(project_id)
    match_results = match_articles_with_charges(articles_list, inventory)

    # All articles should have no available charges
    assert all(len(r.available_charges) == 0 for r in match_results)
    assert all(r.selected_charge is None for r in match_results)


def test_workflow_generates_report_without_certificates(
    app_context,
    sample_nivalista_data,
):
    """Test that report generation works without certificates."""
    db = app_context.database

    # Create project
    project_id = db.save_project(
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer",
        created_by="test_user",
    )

    db.save_project_articles(project_id, sample_nivalista_data)

    # Generate report without any certificates
    project = db.get_project(project_id)
    articles = get_articles_for_project(db, project_id)
    certificates = []  # No certificates

    html = generate_material_specification_html(
        project=project,
        articles=articles,
        certificates=certificates,
        include_watermark=False,
    )

    # Should still generate valid HTML
    assert "<!DOCTYPE html>" in html
    assert "Test Project" in html
    assert "ART-001" in html

    # Summary should show 0 certificates
    summary = get_report_summary(articles, certificates)
    assert summary["certificate_count"] == 0
    assert summary["articles_with_certificates"] == 0
