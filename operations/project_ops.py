"""
Project Operations for Tobbes v2.

Operations for managing project folders and metadata.
Pure functions with minimal side effects.
"""

import logging
from pathlib import Path
from config.paths import get_project_path, sanitize_order_number, get_project_base_path

logger = logging.getLogger(__name__)


def rename_project_folder(old_order_number: str, new_order_number: str) -> bool:
    """
    Byt namn på projektmapp när ordernummer ändras.

    Flyttar hela projektmappen (inkl. certifikat, rapporter etc.) till nytt namn.

    Args:
        old_order_number: Gammalt ordernummer (befintligt mappnamn)
        new_order_number: Nytt ordernummer (nytt mappnamn)

    Returns:
        bool: True om lyckades

    Raises:
        FileNotFoundError: Om gammal mapp inte finns
        FileExistsError: Om ny mapp redan finns
        OSError: Om rename operation misslyckades

    Example:
        >>> rename_project_folder("TO-2024-001", "TO-2024-002")
        True
    """
    # Sanitize order numbers (ta bort ogiltiga tecken)
    old_safe = sanitize_order_number(old_order_number)
    new_safe = sanitize_order_number(new_order_number)

    # Konstruera sökvägar (utan att skapa mapparna)
    old_path = get_project_base_path() / old_safe
    new_path = get_project_base_path() / new_safe

    # Validera att gamla mappen finns
    if not old_path.exists():
        raise FileNotFoundError(
            f"Projektmapp saknas: {old_path}\n"
            f"Ordernummer: {old_order_number}"
        )

    # Validera att nya mappen inte finns
    if new_path.exists():
        raise FileExistsError(
            f"Målmapp finns redan: {new_path}\n"
            f"Ordernummer: {new_order_number}\n"
            f"Välj ett annat ordernummer eller ta bort befintlig mapp."
        )

    # Byt namn på mappen
    try:
        old_path.rename(new_path)
        logger.info(
            f"Renamed project folder: {old_order_number} → {new_order_number}\n"
            f"Path: {old_path} → {new_path}"
        )
        return True

    except OSError as e:
        logger.exception(f"Failed to rename project folder: {old_path} → {new_path}")
        raise OSError(f"Kunde inte byta namn på projektmapp: {e}")
