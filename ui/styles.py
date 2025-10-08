"""
UI Styles for Tobbes v2.

Centralized Qt stylesheet definitions and CSS for HTML reports.
Uses v1's professional CSS with design system, print optimization, and watermark support.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple

from config.constants import (
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_YELLOW,
)

logger = logging.getLogger(__name__)


# ==================== Qt Stylesheet ====================

MAIN_STYLESHEET = """
QMainWindow, QDialog, QWizard {
    background-color: #f5f5f5;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 10pt;
}

QPushButton {
    background-color: #0078d4;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #106ebe;
}

QPushButton:pressed {
    background-color: #005a9e;
}

QPushButton:disabled {
    background-color: #cccccc;
    color: #666666;
}

QLineEdit, QTextEdit, QComboBox {
    border: 1px solid #cccccc;
    border-radius: 4px;
    padding: 6px;
    background-color: white;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 2px solid #0078d4;
}

QTableWidget {
    border: 1px solid #cccccc;
    border-radius: 4px;
    background-color: white;
    gridline-color: #e0e0e0;
}

QTableWidget::item {
    padding: 4px;
}

QTableWidget::item:selected {
    background-color: #0078d4;
    color: white;
}

QHeaderView::section {
    background-color: #f0f0f0;
    padding: 6px;
    border: 1px solid #cccccc;
    font-weight: bold;
}

QGroupBox {
    font-weight: bold;
    border: 2px solid #cccccc;
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 8px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px 0 5px;
}

QProgressBar {
    border: 1px solid #cccccc;
    border-radius: 4px;
    text-align: center;
    background-color: white;
}

QProgressBar::chunk {
    background-color: #0078d4;
    border-radius: 3px;
}

QLabel {
    color: #333333;
}

QLabel.header {
    font-size: 14pt;
    font-weight: bold;
    color: #0078d4;
}

QLabel.subheader {
    font-size: 11pt;
    font-weight: bold;
    color: #666666;
}

QLabel.error {
    color: #d13438;
    font-weight: bold;
}

QLabel.success {
    color: #107c10;
    font-weight: bold;
}

QLabel.warning {
    color: #ff8c00;
    font-weight: bold;
}
"""


# ==================== Charge Selector Styles ====================

def get_charge_selector_style(state: str) -> str:
    """
    Get stylesheet for charge selector based on state.

    Args:
        state: "gray" (manual), "green" (matched), or "yellow" (multiple)

    Returns:
        Qt stylesheet string
    """
    color_map = {
        "gray": COLOR_GRAY,
        "green": COLOR_GREEN,
        "yellow": COLOR_YELLOW,
    }

    bg_color = color_map.get(state, COLOR_GRAY)

    return f"""
    QComboBox {{
        background-color: {bg_color};
        border: 2px solid #999999;
        border-radius: 4px;
        padding: 6px;
    }}

    QComboBox:focus {{
        border: 2px solid #0078d4;
    }}
    """


# ==================== HTML Report CSS ====================

REPORT_CSS = """
<style>
/* === GRUNDLÄGGANDE DESIGN SYSTEM === */
:root {
    /* Färger */
    --color-primary: #007bff;
    --color-dark: #333;
    --color-text: #000;
    --color-text-muted: #6c757d;
    --color-white: #fff;
    --color-border: #dee2e6;
    --color-background-alt: #f8f9fa;
    --color-shadow: rgba(0, 0, 0, 0.1);

    /* Typsnitt */
    --font-family-sans: 'Helvetica', Arial, sans-serif;
    --font-family-mono: 'Courier New', monospace;
    --font-size-base: 12px;
    --font-size-small: 0.85rem;

    /* Layout */
    --border-radius: 4px;
    --spacing-s: 8px;
    --spacing-m: 16px;
    --spacing-l: 24px;
    --spacing-xl: 32px;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

@page {
    size: A4;
    margin: 8mm;
}

body {
    font-family: var(--font-family-sans);
    font-size: var(--font-size-base);
    line-height: 1.4;
    color: var(--color-text);
}

/* === PRINT-OPTIMERING === */

/* Förhindra sidbrytningar för kritiska element */
.page-header h1,
.page-header h2 {
    page-break-after: avoid;
}

/* Förhindra ensamma rader (orphans/widows) */
p, li {
    orphans: 3;
    widows: 3;
}

/* === KOMPONENTER === */

/* Sidhuvud - Används på alla sidor som behöver en titel */
.page-header {
    position: relative;
    text-align: center;
    padding-bottom: var(--spacing-m);
    margin-bottom: var(--spacing-l);
    border-bottom: 2px solid var(--color-primary);
}

.page-header__title {
    color: var(--color-primary);
    font-size: 1.8rem; /* 28px */
    text-transform: uppercase;
    letter-spacing: 2px;
}

.page-header__subtitle {
    font-size: 1.1rem;
    color: var(--color-text-muted);
    font-weight: normal;
}

/* Informationsblock - För projektdata, datum etc. */
.info-block {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-m);
    font-size: 0.9rem;
}

.info-block__project {
    font-weight: bold;
}

.info-block__meta {
    text-align: right;
    color: var(--color-text-muted);
}

/* Centrerad innehållsbox - För skiljeblad */
.content-box {
    text-align: center;
    padding: var(--spacing-xl);
    background: var(--color-white);
    border: 1px solid var(--color-border);
    border-radius: var(--border-radius);
    box-shadow: 0 4px 6px var(--color-shadow);
    max-width: 650px;
    margin: 2rem auto;
}

