"""
Unit tests for Certificate Operations.

Tests cover certificate validation, type guessing, and helper functions.
"""

import pytest
from pathlib import Path
from domain.models import Certificate
from domain.exceptions import ValidationError

from operations.certificate_ops import (
    guess_certificate_type,
    validate_certificate_file,
    create_certificate_dict,
    get_certificates_summary,
    get_certificates_for_article,
    get_certificates_by_type,
    get_articles_with_certificates,
    get_articles_without_certificates,
)


def test_guess_certificate_type_materialintyg():
    """Test guessing Materialintyg type."""
    assert guess_certificate_type("materialintyg_2024.pdf") == "Materialintyg"
    assert guess_certificate_type("material_certificate.pdf") == "Materialintyg"
    assert guess_certificate_type("cert_3.1.pdf") == "Materialintyg"


def test_guess_certificate_type_svetslogg():
    """Test guessing Svetslogg type."""
    assert guess_certificate_type("svets_protokoll.pdf") == "Svetslogg"
    assert guess_certificate_type("weld_report.pdf") == "Svetslogg"


def test_guess_certificate_type_kontrollrapport():
    """Test guessing Kontrollrapport type."""
    assert guess_certificate_type("kontroll_2024.pdf") == "Kontrollrapport"
    assert guess_certificate_type("inspection_report.pdf") == "Kontrollrapport"


def test_guess_certificate_type_unknown():
    """Test unknown type defaults to 'Andra handlingar'."""
    assert guess_certificate_type("unknown_document.pdf") == "Andra handlingar"
    assert guess_certificate_type("random.pdf") == "Andra handlingar"


def test_validate_certificate_file_valid(tmp_path):
    """Test validating valid PDF file."""
    # Create test PDF
    test_file = tmp_path / "test_cert.pdf"
    test_file.write_text("PDF content")

    result = validate_certificate_file(test_file)
    assert result == test_file


def test_validate_certificate_file_not_pdf(tmp_path):
    """Test that non-PDF files are rejected."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("Not a PDF")

    with pytest.raises(ValidationError) as exc_info:
        validate_certificate_file(test_file)

    assert "Invalid file extension" in str(exc_info.value.message)


def test_validate_certificate_file_not_exists():
    """Test that non-existent files are rejected."""
    with pytest.raises(ValidationError) as exc_info:
        validate_certificate_file(Path("/nonexistent/file.pdf"))

    assert "does not exist" in str(exc_info.value.message)


def test_create_certificate_dict_auto_type(tmp_path):
    """Test creating certificate dict with auto-detected type."""
    test_file = tmp_path / "materialintyg_2024.pdf"
    test_file.write_text("PDF content")

    cert_dict = create_certificate_dict(
        project_id=1,
        article_number="ART-001",
        file_path=test_file,
    )

    assert cert_dict["project_id"] == 1
    assert cert_dict["article_number"] == "ART-001"
    assert cert_dict["certificate_type"] == "Materialintyg"  # Auto-detected
    assert cert_dict["original_filename"] == "materialintyg_2024.pdf"
    assert cert_dict["file_path"] == str(test_file)


def test_create_certificate_dict_explicit_type(tmp_path):
    """Test creating certificate dict with explicit type."""
    test_file = tmp_path / "document.pdf"
    test_file.write_text("PDF content")

    cert_dict = create_certificate_dict(
        project_id=1,
        article_number="ART-001",
        file_path=test_file,
        certificate_type="Svetslogg",  # Explicit
        original_name="original_name.pdf",
    )

    assert cert_dict["certificate_type"] == "Svetslogg"
    assert cert_dict["original_filename"] == "original_name.pdf"


def test_get_certificates_summary():
    """Test getting certificate summary statistics."""
    certificates = [
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert1.pdf",
            certificate_type="Materialintyg",
            original_filename="cert1.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert2.pdf",
            certificate_type="Svetslogg",
            original_filename="cert2.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-002",
            file_path="/path/cert3.pdf",
            certificate_type="Materialintyg",
            original_filename="cert3.pdf",
        ),
    ]

    summary = get_certificates_summary(certificates)

    assert summary["total_count"] == 3
    assert summary["unique_types"] == 2
    assert summary["unique_articles"] == 2
    assert summary["by_type"]["Materialintyg"] == 2
    assert summary["by_type"]["Svetslogg"] == 1
    assert summary["by_article"]["ART-001"] == 2
    assert summary["by_article"]["ART-002"] == 1


def test_get_certificates_for_article():
    """Test filtering certificates by article number."""
    certificates = [
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert1.pdf",
            certificate_type="Materialintyg",
            original_filename="cert1.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-002",
            file_path="/path/cert2.pdf",
            certificate_type="Svetslogg",
            original_filename="cert2.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert3.pdf",
            certificate_type="Kontrollrapport",
            original_filename="cert3.pdf",
        ),
    ]

    result = get_certificates_for_article(certificates, "ART-001")

    assert len(result) == 2
    assert all(cert.article_number == "ART-001" for cert in result)


def test_get_certificates_by_type():
    """Test filtering certificates by type."""
    certificates = [
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert1.pdf",
            certificate_type="Materialintyg",
            original_filename="cert1.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-002",
            file_path="/path/cert2.pdf",
            certificate_type="Svetslogg",
            original_filename="cert2.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-003",
            file_path="/path/cert3.pdf",
            certificate_type="Materialintyg",
            original_filename="cert3.pdf",
        ),
    ]

    result = get_certificates_by_type(certificates, "Materialintyg")

    assert len(result) == 2
    assert all(cert.certificate_type == "Materialintyg" for cert in result)


def test_get_articles_with_certificates():
    """Test getting list of articles with certificates."""
    certificates = [
        Certificate(
            project_id=1,
            article_number="ART-003",
            file_path="/path/cert1.pdf",
            certificate_type="Materialintyg",
            original_filename="cert1.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert2.pdf",
            certificate_type="Svetslogg",
            original_filename="cert2.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert3.pdf",
            certificate_type="Kontrollrapport",
            original_filename="cert3.pdf",
        ),
    ]

    result = get_articles_with_certificates(certificates)

    assert result == ["ART-001", "ART-003"]  # Sorted, unique


def test_get_articles_without_certificates():
    """Test getting list of articles without certificates."""
    all_articles = ["ART-001", "ART-002", "ART-003", "ART-004"]

    certificates = [
        Certificate(
            project_id=1,
            article_number="ART-001",
            file_path="/path/cert1.pdf",
            certificate_type="Materialintyg",
            original_filename="cert1.pdf",
        ),
        Certificate(
            project_id=1,
            article_number="ART-003",
            file_path="/path/cert2.pdf",
            certificate_type="Svetslogg",
            original_filename="cert2.pdf",
        ),
    ]

    result = get_articles_without_certificates(all_articles, certificates)

    assert result == ["ART-002", "ART-004"]  # Sorted


def test_empty_certificates_list():
    """Test operations with empty certificate list."""
    summary = get_certificates_summary([])
    assert summary["total_count"] == 0
    assert summary["unique_types"] == 0

    result = get_certificates_for_article([], "ART-001")
    assert result == []

    result = get_articles_with_certificates([])
    assert result == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
