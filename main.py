#!/usr/bin/env python3
"""
Tobbes v2 - Spårbarhetsguiden
Main entry point for the application
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def setup_logging():
    """
    Configure logging for the application.

    Sets up console output with DEBUG level and pretty formatting.
    Suppresses noisy third-party loggers.
    """
    # Create formatter with timestamp, level, module name
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)

    # Suppress noisy third-party loggers
    logging.getLogger('PySide6').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    logging.getLogger('PIL').setLevel(logging.WARNING)

    logging.info("=" * 60)
    logging.info("Tobbes v2 - Spårbarhetsguiden")
    logging.info("Logging initialized - Level: DEBUG")
    logging.info("=" * 60)


def main():
    """Main application entry point."""
    # Setup logging FIRST
    setup_logging()

    # Launch GUI wizard
    try:
        from PySide6.QtWidgets import QApplication, QStyleFactory
        from PySide6.QtGui import QPalette
        from PySide6.QtCore import Qt
        from ui.wizard import TobbesWizard

        app = QApplication(sys.argv)

        # Force Windows native light theme (not dark mode)
        app.setStyle(QStyleFactory.create("Fusion"))  # Cross-platform consistent style

        # Set light palette explicitly
        palette = QPalette()
        palette.setColor(QPalette.Window, Qt.white)
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.Base, Qt.white)
        palette.setColor(QPalette.AlternateBase, Qt.lightGray)
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.black)
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.Button, Qt.white)
        palette.setColor(QPalette.ButtonText, Qt.black)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, Qt.blue)
        palette.setColor(QPalette.Highlight, Qt.blue)
        palette.setColor(QPalette.HighlightedText, Qt.white)
        app.setPalette(palette)

        wizard = TobbesWizard()
        wizard.show()
        sys.exit(app.exec())
    except Exception as e:
        print(f"\n❌ Failed to launch GUI: {e}")
        print("Run in development mode: python -m pytest tests/")
        sys.exit(1)


if __name__ == "__main__":
    main()
