"""
Report Progress Dialog for Tobbes v2.

Shows progress during PDF report generation with option to open report when done.
"""

import logging
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QProgressBar
    )
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QDesktopServices
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QDialog = object

logger = logging.getLogger(__name__)


class ReportProgressDialog(QDialog):
    """
    Progress dialog for report generation.

    Shows progress bar and status messages during generation.
    When complete, shows "Öppna rapport" button to open PDF in system viewer.
    """

    def __init__(self, parent=None):
        """Initialize progress dialog."""
        super().__init__(parent)

        self.report_path = None
        self.is_complete = False

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("Genererar rapport...")
        self.setModal(True)
        self.setMinimumWidth(400)

        layout = QVBoxLayout()

        # Status label
        self.status_label = QLabel("Förbereder rapportgenerering...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        # Buttons (initially hidden)
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_open_report = QPushButton("Öppna rapport")
        self.btn_open_report.clicked.connect(self._open_report)
        self.btn_open_report.setVisible(False)
        button_layout.addWidget(self.btn_open_report)

        self.btn_close = QPushButton("Stäng")
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setVisible(False)
        button_layout.addWidget(self.btn_close)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_progress(self, value: int, status: str = None):
        """
        Update progress bar and optional status message.

        Args:
            value: Progress value (0-100)
            status: Optional status message
        """
        self.progress_bar.setValue(value)

        if status:
            self.status_label.setText(status)
            logger.debug(f"Progress: {value}% - {status}")

    def set_complete(self, report_path: Path):
        """
        Mark generation as complete and show action buttons.

        Args:
            report_path: Path to generated report
        """
        self.is_complete = True
        self.report_path = report_path

        # Update UI
        self.setWindowTitle("Rapport genererad")
        self.progress_bar.setValue(100)
        self.status_label.setText(
            f"Rapporten har genererats!\n\nFil: {report_path.name}"
        )

        # Show buttons
        self.btn_open_report.setVisible(True)
        self.btn_close.setVisible(True)

        logger.info(f"Report generation complete: {report_path}")

    def set_error(self, error_message: str):
        """
        Show error state.

        Args:
            error_message: Error message to display
        """
        self.setWindowTitle("Rapportgenerering misslyckades")
        self.status_label.setText(f"Ett fel uppstod:\n\n{error_message}")

        # Show only close button
        self.btn_close.setVisible(True)

        logger.error(f"Report generation error: {error_message}")

    def _open_report(self):
        """Open report in system PDF viewer."""
        if not self.report_path or not self.report_path.exists():
            logger.warning("Cannot open report - file not found")
            return

        # Open with system default PDF viewer
        url = QUrl.fromLocalFile(str(self.report_path))
        success = QDesktopServices.openUrl(url)

        if success:
            logger.info(f"Opened report in system viewer: {self.report_path}")
        else:
            logger.warning(f"Failed to open report: {self.report_path}")
