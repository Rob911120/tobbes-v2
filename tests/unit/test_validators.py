"""
Unit tests for domain validators.

Tests cover validation logic and error handling.
"""

import pytest
from pathlib import Path

from domain.validators import (
    validate_order_number,
    validate_article_number,
    validate_charge_number,
    validate_quantity,
    validate_file_path,
    validate_level_number,
    validate_certificate_type,
    sanitize_filename,
)
from domain.exceptions import ValidationError


def test_validate_order_number_valid():
    """Test valid order numbers."""
    assert validate_order_number("TO-12345") == "TO-12345"
    assert validate_order_number("to-12345") == "TO-12345"  # Uppercased
    assert validate_order_number("  TO-12345  ") == "TO-12345"  # Trimmed
    assert validate_order_number("TO-123456") == "TO-123456"  # 6 digits OK


def test_validate_order_number_invalid():
    """Test invalid order numbers."""
    with pytest.raises(ValidationError):
        validate_order_number("")  # Empty

    with pytest.raises(ValidationError):
        validate_order_number("TO-123")  # Too short

    with pytest.raises(ValidationError):
        validate_order_number("TO-ABC")  # Not numeric

    with pytest.raises(ValidationError):
        validate_order_number("12345")  # Missing prefix


def test_validate_article_number_valid():
    """Test valid article numbers."""
    assert validate_article_number("ART-001") == "ART-001"
    assert validate_article_number("  ART-001  ") == "ART-001"  # Trimmed
    assert validate_article_number("ART_123-ABC") == "ART_123-ABC"


def test_validate_article_number_invalid():
    """Test invalid article numbers."""
    with pytest.raises(ValidationError):
        validate_article_number("")  # Empty

    with pytest.raises(ValidationError):
        validate_article_number("A" * 51)  # Too long

    with pytest.raises(ValidationError):
        validate_article_number("ART@001")  # Invalid character


def test_validate_charge_number():
    """Test charge number validation."""
    assert validate_charge_number("CHARGE-A") == "CHARGE-A"
    assert validate_charge_number("  CHARGE-A  ") == "CHARGE-A"

    with pytest.raises(ValidationError):
        validate_charge_number("")  # Empty

    with pytest.raises(ValidationError):
        validate_charge_number("C" * 31)  # Too long


def test_validate_quantity():
    """Test quantity validation."""
    assert validate_quantity(10.5) == 10.5
    assert validate_quantity(0) == 0
    assert validate_quantity(0, allow_zero=True) == 0

    with pytest.raises(ValidationError):
        validate_quantity(-1)  # Negative

    with pytest.raises(ValidationError):
        validate_quantity(0, allow_zero=False)  # Zero not allowed


def test_validate_file_path(tmp_path):
    """Test file path validation."""
    # Create a test file
    test_file = tmp_path / "test.pdf"
    test_file.touch()

    # Valid path
    validated = validate_file_path(test_file, must_exist=True)
    assert validated == test_file

    # Non-existent file (must_exist=False)
    non_existent = tmp_path / "missing.pdf"
    validated = validate_file_path(non_existent, must_exist=False)
    assert validated == non_existent

    # Non-existent file (must_exist=True) - should fail
    with pytest.raises(ValidationError):
        validate_file_path(non_existent, must_exist=True)

    # Wrong extension
    with pytest.raises(ValidationError):
        validate_file_path(test_file, allowed_extensions=[".xlsx", ".xls"])

    # Correct extension
    validated = validate_file_path(test_file, allowed_extensions=[".pdf"])
    assert validated == test_file


def test_validate_level_number():
    """Test BOM level validation."""
    assert validate_level_number("1") == "1"
    assert validate_level_number("1.1") == "1.1"
    assert validate_level_number("1.1.1") == "1.1.1"
    assert validate_level_number("  1.2.3  ") == "1.2.3"
    assert validate_level_number("") == ""  # Empty OK

    with pytest.raises(ValidationError):
        validate_level_number("1.a")  # Non-numeric

    with pytest.raises(ValidationError):
        validate_level_number("1..1")  # Double dot


def test_validate_certificate_type():
    """Test certificate type validation."""
    assert validate_certificate_type("Materialintyg") == "Materialintyg"
    assert validate_certificate_type("  Materialintyg  ") == "Materialintyg"

    with pytest.raises(ValidationError):
        validate_certificate_type("")  # Empty

    with pytest.raises(ValidationError):
        validate_certificate_type("A" * 101)  # Too long


def test_sanitize_filename():
    """Test filename sanitization."""
    assert sanitize_filename("test.pdf") == "test.pdf"
    assert sanitize_filename("test/file.pdf") == "test_file.pdf"
    assert sanitize_filename("test\\file.pdf") == "test_file.pdf"
    assert sanitize_filename('test:file"?.pdf') == "test_file__.pdf"
    assert sanitize_filename("  .test.pdf  ") == "test.pdf"  # Leading dot removed

    # Long filename
    long_name = "a" * 300 + ".pdf"
    sanitized = sanitize_filename(long_name)
    assert len(sanitized) <= 255
    assert sanitized.endswith(".pdf")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
