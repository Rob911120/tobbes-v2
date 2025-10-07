"""
Unit tests for Report Operations.

Tests cover HTML generation, PDF report creation, and helper functions.
"""

import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from domain.models import Project, Certificate
from domain.exceptions import ReportGenerationError

from operations.report_ops import (
    generate_material_specification_html,
    generate_pdf_report,
    merge_certificates_into_report,
    create_table_of_contents,
    get_report_summary,
    filter_articles_by_charge_status,
)


# ==================== Fixtures ====================


@pytest.fixture
def sample_project():
    """Create sample project for testing."""
    return Project(
        id=1,
        project_name="Test Project",
        order_number="TO-2024-001",
        customer="Test Customer AB",
        created_by="test_user",
        created_at=datetime(2024, 1, 1),
    )


@pytest.fixture
def sample_articles():
    """Create sample article dicts for testing."""
    return [
        {
            "article_number": "ART-001",
            "description": "Test Article 1",
            "global_description": "Global Description 1",
            "quantity": 10.0,
            "level": "1",
            "charge_number": "CHARGE-001",
        },
        {
            "article_number": "ART-002",
            "description": "Test Article 2",
            "global_description": "Global Description 2",
            "quantity": 5.0,
            "level": "2",
            "charge_number": "CHARGE-002",
        },
        {
            "article_number": "ART-003",
            "description": "Test Article 3",
            "global_description": "Global Description 3",
            "quantity": 15.0,
            "level": "1",
            "charge_number": "",  # No charge
        },
    ]


@pytest.fixture
def sample_certificates():
    """Create sample certificates for testing."""
    return [
        Certificate(
            id=1,
            project_id=1,
            article_number="ART-001",
            certificate_type="Materialintyg",
            file_path="project_1/article_ART-001/cert1.pdf",
            original_filename="cert1.pdf",
            page_count=3,
        ),
        Certificate(
            id=2,
            project_id=1,
            article_number="ART-001",
            certificate_type="Svetslogg",
            file_path="project_1/article_ART-001/cert2.pdf",
            original_filename="cert2.pdf",
            page_count=2,
        ),
        Certificate(
            id=3,
            project_id=1,
            article_number="ART-002",
            certificate_type="Kontrollrapport",
            file_path="project_1/article_ART-002/cert3.pdf",
            original_filename="cert3.pdf",
            page_count=1,
        ),
    ]


# ==================== HTML Generation Tests ====================


def test_generate_material_specification_html_basic(sample_project, sample_articles):
    """Test generating basic HTML material specification."""
    html = generate_material_specification_html(
        project=sample_project,
        articles=sample_articles,
        include_watermark=False,
    )

    # Check HTML structure
    assert "<!DOCTYPE html>" in html
    assert "<html>" in html
    assert "</html>" in html
    assert "<body>" in html or "<body " in html

    # Check project info
    assert "Test Project" in html
    assert "TO-2024-001" in html
    assert "Test Customer AB" in html

    # Check articles
    assert "ART-001" in html
    assert "ART-002" in html
    assert "ART-003" in html
    assert "Global Description 1" in html


def test_generate_material_specification_html_with_watermark(sample_project, sample_articles):
    """Test generating HTML with watermark enabled."""
    html = generate_material_specification_html(
        project=sample_project,
        articles=sample_articles,
        include_watermark=True,
    )

    # Check watermark class
    assert 'class="watermarked"' in html
    # Check watermark CSS
    assert "FA-TEC" in html or "watermark" in html.lower()


def test_generate_material_specification_html_with_certificates(
    sample_project, sample_articles, sample_certificates
):
    """Test generating HTML with certificates included."""
    html = generate_material_specification_html(
        project=sample_project,
        articles=sample_articles,
        certificates=sample_certificates,
        include_watermark=False,
    )

    # Check certificate info appears
    assert "Materialintyg" in html
    assert "Svetslogg" in html
    assert "Kontrollrapport" in html


def test_generate_material_specification_html_empty_articles(sample_project):
    """Test generating HTML with no articles."""
    html = generate_material_specification_html(
        project=sample_project,
        articles=[],
        include_watermark=False,
    )

    # Should still generate valid HTML
    assert "<!DOCTYPE html>" in html
    assert "Test Project" in html
    # But table should be empty or show no articles


