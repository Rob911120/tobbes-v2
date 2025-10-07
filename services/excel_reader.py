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

    def read_nivalista(
        self,
        article_col: str = "Artikelnummer",
        description_col: str = "Benämning",
        quantity_col: str = "Antal",
        level_col: str = "Nivå",
        parent_col: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Read nivålista (BOM) from Excel file.

        Expected columns:
        - Artikelnummer: Article number
        - Benämning: Description
        - Antal: Quantity
        - Nivå: Level (e.g., "1", "1.1", "1.1.1")

        Args:
            article_col: Column name for article number
            description_col: Column name for description
            quantity_col: Column name for quantity
            level_col: Column name for level
            parent_col: Column name for parent article (optional)

        Returns:
            List of article dictionaries

        Raises:
            ImportValidationError: If required columns are missing
        """
        df = self.read_dataframe()

        # Validate required columns
        required_cols = [article_col, description_col, quantity_col]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            raise ImportValidationError(
                f"Saknade kolumner i nivålista: {', '.join(missing_cols)}",
                details={
                    "file": str(self.file_path),
                    "missing": missing_cols,
                    "available": list(df.columns),
                },
            )

        articles = []
        for idx, row in df.iterrows():
            article_number = row.get(article_col)
            if not article_number or pd.isna(article_number):
                logger.warning(f"Skipping row {idx}: No article number")
                continue

            article = {
                "article_number": str(article_number).strip(),
                "description": str(row.get(description_col, "")).strip(),
                "quantity": float(row.get(quantity_col, 0.0) or 0.0),
                "level": str(row.get(level_col, "")).strip() if level_col in df.columns else "",
                "parent_article": str(row.get(parent_col, "")).strip() if parent_col and parent_col in df.columns else None,
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
        Read lagerlogg (inventory log) from Excel file.

        Expected columns:
        - Artikelnummer: Article number
        - Chargenummer: Charge/batch number
        - Antal: Quantity
        - Batch: Batch ID (optional)
        - Plats: Location (optional)
        - Datum: Received date (optional)

        Args:
            article_col: Column name for article number
            charge_col: Column name for charge number
            quantity_col: Column name for quantity
            batch_col: Column name for batch ID
            location_col: Column name for location
            date_col: Column name for received date

        Returns:
            List of inventory item dictionaries

        Raises:
            ImportValidationError: If required columns are missing
        """
        df = self.read_dataframe()

        # Validate required columns
        required_cols = [article_col, charge_col, quantity_col]
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            raise ImportValidationError(
                f"Saknade kolumner i lagerlogg: {', '.join(missing_cols)}",
                details={
                    "file": str(self.file_path),
                    "missing": missing_cols,
                    "available": list(df.columns),
                },
            )

        inventory_items = []
        for idx, row in df.iterrows():
            article_number = row.get(article_col)
            charge_number = row.get(charge_col)

            if not article_number or pd.isna(article_number):
                logger.warning(f"Skipping row {idx}: No article number")
                continue

            if not charge_number or pd.isna(charge_number):
                logger.warning(f"Skipping row {idx}: No charge number")
                continue

            item = {
                "article_number": str(article_number).strip(),
                "charge_number": str(charge_number).strip(),
                "quantity": float(row.get(quantity_col, 0.0) or 0.0),
                "batch_id": str(row.get(batch_col, "")).strip() if batch_col and batch_col in df.columns else None,
                "location": str(row.get(location_col, "")).strip() if location_col and location_col in df.columns else None,
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
