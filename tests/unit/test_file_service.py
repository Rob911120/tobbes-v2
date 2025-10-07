"""
Unit tests for File Service.

Tests cover file validation, copying, deletion, and directory management.
"""

import pytest
from pathlib import Path
from domain.exceptions import ValidationError
from services.file_service import FileService


# ==================== Fixtures ====================


@pytest.fixture
def file_service(tmp_path):
    """Create FileService with temporary directory."""
    base_dir = tmp_path / "certificates"
    return FileService(base_dir)


@pytest.fixture
def sample_pdf(tmp_path):
    """Create sample PDF file."""
    pdf_file = tmp_path / "test_certificate.pdf"
    pdf_file.write_text("PDF content")
    return pdf_file


@pytest.fixture
def sample_large_file(tmp_path):
    """Create large file (> 10 MB)."""
    large_file = tmp_path / "large_file.pdf"
    # Create 15 MB file
    large_file.write_bytes(b"0" * (15 * 1024 * 1024))
    return large_file


# ==================== Validation Tests ====================


def test_validate_file_success(file_service, sample_pdf):
    """Test validating valid file."""
    result = file_service.validate_file(sample_pdf)
    assert result is True


def test_validate_file_with_allowed_extensions(file_service, sample_pdf):
    """Test validating file with allowed extensions."""
    result = file_service.validate_file(sample_pdf, allowed_extensions=['.pdf'])
    assert result is True


def test_validate_file_not_exists(file_service):
    """Test validating non-existent file."""
    with pytest.raises(ValidationError) as exc_info:
        file_service.validate_file(Path("/nonexistent/file.pdf"))

    assert "finns inte" in str(exc_info.value.message)


def test_validate_file_is_directory(file_service, tmp_path):
    """Test validating directory instead of file."""
    directory = tmp_path / "test_dir"
    directory.mkdir()

    with pytest.raises(ValidationError) as exc_info:
        file_service.validate_file(directory)

    assert "Inte en fil" in str(exc_info.value.message)


