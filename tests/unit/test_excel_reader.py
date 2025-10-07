"""
Unit tests for Excel Reader service.

Tests cover Excel file reading and parsing.
"""

import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.excel_reader import ExcelReader
from domain.exceptions import ImportValidationError, ValidationError


@pytest.fixture
def mock_nivalista_df():
    """Mock DataFrame for nivålista."""
    return pd.DataFrame({
        "Artikelnummer": ["ART-001", "ART-002", "ART-003"],
        "Benämning": ["Artikel 1", "Artikel 2", "Artikel 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": ["1", "1.1", "1.1.1"],
    })


@pytest.fixture
def mock_lagerlogg_df():
    """Mock DataFrame for lagerlogg."""
    return pd.DataFrame({
        "Artikelnummer": ["ART-001", "ART-002", "ART-001"],
        "Chargenummer": ["CHARGE-A", "CHARGE-B", "CHARGE-C"],
        "Antal": [100.0, 50.0, 75.0],
        "Plats": ["Lager A", "Lager B", "Lager A"],
    })


def test_excel_reader_init_with_valid_file(tmp_path):
    """Test ExcelReader initialization with valid file."""
    # Create a test Excel file
    test_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    assert reader.file_path == test_file


def test_excel_reader_init_with_invalid_extension(tmp_path):
    """Test ExcelReader raises error for invalid file extension."""
    test_file = tmp_path / "test.txt"
    test_file.touch()

    with pytest.raises(ValidationError) as exc_info:
        ExcelReader(test_file)

    assert "Invalid file extension" in str(exc_info.value)


def test_excel_reader_init_with_nonexistent_file(tmp_path):
    """Test ExcelReader raises error for non-existent file."""
    test_file = tmp_path / "nonexistent.xlsx"

    with pytest.raises(ValidationError):
        ExcelReader(test_file)


def test_read_dataframe(tmp_path):
    """Test reading DataFrame from Excel."""
    test_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    result = reader.read_dataframe()

    assert len(result) == 3
    assert "A" in result.columns
    assert "B" in result.columns


def test_clean_dataframe_removes_empty_rows(tmp_path):
    """Test that empty rows are removed."""
    test_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({
        "A": [1, None, 3],
        "B": [4, None, 6],
    })
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    result = reader.read_dataframe()

    # Should remove the completely empty middle row
    assert len(result) == 2


def test_read_nivalista_success(tmp_path, mock_nivalista_df):
    """Test reading nivålista successfully."""
    test_file = tmp_path / "nivalista.xlsx"
    mock_nivalista_df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    articles = reader.read_nivalista()

    assert len(articles) == 3
    assert articles[0]["article_number"] == "ART-001"
    assert articles[0]["description"] == "Artikel 1"
    assert articles[0]["quantity"] == 5.0
    assert articles[0]["level"] == "1"


def test_read_nivalista_missing_columns(tmp_path):
    """Test reading nivålista with missing required columns."""
    test_file = tmp_path / "invalid.xlsx"
    df = pd.DataFrame({"WrongColumn": [1, 2, 3]})
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)

    with pytest.raises(ImportValidationError) as exc_info:
        reader.read_nivalista()

    assert "Saknade kolumner" in str(exc_info.value)


def test_read_nivalista_skips_empty_rows(tmp_path):
    """Test that rows without article number are skipped."""
    test_file = tmp_path / "nivalista.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", None, "ART-003"],
        "Benämning": ["Art 1", "Art 2", "Art 3"],
        "Antal": [5.0, 10.0, 2.5],
        "Nivå": ["1", "2", "3"],
    })
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    articles = reader.read_nivalista()

    # Should skip the middle row (None article number)
    assert len(articles) == 2
    assert articles[0]["article_number"] == "ART-001"
    assert articles[1]["article_number"] == "ART-003"


def test_read_lagerlogg_success(tmp_path, mock_lagerlogg_df):
    """Test reading lagerlogg successfully."""
    test_file = tmp_path / "lagerlogg.xlsx"
    mock_lagerlogg_df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    items = reader.read_lagerlogg()

    assert len(items) == 3
    assert items[0]["article_number"] == "ART-001"
    assert items[0]["charge_number"] == "CHARGE-A"
    assert items[0]["quantity"] == 100.0
    assert items[0]["location"] == "Lager A"


def test_read_lagerlogg_missing_columns(tmp_path):
    """Test reading lagerlogg with missing required columns."""
    test_file = tmp_path / "invalid.xlsx"
    df = pd.DataFrame({"WrongColumn": [1, 2, 3]})
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)

    with pytest.raises(ImportValidationError) as exc_info:
        reader.read_lagerlogg()

    assert "Saknade kolumner" in str(exc_info.value)


def test_read_lagerlogg_skips_invalid_rows(tmp_path):
    """Test that rows without article/charge number are skipped."""
    test_file = tmp_path / "lagerlogg.xlsx"
    df = pd.DataFrame({
        "Artikelnummer": ["ART-001", None, "ART-003"],
        "Chargenummer": ["CHG-A", "CHG-B", None],
        "Antal": [100.0, 50.0, 75.0],
    })
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    items = reader.read_lagerlogg()

    # Should skip rows with missing article or charge
    assert len(items) == 1
    assert items[0]["article_number"] == "ART-001"


def test_get_sheet_names(tmp_path):
    """Test getting sheet names from Excel file."""
    test_file = tmp_path / "multi_sheet.xlsx"

    with pd.ExcelWriter(test_file) as writer:
        pd.DataFrame({"A": [1]}).to_excel(writer, sheet_name="Sheet1", index=False)
        pd.DataFrame({"B": [2]}).to_excel(writer, sheet_name="Sheet2", index=False)

    reader = ExcelReader(test_file)
    sheets = reader.get_sheet_names()

    assert len(sheets) == 2
    assert "Sheet1" in sheets
    assert "Sheet2" in sheets


def test_peek_columns(tmp_path):
    """Test peeking at columns."""
    test_file = tmp_path / "test.xlsx"
    df = pd.DataFrame({"A": [1, 2, 3, 4, 5], "B": [6, 7, 8, 9, 10]})
    df.to_excel(test_file, index=False)

    reader = ExcelReader(test_file)
    peek = reader.peek_columns(rows=3)

    assert len(peek) == 3
    assert "A" in peek.columns
    assert "B" in peek.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
