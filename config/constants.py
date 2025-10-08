"""
Application constants for Tobbes v2.

Centralized location for all application-wide constants.
"""

from pathlib import Path

# ==================== Application Info ====================

APP_NAME = "Tobbes v2 - Spårbarhetsguiden"
APP_VERSION = "2.0.0"
APP_ORGANIZATION = "FA-TEC"
APP_AUTHOR = "Tobbes"

# ==================== File Extensions ====================

EXCEL_EXTENSIONS = [".xlsx", ".xls"]
PDF_EXTENSIONS = [".pdf"]
ALLOWED_CERTIFICATE_EXTENSIONS = [".pdf", ".jpg", ".jpeg", ".png"]

# ==================== Default Values ====================

# Database filename (actual path computed by paths.get_database_path())
# Location: projects/sparbarhet.db (for portability)
DEFAULT_DATABASE_NAME = "sparbarhet.db"
DEFAULT_USER_NAME = "user"
DEFAULT_PDF_PAGE_SIZE = "A4"

# ==================== Validation Limits ====================

MAX_ARTICLE_NUMBER_LENGTH = 50
MAX_ORDER_NUMBER_LENGTH = 50
MAX_CHARGE_NUMBER_LENGTH = 50
MAX_DESCRIPTION_LENGTH = 500
MAX_NOTES_LENGTH = 5000
MAX_FILE_SIZE_MB = 100  # Max file size for certificates

MIN_QUANTITY = 0.0
MAX_QUANTITY = 999999.0

# ==================== Excel Column Names ====================

# Nivålista (BOM) columns
NIVALISTA_COLUMNS = {
    "article_number": ["Artikelnummer", "Art.nr", "Article Number"],
    "description": ["Benämning", "Beskrivning", "Description"],
    "quantity": ["Antal", "Qty", "Quantity"],
    "level": ["Nivå", "Level"],
}

# Lagerlogg (Inventory) columns
LAGERLOGG_COLUMNS = {
    "article_number": ["Artikelnummer", "Art.nr", "Article Number"],
    "charge_number": ["Chargenr", "Charge", "Batch"],
    "quantity": ["Antal", "Qty", "Quantity"],
    "location": ["Plats", "Location"],
    "received_date": ["Mottaget", "Received"],
}

# ==================== Certificate Types ====================

# Default global certificate types
DEFAULT_CERTIFICATE_TYPES = [
    "Materialintyg",
    "Svetslogg",
    "Kontrollrapport",
    "Provningsprotokoll",
    "Leverantörsintyg",
    "Kvalitetsintyg",
    "Andra handlingar",
]

# Keywords for auto-detection (from domain.rules)
CERTIFICATE_TYPE_KEYWORDS = {
    "materialintyg": "Materialintyg",
    "material": "Materialintyg",
    "3.1": "Materialintyg",
    "3.2": "Materialintyg",
    "certifikat": "Certifikat",
    "certificate": "Certifikat",
    "svets": "Svetslogg",
    "weld": "Svetslogg",
    "kontroll": "Kontrollrapport",
    "inspection": "Kontrollrapport",
    "provning": "Provningsprotokoll",
    "test": "Provningsprotokoll",
    "leverantör": "Leverantörsintyg",
    "supplier": "Leverantörsintyg",
    "kvalitet": "Kvalitetsintyg",
    "quality": "Kvalitetsintyg",
}

# ==================== UI Constants ====================

# Window sizes
WINDOW_MIN_WIDTH = 800
WINDOW_MIN_HEIGHT = 600
WINDOW_DEFAULT_WIDTH = 1024
WINDOW_DEFAULT_HEIGHT = 768

# Colors (for charge selector widget)
COLOR_GRAY = "#CCCCCC"  # Manual input (no choices)
COLOR_GREEN = "#90EE90"  # Matched (one choice)
COLOR_YELLOW = "#FFEB3B"  # Needs selection (multiple choices)

# ==================== Report Constants ====================

# Watermark settings
WATERMARK_TEXT = "FA-TEC"
WATERMARK_OPACITY = 0.05
WATERMARK_ROTATION = -45
WATERMARK_FONT_SIZE = 120

# PDF merge settings
PDF_MERGE_CHUNK_SIZE = 1024 * 1024  # 1 MB chunks for streaming
PDF_MAX_RETRIES = 3
PDF_RETRY_DELAY = 1  # seconds

# ==================== Paths ====================

# Relative to project root
# NOTE: Reports and certificates are now stored in projects/{project_id}/
# using config.paths module (not these legacy constants)
DATA_DIR = Path("data")
TEMP_DIR = Path("temp")

# ==================== Error Messages ====================

ERROR_MESSAGES = {
    "file_not_found": "Filen kunde inte hittas: {path}",
    "invalid_excel": "Ogiltig Excel-fil: {path}",
    "chrome_not_found": "Chrome/Chromium krävs för PDF-generering men kunde inte hittas.\n\nInstallera Chrome från: https://google.com/chrome",
    "database_error": "Databasfel: {error}",
    "validation_error": "Valideringsfel: {error}",
    "import_error": "Import misslyckades: {error}",
}

# ==================== Success Messages ====================

SUCCESS_MESSAGES = {
    "project_created": "Projekt skapat: {project_name}",
    "import_complete": "Importerade {count} artiklar",
    "report_generated": "Rapport genererad: {path}",
    "update_applied": "Uppdaterade {count} artiklar",
}
