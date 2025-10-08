"""
Excel Reader Service.

Handles reading and parsing Excel files for:
- Nivålista (Bill of Materials / BOM)
- Lagerlogg (Inventory log)

Uses pandas and openpyxl for Excel processing.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from domain.exceptions import ImportValidationError
from domain.validators import validate_file_path

logger = logging.getLogger(__name__)


# Column name mappings for flexible matching
ARTICLE_NUMBER_VARIANTS = ['artikelnummer', 'artikel', 'art.nr', 'artikel/operation']
DESCRIPTION_VARIANTS = ['benämning', 'artikelbenämning', 'beskrivning', 'description']
QUANTITY_VARIANTS = ['antal', 'kvantitet', 'quantity', 'qty', 'saldoförändring']
CHARGE_VARIANTS = ['chargenummer', 'charge']  # Charge and batch are separate concepts
BATCH_VARIANTS = ['batchnummer', 'batch', 'batch_id', 'batchnr', 'batch_number']
LEVEL_VARIANTS = ['nivå', 'level', 'outline_level']


class ExcelReader:
    """
    Excel file reader with support for nivålista and lagerlogg formats.

    This class provides methods to read and parse Excel files into
    standardized dictionary formats.
    """

    def __init__(self, file_path: Path):
        """
        Initialize Excel reader.

        Args:
            file_path: Path to Excel file (.xlsx or .xls)

        Raises:
            ImportValidationError: If file is invalid or doesn't exist
        """
        self.file_path = validate_file_path(
            file_path,
            must_exist=True,
            allowed_extensions=[".xlsx", ".xls"],
        )
        logger.info(f"Initialized Excel reader for: {self.file_path}")

    def _find_column(self, columns: List[str], search_terms: List[str]) -> Optional[str]:
        """
        Find column name using flexible matching.

        Tries exact match first, then partial match (case-insensitive).
        Matches v1 behavior for column detection.

        Args:
            columns: Available column names in DataFrame
            search_terms: List of possible column name variations to search for

        Returns:
            Matched column name, or None if not found
        """
        # Try exact matches first
        for term in search_terms:
            for col in columns:
                if term.lower() == str(col).lower():
                    logger.debug(f"Found exact match: '{col}' for search term '{term}'")
                    return col

        # Then try partial matches
        for term in search_terms:
            for col in columns:
                col_lower = str(col).lower()
                if term.lower() in col_lower:
                    logger.debug(f"Found partial match: '{col}' contains '{term}'")
                    return col

        return None

    def read_dataframe(
        self,
        sheet_name: Optional[str] = None,
        header_row: int = 0,
        skip_rows: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        """
        Read Excel file into pandas DataFrame.

        Args:
            sheet_name: Sheet to read (None = first sheet)
            header_row: Row index for column headers (0-indexed)
            skip_rows: Rows to skip

        Returns:
            DataFrame with cleaned data

        Raises:
            ImportValidationError: If file cannot be read
        """
        try:
            df = pd.read_excel(
                self.file_path,
                sheet_name=sheet_name or 0,
                header=header_row,
                skiprows=skip_rows,
            )

            # Clean dataframe
            df = self._clean_dataframe(df)

            logger.debug(f"Read {len(df)} rows from {self.file_path.name}")
            return df

        except Exception as e:
            raise ImportValidationError(
                f"Kunde inte läsa Excel-fil: {e}",
                details={"file": str(self.file_path), "error": str(e)},
            )

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean DataFrame by removing empty rows and standardizing columns.

        Args:
            df: Input DataFrame

        Returns:
            Cleaned DataFrame
        """
        # Remove completely empty rows
        df = df.dropna(how="all")

        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == "object":
                df[col] = df[col].str.strip() if hasattr(df[col], "str") else df[col]

        # Replace NaN with None for better handling
        df = df.where(pd.notnull(df), None)

        return df

    def _safe_str(self, value, default: str = "") -> str:
        """
        Convert value to string safely, handling None/NaN.

        This prevents str(None) → "None" (the string) which causes UI issues.

        Args:
            value: Value to convert (can be None, NaN, or any value)
            default: Default string if value is None/NaN (default: "")

        Returns:
            String value or default

        Examples:
            >>> _safe_str(None) → ""
            >>> _safe_str("ABC123") → "ABC123"
            >>> _safe_str(pd.NA) → ""
            >>> _safe_str(123) → "123"
        """
        if value is None:
            return default
        # Check for pandas NaN/NA
        if hasattr(value, '__class__') and pd.isna(value):
            return default
        return str(value).strip()

    def read_nivalista(
        self,
        article_col: str = "Artikelnummer",
        description_col: str = "Benämning",
        quantity_col: str = "Antal",
        level_col: str = "Nivå",
        parent_col: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read nivålista (BOM) from Excel file with flexible column matching.

        Automatically detects column names using common variations:
        - Artikelnummer: 'artikelnummer', 'artikel', 'art.nr', 'artikel/operation'
        - Benämning: 'benämning', 'artikelbenämning', 'beskrivning'
        - Antal/Kvantitet: 'antal', 'kvantitet', 'quantity', 'qty'
        - Nivå: 'nivå', 'level', 'outline_level' (optional)

        Args:
            article_col: Fallback column name for article number
            description_col: Fallback column name for description
            quantity_col: Fallback column name for quantity
            level_col: Fallback column name for level
            parent_col: Column name for parent article (optional)

        Returns:
            List of article dictionaries

        Raises:
            ImportValidationError: If required columns cannot be found
        """
        df = self.read_dataframe()
        columns = list(df.columns)

        logger.info(f"Available columns in nivålista: {columns}")

        # Find columns using flexible matching
        article_col_found = self._find_column(columns, ARTICLE_NUMBER_VARIANTS) or article_col
        description_col_found = self._find_column(columns, DESCRIPTION_VARIANTS) or description_col
        quantity_col_found = self._find_column(columns, QUANTITY_VARIANTS) or quantity_col
        level_col_found = self._find_column(columns, LEVEL_VARIANTS)  # Optional

        # Validate required columns exist
        required_mapping = {
            'Artikelnummer': article_col_found,
            'Benämning': description_col_found,
            'Antal/Kvantitet': quantity_col_found,
        }

        missing_cols = []
        for field_name, col_name in required_mapping.items():
            if col_name not in df.columns:
                missing_cols.append(field_name)
                logger.error(f"Required column '{field_name}' not found (tried: {col_name})")

        if missing_cols:
            raise ImportValidationError(
                f"Saknade kolumner i nivålista: {', '.join(missing_cols)}",
                details={
                    "file": str(self.file_path),
                    "missing": missing_cols,
                    "available": columns,
                },
            )

        logger.info(f"Using columns - Article: '{article_col_found}', "
                   f"Description: '{description_col_found}', "
                   f"Quantity: '{quantity_col_found}', "
                   f"Level: '{level_col_found or 'N/A'}'")

        articles = []
        for idx, row in df.iterrows():
            article_number = row.get(article_col_found)
            if not article_number or pd.isna(article_number):
                logger.warning(f"Skipping row {idx}: No article number")
                continue

            # Handle quantity with explicit NaN check (v1 compatibility)
            qty_raw = row.get(quantity_col_found, 0.0)
            quantity = 0.0 if pd.isna(qty_raw) else float(qty_raw or 0.0)

            article = {
                "article_number": self._safe_str(article_number),
                "description": self._safe_str(row.get(description_col_found)),
                "quantity": quantity,
                "level": self._safe_str(row.get(level_col_found)) if level_col_found and level_col_found in df.columns else "",
                "parent_article": self._safe_str(row.get(parent_col)) if parent_col and parent_col in df.columns else None,
            }

            articles.append(article)

        logger.info(f"Parsed {len(articles)} articles from nivålista")
        return articles

    def read_lagerlogg(
        self,
        article_col: str = "Artikelnummer",
        charge_col: str = "Chargenummer",
        quantity_col: str = "Antal",
        batch_col: Optional[str] = "Batch",
        location_col: Optional[str] = "Plats",
        date_col: Optional[str] = "Datum",
    ) -> List[Dict[str, Any]]:
        """
        Read lagerlogg (inventory log) from Excel file with flexible column matching.

        Automatically detects column names using common variations:
        - Artikelnummer: 'artikelnummer', 'artikel', 'art.nr'
        - Chargenummer: 'chargenummer', 'charge' (separate from batch)
        - Antal: 'antal', 'kvantitet', 'saldoförändring', 'quantity'
        - Batchnummer: 'batchnummer', 'batch', 'batch_id', 'batchnr' (optional)
        - Additional optional columns: Plats, Datum

        Args:
            article_col: Fallback column name for article number
            charge_col: Fallback column name for charge number
            quantity_col: Fallback column name for quantity
            batch_col: Fallback column name for batch ID (optional, uses flexible matching)
            location_col: Column name for location
            date_col: Column name for received date

        Returns:
            List of inventory item dictionaries

        Raises:
            ImportValidationError: If required columns cannot be found
        """
        df = self.read_dataframe()
        columns = list(df.columns)

        logger.info(f"Available columns in lagerlogg: {columns}")

        # Find columns using flexible matching
        article_col_found = self._find_column(columns, ARTICLE_NUMBER_VARIANTS) or article_col
        charge_col_found = self._find_column(columns, CHARGE_VARIANTS) or charge_col
        quantity_col_found = self._find_column(columns, QUANTITY_VARIANTS) or quantity_col
        batch_col_found = self._find_column(columns, BATCH_VARIANTS)  # Optional - can be None

        # Validate required columns exist
        required_mapping = {
            'Artikelnummer': article_col_found,
            'Chargenummer': charge_col_found,
            'Antal': quantity_col_found,
        }

        missing_cols = []
        for field_name, col_name in required_mapping.items():
            if col_name not in df.columns:
                missing_cols.append(field_name)
                logger.error(f"Required column '{field_name}' not found (tried: {col_name})")

        if missing_cols:
            raise ImportValidationError(
                f"Saknade kolumner i lagerlogg: {', '.join(missing_cols)}",
                details={
                    "file": str(self.file_path),
                    "missing": missing_cols,
                    "available": columns,
                },
            )

        logger.info(f"Using columns - Article: '{article_col_found}', "
                   f"Charge: '{charge_col_found}', "
                   f"Quantity: '{quantity_col_found}', "
                   f"Batch: '{batch_col_found or 'N/A'}'")

        inventory_items = []
        for idx, row in df.iterrows():
            article_number = row.get(article_col_found)
            charge_number = row.get(charge_col_found)

            if not article_number or pd.isna(article_number):
                logger.warning(f"Skipping row {idx}: No article number")
                continue

            # Allow empty charge number (v1 compatibility)
            # Lagerlogg may have rows without charge (admin posts, articles in receiving, etc.)
            if not charge_number or pd.isna(charge_number):
                charge_number = ""  # Empty string instead of skipping
                logger.debug(f"Row {idx}: No charge number, using empty string")

            # Handle quantity with explicit NaN check (v1 compatibility)
            # Note: lagerlogg quantities can be negative (withdrawals)
            qty_raw = row.get(quantity_col_found, 0.0)
            quantity = 0.0 if pd.isna(qty_raw) else float(qty_raw or 0.0)

            item = {
                "article_number": self._safe_str(article_number),
                "charge_number": self._safe_str(charge_number),
                "quantity": quantity,
                "batch_id": self._safe_str(row.get(batch_col_found)) if batch_col_found and batch_col_found in df.columns else None,
                "location": self._safe_str(row.get(location_col)) if location_col and location_col in df.columns else None,
                "received_date": row.get(date_col) if date_col and date_col in df.columns else None,
            }

            inventory_items.append(item)

        logger.info(f"Parsed {len(inventory_items)} inventory items from lagerlogg")
        return inventory_items

    def get_sheet_names(self) -> List[str]:
        """
        Get list of sheet names in Excel file.

        Returns:
            List of sheet names
        """
        try:
            excel_file = pd.ExcelFile(self.file_path)
            return excel_file.sheet_names
        except Exception as e:
            raise ImportValidationError(
                f"Kunde inte läsa ark-namn från Excel: {e}",
                details={"file": str(self.file_path)},
            )

    def peek_columns(self, sheet_name: Optional[str] = None, rows: int = 5) -> pd.DataFrame:
        """
        Peek at first few rows to see column structure.

        Useful for debugging import issues.

        Args:
            sheet_name: Sheet to peek at (None = first sheet)
            rows: Number of rows to show

        Returns:
            DataFrame with first N rows
        """
        df = self.read_dataframe(sheet_name=sheet_name)
        return df.head(rows)