def test_validate_file_invalid_extension(file_service, tmp_path):
    """Test validating file with invalid extension."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Not a PDF")

    with pytest.raises(ValidationError) as exc_info:
        file_service.validate_file(txt_file, allowed_extensions=['.pdf'])

    assert "Ogiltig filtyp" in str(exc_info.value.message)


def test_validate_file_too_large(file_service, sample_large_file):
    """Test validating file that is too large."""
    with pytest.raises(ValidationError) as exc_info:
        file_service.validate_file(sample_large_file, max_size_mb=10)

    assert "för stor" in str(exc_info.value.message)


def test_validate_file_within_size_limit(file_service, sample_pdf):
    """Test validating file within size limit."""
    result = file_service.validate_file(sample_pdf, max_size_mb=10)
    assert result is True


# ==================== Copy Certificate Tests ====================


def test_copy_certificate_success(file_service, sample_pdf):
    """Test copying certificate successfully."""
    dest = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
    )

    # Check destination path structure
    assert "project_1" in str(dest)
    assert "article_ART-001" in str(dest)
    assert dest.exists()
    assert dest.read_text() == "PDF content"


def test_copy_certificate_preserve_name(file_service, sample_pdf):
    """Test copying certificate with preserved name."""
    dest = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
        preserve_name=True,
    )

    assert dest.name == sample_pdf.name


def test_copy_certificate_generate_name(file_service, sample_pdf):
    """Test copying certificate with generated name."""
    dest = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
        preserve_name=False,
    )

    # Should contain article number and timestamp
    assert "ART-001" in dest.name
    assert dest.suffix == ".pdf"


def test_copy_certificate_duplicate_handling(file_service, sample_pdf):
    """Test handling duplicate filenames."""
    # Copy first time
    dest1 = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
    )

    # Copy again - should create new file with counter
    dest2 = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
    )

    assert dest1 != dest2
    assert dest1.exists()
    assert dest2.exists()
    assert "_1" in dest2.name


def test_copy_certificate_sanitizes_article_number(file_service, sample_pdf):
    """Test that article number is sanitized in path."""
    dest = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART/001*TEST",  # Invalid chars
    )

    # Should have sanitized article number in path
    assert "article_ART_001_TEST" in str(dest) or "article_ART001TEST" in str(dest)


def test_copy_certificate_creates_directories(file_service, sample_pdf):
    """Test that necessary directories are created."""
    dest = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
    )

    # Check directory structure exists
    project_dir = file_service.base_dir / "project_1"
    article_dir = project_dir / "article_ART-001"

    assert project_dir.exists()
    assert article_dir.exists()


def test_copy_certificate_multiple_articles(file_service, sample_pdf):
    """Test copying certificates for multiple articles."""
    dest1 = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-001",
    )

    dest2 = file_service.copy_certificate(
        source_path=sample_pdf,
        project_id=1,
        article_number="ART-002",
    )

    assert "article_ART-001" in str(dest1)
    assert "article_ART-002" in str(dest2)
    assert dest1.exists()
    assert dest2.exists()


# ==================== Delete File Tests ====================


def test_delete_file_success(file_service):
    """Test deleting file successfully."""
    # Create test file
    test_file = file_service.base_dir / "test.pdf"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("test")

    result = file_service.delete_file(test_file)

    assert result is True
    assert not test_file.exists()


def test_delete_file_not_exists(file_service):
    """Test deleting non-existent file."""
    result = file_service.delete_file(file_service.base_dir / "nonexistent.pdf")
    assert result is False


def test_delete_file_outside_base_dir_safe_mode(file_service, tmp_path):
    """Test that safe mode prevents deleting files outside base_dir."""
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_text("test")

    with pytest.raises(ValidationError) as exc_info:
        file_service.delete_file(outside_file, safe=True)

    assert "utanför arbetskatalogen" in str(exc_info.value.message)
    assert outside_file.exists()  # File should still exist


def test_delete_file_outside_base_dir_unsafe_mode(file_service, tmp_path):
    """Test that unsafe mode allows deleting files outside base_dir."""
    outside_file = tmp_path / "outside.pdf"
    outside_file.write_text("test")

    result = file_service.delete_file(outside_file, safe=False)

    assert result is True
    assert not outside_file.exists()


# ==================== Cleanup Directories Tests ====================


def test_cleanup_empty_directories_success(file_service):
    """Test cleaning up empty article directories."""
    # Create empty article directories
    project_dir = file_service.base_dir / "project_1"
    article_dir1 = project_dir / "article_ART-001"
    article_dir2 = project_dir / "article_ART-002"

    article_dir1.mkdir(parents=True)
    article_dir2.mkdir(parents=True)

    # Cleanup
    removed = file_service.cleanup_empty_directories(project_id=1)

    assert removed == 2
    assert not article_dir1.exists()
    assert not article_dir2.exists()


def test_cleanup_empty_directories_preserves_non_empty(file_service):
    """Test that non-empty directories are preserved."""
    # Create article directory with file
    project_dir = file_service.base_dir / "project_1"
    article_dir = project_dir / "article_ART-001"
    article_dir.mkdir(parents=True)

    cert_file = article_dir / "cert.pdf"
    cert_file.write_text("certificate")

    # Cleanup - should not remove
    removed = file_service.cleanup_empty_directories(project_id=1)

    assert removed == 0
    assert article_dir.exists()
    assert cert_file.exists()


def test_cleanup_empty_directories_removes_project_dir(file_service):
    """Test that empty project directory is also removed."""
    # Create empty project directory
    project_dir = file_service.base_dir / "project_1"
    project_dir.mkdir(parents=True)

    # Cleanup
    removed = file_service.cleanup_empty_directories(project_id=1)

    assert not project_dir.exists()


def test_cleanup_empty_directories_nonexistent_project(file_service):
    """Test cleaning up non-existent project."""
    removed = file_service.cleanup_empty_directories(project_id=999)
    assert removed == 0


def test_cleanup_empty_directories_mixed(file_service):
    """Test cleanup with mix of empty and non-empty directories."""
    project_dir = file_service.base_dir / "project_1"

    # Empty directory
    empty_dir = project_dir / "article_ART-001"
    empty_dir.mkdir(parents=True)

    # Non-empty directory
    non_empty_dir = project_dir / "article_ART-002"
    non_empty_dir.mkdir(parents=True)
    cert_file = non_empty_dir / "cert.pdf"
    cert_file.write_text("certificate")

    # Cleanup
    removed = file_service.cleanup_empty_directories(project_id=1)

    assert removed == 1
    assert not empty_dir.exists()
    assert non_empty_dir.exists()


# ==================== Get Certificates Tests ====================


def test_get_project_certificates_success(file_service):
    """Test getting all certificates for a project."""
    # Create project with multiple articles and certificates
    project_dir = file_service.base_dir / "project_1"

    article1_dir = project_dir / "article_ART-001"
    article1_dir.mkdir(parents=True)
    (article1_dir / "cert1.pdf").write_text("cert1")
    (article1_dir / "cert2.pdf").write_text("cert2")

    article2_dir = project_dir / "article_ART-002"
    article2_dir.mkdir(parents=True)
    (article2_dir / "cert3.pdf").write_text("cert3")

    # Get certificates
    certs = file_service.get_project_certificates(project_id=1)

    assert len(certs) == 3
    assert all(cert.suffix == ".pdf" for cert in certs)


def test_get_project_certificates_empty_project(file_service):
    """Test getting certificates for project with no certificates."""
    certs = file_service.get_project_certificates(project_id=999)
    assert certs == []


def test_get_project_certificates_sorted(file_service):
    """Test that certificates are returned sorted."""
    project_dir = file_service.base_dir / "project_1"
    article_dir = project_dir / "article_ART-001"
    article_dir.mkdir(parents=True)

    # Create files in non-alphabetical order
    (article_dir / "cert_c.pdf").write_text("c")
    (article_dir / "cert_a.pdf").write_text("a")
    (article_dir / "cert_b.pdf").write_text("b")

    certs = file_service.get_project_certificates(project_id=1)

    # Should be sorted
    assert certs[0].name == "cert_a.pdf"
    assert certs[1].name == "cert_b.pdf"
    assert certs[2].name == "cert_c.pdf"


def test_get_article_certificates_success(file_service):
    """Test getting certificates for specific article."""
    project_dir = file_service.base_dir / "project_1"
    article_dir = project_dir / "article_ART-001"
    article_dir.mkdir(parents=True)

    (article_dir / "cert1.pdf").write_text("cert1")
    (article_dir / "cert2.pdf").write_text("cert2")

    # Get article certificates
    certs = file_service.get_article_certificates(project_id=1, article_number="ART-001")

    assert len(certs) == 2
    assert all(cert.suffix == ".pdf" for cert in certs)


def test_get_article_certificates_nonexistent_article(file_service):
    """Test getting certificates for non-existent article."""
    certs = file_service.get_article_certificates(project_id=1, article_number="ART-999")
    assert certs == []


def test_get_article_certificates_sanitizes_article_number(file_service):
    """Test that article number is sanitized when retrieving certificates."""
    project_dir = file_service.base_dir / "project_1"
    article_dir = project_dir / "article_ART-001"
    article_dir.mkdir(parents=True)
    (article_dir / "cert.pdf").write_text("cert")

    # Should work with sanitized article number
    certs = file_service.get_article_certificates(project_id=1, article_number="ART-001")
    assert len(certs) == 1


# ==================== Base Directory Tests ====================


def test_file_service_creates_base_dir(tmp_path):
    """Test that FileService creates base directory if missing."""
    base_dir = tmp_path / "new_certificates"

    service = FileService(base_dir)

    assert base_dir.exists()
    assert service.base_dir == base_dir


def test_file_service_accepts_existing_base_dir(tmp_path):
    """Test that FileService works with existing base directory."""
    base_dir = tmp_path / "certificates"
    base_dir.mkdir()

    service = FileService(base_dir)

    assert service.base_dir == base_dir
