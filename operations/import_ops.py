"""
Import Operations for Tobbes v2.

Pure functions for importing and parsing Excel files.
No database access - returns parsed data structures.

According to plan (Week 2, Day 11):
- import_nivalista() - Import BOM/level list
- import_lagerlogg() - Import inventory log
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

from services.excel_reader import ExcelReader
from domain.models import Article, InventoryItem, GlobalArticle
from domain.exceptions import ImportValidationError
from domain.validators import (
    validate_file_path,
    validate_article_number,
    validate_charge_number,
    validate_quantity,
)

logger = logging.getLogger(__name__)


def import_nivalista(
    file_path: Path,
    article_col: str = "Artikelnummer",
    description_col: str = "Benämning",
    quantity_col: str = "Antal",
    level_col: str = "Nivå",
) -> List[Dict[str, Any]]:
    """
    Import nivålista (BOM/level list) from Excel.

    This is a PURE FUNCTION - no database access, no side effects.
    Returns parsed article data that can be saved to database separately.

    Args:
        file_path: Path to Excel file (.xlsx or .xls)
        article_col: Column name for article number
        description_col: Column name for description
        quantity_col: Column name for quantity
        level_col: Column name for level

    Returns:
        List of article dictionaries ready for database insertion

    Raises:
        ImportValidationError: If file is invalid or parsing fails

    Example:
        >>> articles = import_nivalista(Path("nivalista.xlsx"))
        >>> db.save_project_articles(project_id, articles)
    """
    logger.info(f"Importing nivålista from: {file_path}")

    # Validate file
    validate_file_path(file_path, must_exist=True, allowed_extensions=[".xlsx", ".xls"])

    # Read Excel file
    reader = ExcelReader(file_path)
    raw_articles = reader.read_nivalista(
        article_col=article_col,
        description_col=description_col,
        quantity_col=quantity_col,
        level_col=level_col,
    )

    # Validate and clean each article
    articles = []
    for idx, raw_article in enumerate(raw_articles):
        try:
            # Validate article number
            article_number = validate_article_number(raw_article["article_number"])

            # Validate quantity
            quantity = validate_quantity(
                raw_article.get("quantity", 0.0),
                allow_zero=True,
            )

            # Create clean article dict
            article = {
                "article_number": article_number,
                "description": raw_article.get("description", "").strip(),
                "quantity": quantity,
                "level": raw_article.get("level", "").strip(),
                "parent_article": raw_article.get("parent_article"),
            }

            articles.append(article)

        except Exception as e:
            logger.warning(f"Skipping invalid article at row {idx}: {e}")
            continue

    if not articles:
        raise ImportValidationError(
            "Inga giltiga artiklar hittades i nivålistan",
            details={"file": str(file_path)},
        )

    logger.info(f"Successfully imported {len(articles)} articles from nivålista")
    return articles


def import_lagerlogg(
    file_path: Path,
    article_col: str = "Artikelnummer",
    charge_col: str = "Chargenummer",
    quantity_col: str = "Antal",
    batch_col: str = "Batch",
    location_col: str = "Plats",
    date_col: str = "Datum",
) -> List[Dict[str, Any]]:
    """
    Import lagerlogg (inventory log) from Excel.

    This is a PURE FUNCTION - no database access, no side effects.
    Returns parsed inventory data that can be saved to database separately.

    Args:
        file_path: Path to Excel file (.xlsx or .xls)
        article_col: Column name for article number
        charge_col: Column name for charge number
        quantity_col: Column name for quantity
        batch_col: Column name for batch ID
        location_col: Column name for location
        date_col: Column name for received date

    Returns:
        List of inventory item dictionaries ready for database insertion

    Raises:
        ImportValidationError: If file is invalid or parsing fails

    Example:
        >>> inventory = import_lagerlogg(Path("lagerlogg.xlsx"))
        >>> db.save_inventory_items(project_id, inventory)
    """
    logger.info(f"Importing lagerlogg from: {file_path}")

    # Validate file
    validate_file_path(file_path, must_exist=True, allowed_extensions=[".xlsx", ".xls"])

    # Read Excel file
    reader = ExcelReader(file_path)
    raw_items = reader.read_lagerlogg(
        article_col=article_col,
        charge_col=charge_col,
        quantity_col=quantity_col,
        batch_col=batch_col,
        location_col=location_col,
        date_col=date_col,
    )

    # Validate and clean each inventory item
    inventory_items = []
    for idx, raw_item in enumerate(raw_items):
        try:
            # Validate article number
            article_number = validate_article_number(raw_item["article_number"])

            # Validate charge number
            charge_number = validate_charge_number(raw_item["charge_number"])

            # Validate quantity
            quantity = validate_quantity(
                raw_item.get("quantity", 0.0),
                allow_zero=True,
            )

            # Create clean inventory item dict
            item = {
                "article_number": article_number,
                "charge_number": charge_number,
                "quantity": quantity,
                "batch_id": raw_item.get("batch_id"),
                "location": raw_item.get("location"),
                "received_date": raw_item.get("received_date"),
            }

            inventory_items.append(item)

        except Exception as e:
            logger.warning(f"Skipping invalid inventory item at row {idx}: {e}")
            continue

    if not inventory_items:
        raise ImportValidationError(
            "Inga giltiga lagerloggar hittades",
            details={"file": str(file_path)},
        )

    logger.info(f"Successfully imported {len(inventory_items)} inventory items from lagerlogg")
    return inventory_items


def validate_import_file(file_path: Path, expected_type: str = "nivålista") -> bool:
    """
    Validate that an import file exists and has correct format.

    Args:
        file_path: Path to file
        expected_type: Expected file type ("nivålista" or "lagerlogg")

    Returns:
        True if file is valid

    Raises:
        ImportValidationError: If file is invalid
    """
    # Check file exists and has correct extension
    validate_file_path(file_path, must_exist=True, allowed_extensions=[".xlsx", ".xls"])

    # Try to peek at columns to verify structure
    try:
        reader = ExcelReader(file_path)
        peek = reader.peek_columns(rows=1)

        if expected_type == "nivålista":
            # Check for typical nivålista columns
            expected_cols = ["Artikelnummer", "Benämning", "Antal"]
            missing = [col for col in expected_cols if col not in peek.columns]
            if missing:
                raise ImportValidationError(
                    f"Nivålista saknar obligatoriska kolumner: {', '.join(missing)}",
                    details={"file": str(file_path), "missing": missing},
                )

        elif expected_type == "lagerlogg":
            # Check for typical lagerlogg columns
            expected_cols = ["Artikelnummer", "Chargenummer", "Antal"]
            missing = [col for col in expected_cols if col not in peek.columns]
            if missing:
                raise ImportValidationError(
                    f"Lagerlogg saknar obligatoriska kolumner: {', '.join(missing)}",
                    details={"file": str(file_path), "missing": missing},
                )

        return True

    except Exception as e:
        raise ImportValidationError(
            f"Kunde inte validera importfil: {e}",
            details={"file": str(file_path), "type": expected_type},
        )


def get_import_summary(articles: List[Dict[str, Any]] = None, inventory: List[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get summary statistics for imported data.

    Useful for displaying to user before saving to database.

    Args:
        articles: Imported articles from nivålista
        inventory: Imported inventory items from lagerlogg

    Returns:
        Dict with summary statistics

    Example:
        >>> articles = import_nivalista(file)
        >>> summary = get_import_summary(articles=articles)
        >>> print(f"Imported {summary['article_count']} articles")
    """
    summary = {}

    if articles:
        summary["article_count"] = len(articles)
        summary["unique_articles"] = len(set(a["article_number"] for a in articles))
        summary["total_quantity"] = sum(a.get("quantity", 0.0) for a in articles)
        summary["articles_with_level"] = sum(1 for a in articles if a.get("level"))

    if inventory:
        summary["inventory_count"] = len(inventory)
        summary["unique_charges"] = len(set(i["charge_number"] for i in inventory))
        summary["unique_articles_in_inventory"] = len(set(i["article_number"] for i in inventory))
        summary["total_inventory_quantity"] = sum(i.get("quantity", 0.0) for i in inventory)

    return summary
