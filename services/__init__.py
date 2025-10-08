"""
Services layer for Tobbes v2.

Infrastructure services that support operations and UI layers.
"""

from .chrome_checker import (
    has_system_chrome,
    get_chrome_path,
    ensure_chrome_installed,
    get_chrome_info,
    get_installation_instructions,
)

from .excel_reader import ExcelReader
from .pdf_service import PDFService, create_pdf_service

__all__ = [
    # Chrome Checker
    "has_system_chrome",
    "get_chrome_path",
    "ensure_chrome_installed",
    "get_chrome_info",
    "get_installation_instructions",
    # Excel Reader
    "ExcelReader",
    # PDF Service
    "PDFService",
    "create_pdf_service",
]