# ==================== PDF Generation Tests ====================


def test_generate_pdf_report_success(tmp_path):
    """Test successful PDF generation."""
    output_path = tmp_path / "test_report.pdf"
    html_content = "<html><body><h1>Test</h1></body></html>"

    # Mock PDFService
    mock_service = Mock()
    mock_service.html_to_pdf.return_value = output_path

    # Generate PDF
    result = generate_pdf_report(
        pdf_service=mock_service,
        html_content=html_content,
        output_path=output_path,
    )

    # Verify
    assert result == output_path
    mock_service.html_to_pdf.assert_called_once_with(
        html_content=html_content,
        output_path=output_path,
        page_size="A4",
    )


def test_generate_pdf_report_creates_output_directory(tmp_path):
    """Test that output directory is created if missing."""
    output_path = tmp_path / "subdir" / "test_report.pdf"
    html_content = "<html><body><h1>Test</h1></body></html>"

    # Mock PDFService
    mock_service = Mock()
    mock_service.html_to_pdf.return_value = output_path

    # Generate PDF
    result = generate_pdf_report(
        pdf_service=mock_service,
        html_content=html_content,
        output_path=output_path,
    )

    # Verify directory was created
    assert output_path.parent.exists()
    assert result == output_path


def test_generate_pdf_report_failure():
    """Test PDF generation failure handling."""
    output_path = Path("/tmp/test.pdf")
    html_content = "<html><body><h1>Test</h1></body></html>"

    # Mock PDFService that raises exception
    mock_service = Mock()
    mock_service.html_to_pdf.side_effect = Exception("PDF generation failed")

    # Should raise ReportGenerationError
    with pytest.raises(ReportGenerationError) as exc_info:
        generate_pdf_report(
            pdf_service=mock_service,
            html_content=html_content,
            output_path=output_path,
        )

    assert "Kunde inte generera PDF-rapport" in str(exc_info.value.message)


# ==================== Certificate Merging Tests ====================


def test_merge_certificates_into_report_success(tmp_path, sample_certificates):
    """Test successful certificate merging."""
    main_report = tmp_path / "main_report.pdf"
    main_report.write_text("Main report content")
    output_path = tmp_path / "merged_report.pdf"
    base_dir = tmp_path

    # Create certificate files
    for cert in sample_certificates:
        cert_path = base_dir / cert.file_path
        cert_path.parent.mkdir(parents=True, exist_ok=True)
        cert_path.write_text(f"Certificate {cert.id} content")

    # Mock PDFService
    mock_service = Mock()
    mock_service.merge_pdfs.return_value = output_path

    # Merge
    result = merge_certificates_into_report(
        pdf_service=mock_service,
        main_report_path=main_report,
        certificates=sample_certificates,
        output_path=output_path,
        base_dir=base_dir,
    )

    # Verify
    assert result == output_path
    mock_service.merge_pdfs.assert_called_once()
    call_args = mock_service.merge_pdfs.call_args
    pdf_files = call_args.kwargs['pdf_files']
    assert main_report in pdf_files
    assert len(pdf_files) == 4  # 1 main + 3 certificates


def test_merge_certificates_into_report_missing_certificate(tmp_path, sample_certificates):
    """Test merging when some certificate files are missing."""
    main_report = tmp_path / "main_report.pdf"
    main_report.write_text("Main report content")
    output_path = tmp_path / "merged_report.pdf"
    base_dir = tmp_path

    # Only create first certificate file
    cert1_path = base_dir / sample_certificates[0].file_path
    cert1_path.parent.mkdir(parents=True, exist_ok=True)
    cert1_path.write_text("Certificate 1 content")

    # Mock PDFService
    mock_service = Mock()
    mock_service.merge_pdfs.return_value = output_path

    # Merge - should continue even if some files are missing
    result = merge_certificates_into_report(
        pdf_service=mock_service,
        main_report_path=main_report,
        certificates=sample_certificates,
        output_path=output_path,
        base_dir=base_dir,
    )

    # Verify
    assert result == output_path
    call_args = mock_service.merge_pdfs.call_args
    pdf_files = call_args.kwargs['pdf_files']
    assert main_report in pdf_files
    assert len(pdf_files) == 2  # 1 main + 1 existing certificate