/* Särskild styling för enkla dividers - print-optimerad */
.divider-page {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    background: var(--color-white);
}

.divider-page .content-box {
    border: 3px solid var(--color-primary);
    border-radius: var(--border-radius);
    box-shadow: none;
}

.divider-page .page-header__title {
    font-size: 2.5rem;
    margin-bottom: var(--spacing-l);
    text-transform: uppercase;
    letter-spacing: 2px;
}

/* Sidfot */
.page-footer {
    margin-top: var(--spacing-l);
    padding-top: var(--spacing-m);
    text-align: center;
    border-top: 1px solid var(--color-border);
    color: var(--color-text-muted);
    font-size: var(--font-size-small);
}

/* === VATTENSTÄMPEL === */

/* FA-TEC logga som STOR diagonal vattenstämpel */
body.with-watermark::before {
    content: "";
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate(-45deg);
    width: 150%;  /* Mycket större än sidan */
    height: 150%;
    background-image: url('LOGO_BASE64_PLACEHOLDER');
    background-repeat: no-repeat;
    background-position: center;
    background-size: 70%;  /* Stor logga som täcker det mesta */
    opacity: 0.08;  /* 8% synlighet - mycket svag men synlig */
    z-index: -1;
    pointer-events: none;
}

/* Alternativ mindre centrerad vattenstämpel */
body.with-watermark-small::before {
    content: "";
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 400px;
    height: 400px;
    background-image: url('LOGO_BASE64_PLACEHOLDER');
    background-repeat: no-repeat;
    background-position: center;
    background-size: contain;
    opacity: 0.05;  /* 5% synlighet */
    z-index: -1;
    pointer-events: none;
}

/* Säkerställ att vattenstämpel syns vid print */
@media print {
    body.with-watermark::before,
    body.with-watermark-diagonal::before {
        print-color-adjust: exact;
        -webkit-print-color-adjust: exact;
    }
}

/* === TABELLSTYLING (ENHETLIG) === */

/* Bas-tabell - Gemensam styling för alla tabeller */
.base-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: var(--spacing-m);
    font-size: var(--font-size-small);
    border: 1px solid var(--color-border);
}

.base-table th,
.base-table td {
    padding: var(--spacing-s);
    text-align: left;
    vertical-align: top;
    border-bottom: 1px solid var(--color-border);
}

.base-table thead th {
    background-color: var(--color-background-alt);
    color: var(--color-dark);
    font-weight: bold;
    border-bottom-width: 2px;
}

.base-table tbody tr:nth-child(even) {
    background-color: var(--color-background-alt);
}

/* Data-tabell - Ärver från bas-tabell med print-optimering */
.data-table thead {
    /* Repetera tabellhuvud på varje sida */
    display: table-header-group;
}

.data-table tbody tr {
    /* Förhindra att tabellrader bryts över sidor */
    page-break-inside: avoid;
}

/* TOC-tabell - Ärver från bas-tabell */
.toc-table {
    /* Ärver all bas-styling */
}

.toc-table tbody tr {
    /* Förhindra att TOC-rader bryts över sidor */
    page-break-inside: avoid;
}

/* Modifierare för TOC-tabellen */
.data-table--toc .col-article,
.toc-table .col-article {
    font-weight: bold;
    color: var(--color-primary);
    width: 50%;
}

.data-table--toc .col-pages,
.toc-table .col-pages {
    font-weight: bold;
}

/* === KOLUMNSPECIFIK STYLING (Optimerad för 8mm marginaler) === */
.col-level       { width: 6%; }
.col-article     { width: 25%; }
.col-description { width: 45%; }
.col-quantity    { width: 8%; text-align: right; font-weight: 500; }
.col-batch,
.col-charge      { width: 8%; font-family: var(--font-family-mono); }

/* För TOC-tabellen */
.col-pages       {
    width: 50%;
    text-align: right;
}
.col-page        { width: 8%; text-align: center; }

/* === STATISTIKBAR === */
.stats-bar {
    font-size: var(--font-size-small);
    color: var(--color-text-muted);
    text-align: center;
    margin-top: var(--spacing-s);
}

/* Container for layout */
.container {
    max-width: 100%;
    margin: 0 auto;
}
</style>
"""


def _get_logo_base64() -> Optional[str]:
    """
    Load FA-TEC logo as base64 from assets folder.

    Returns:
        Base64 string if found, None otherwise
    """
    try:
        logo_path = Path(__file__).parent / "assets" / "fatec_logo_base64.txt"
        if logo_path.exists():
            logo_base64 = logo_path.read_text().strip()
            logger.info("Loaded FA-TEC logo for watermark")
            return logo_base64
        else:
            logger.warning(f"FA-TEC logo file not found at: {logo_path}")
    except Exception as e:
        logger.warning(f"Could not read logo: {e}")
    return None


def get_report_css_with_watermark() -> Tuple[str, str]:
    """
    Get report CSS with watermark enabled.

    Returns:
        Tuple of (CSS string, body class name)
    """
    css_content = REPORT_CSS
    body_class = "report-page"

    # Try to load logo
    logo_base64 = _get_logo_base64()

    if logo_base64:
        # Inject logo into CSS
        css_content = css_content.replace('LOGO_BASE64_PLACEHOLDER', logo_base64)
        body_class = "report-page with-watermark"
        logger.info("Added FA-TEC watermark to CSS")
    else:
        logger.warning("Could not add watermark - logo not found")

    return css_content, body_class
