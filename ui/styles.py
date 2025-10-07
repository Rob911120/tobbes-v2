"""
UI Styles for Tobbes v2.

Centralized Qt stylesheet definitions and CSS for HTML reports.
"""

from config.constants import (
    COLOR_GRAY,
    COLOR_GREEN,
    COLOR_YELLOW,
    WATERMARK_TEXT,
    WATERMARK_OPACITY,
    WATERMARK_ROTATION,
    WATERMARK_FONT_SIZE,
)


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
body {
    font-family: 'Segoe UI', Arial, sans-serif;
    margin: 20px;
    color: #333333;
}

h1 {
    color: #0078d4;
    border-bottom: 2px solid #0078d4;
    padding-bottom: 10px;
}

h2 {
    color: #106ebe;
    margin-top: 30px;
}

table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

th {
    background-color: #0078d4;
    color: white;
    padding: 12px;
    text-align: left;
    font-weight: bold;
}

td {
    padding: 10px;
    border-bottom: 1px solid #e0e0e0;
}

tr:hover {
    background-color: #f5f5f5;
}

.project-info {
    background-color: #f0f0f0;
    padding: 15px;
    border-radius: 6px;
    margin-bottom: 20px;
}

.article-row {
    page-break-inside: avoid;
}

.certificate-list {
    padding-left: 20px;
    color: #666666;
}

@media print {
    body {
        margin: 0;
    }

    .no-print {
        display: none;
    }
}
</style>
"""


def get_report_css_with_watermark() -> str:
    """
    Get report CSS with watermark enabled.

    Returns:
        Tuple of (CSS string, body class name)
    """
    watermark_css = f"""
body.watermarked::before {{
    content: "{WATERMARK_TEXT}";
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%) rotate({WATERMARK_ROTATION}deg);
    font-size: {WATERMARK_FONT_SIZE}px;
    color: rgba(0, 0, 0, {WATERMARK_OPACITY});
    z-index: -1;
    pointer-events: none;
}}
"""

    return REPORT_CSS + f"<style>{watermark_css}</style>"