def test_merge_certificates_into_report_with_progress(tmp_path, sample_certificates):
    """Test merging with progress callback."""
    main_report = tmp_path / "main_report.pdf"
    main_report.write_text("Main report content")
    output_path = tmp_path / "merged_report.pdf"
    base_dir = tmp_path

    # Mock PDFService
    mock_service = Mock()
    mock_service.merge_pdfs.return_value = output_path

    # Progress callback
    progress_values = []
    def progress_callback(value):
        progress_values.append(value)

    # Merge
    merge_certificates_into_report(
        pdf_service=mock_service,
        main_report_path=main_report,
        certificates=[],
        output_path=output_path,
        base_dir=base_dir,
        progress_callback=progress_callback,
    )

    # Verify progress was called
    assert 20 in progress_values
    assert 100 in progress_values


# ==================== Table of Contents Tests ====================


def test_create_table_of_contents_basic(sample_project, sample_articles, sample_certificates):
    """Test creating basic table of contents."""
    toc_html = create_table_of_contents(
        project=sample_project,
        articles=sample_articles,
        certificates=sample_certificates,
    )

    # Check HTML structure
    assert "<!DOCTYPE html>" in toc_html
    assert "Innehållsförteckning" in toc_html

    # Check project info
    assert "Test Project" in toc_html
    assert "TO-2024-001" in toc_html

    # Check article count
    assert "3" in toc_html  # 3 articles

    # Check certificate info
    assert "Materialintyg" in toc_html
    assert "ART-001" in toc_html


def test_create_table_of_contents_no_certificates(sample_project, sample_articles):
    """Test creating TOC with no certificates."""
    toc_html = create_table_of_contents(
        project=sample_project,
        articles=sample_articles,
        certificates=[],
    )

    # Should still generate valid HTML
    assert "<!DOCTYPE html>" in toc_html
    assert "Innehållsförteckning" in toc_html
    assert "(Inga certifikat)" in toc_html or "Inga" in toc_html.lower()


# ==================== Summary Functions Tests ====================


def test_get_report_summary_complete(sample_articles, sample_certificates):
    """Test getting complete report summary."""
    summary = get_report_summary(sample_articles, sample_certificates)

    assert summary["article_count"] == 3
    assert summary["articles_with_charge"] == 2
    assert summary["articles_without_charge"] == 1
    assert summary["certificate_count"] == 3
    assert summary["articles_with_certificates"] == 2  # ART-001, ART-002
    assert summary["unique_certificate_types"] == 3  # Materialintyg, Svetslogg, Kontrollrapport


def test_get_report_summary_no_certificates(sample_articles):
    """Test summary with no certificates."""
    summary = get_report_summary(sample_articles, [])

    assert summary["article_count"] == 3
    assert summary["certificate_count"] == 0
    assert summary["articles_with_certificates"] == 0
    assert summary["unique_certificate_types"] == 0


def test_get_report_summary_all_without_charge():
    """Test summary when all articles lack charges."""
    articles = [
        {"article_number": "ART-001", "charge_number": ""},
        {"article_number": "ART-002", "charge_number": None},
    ]

    summary = get_report_summary(articles, [])

    assert summary["article_count"] == 2
    assert summary["articles_with_charge"] == 0
    assert summary["articles_without_charge"] == 2


def test_filter_articles_by_charge_status_with_charge(sample_articles):
    """Test filtering articles WITH charge."""
    with_charge = filter_articles_by_charge_status(sample_articles, has_charge=True)

    assert len(with_charge) == 2
    assert with_charge[0]["article_number"] == "ART-001"
    assert with_charge[1]["article_number"] == "ART-002"


def test_filter_articles_by_charge_status_without_charge(sample_articles):
    """Test filtering articles WITHOUT charge."""
    without_charge = filter_articles_by_charge_status(sample_articles, has_charge=False)

    assert len(without_charge) == 1
    assert without_charge[0]["article_number"] == "ART-003"


def test_filter_articles_by_charge_status_empty_list():
    """Test filtering empty article list."""
    result = filter_articles_by_charge_status([], has_charge=True)
    assert result == []
