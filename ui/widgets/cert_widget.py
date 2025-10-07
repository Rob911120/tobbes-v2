"""
Certificate Widget.

Displays certificate information with actions (view, remove).
"""

import logging
from pathlib import Path
from typing import Optional, Callable

try:
    from PySide6.QtWidgets import (
        QWidget, QHBoxLayout, QVBoxLayout, QLabel,
        QPushButton, QMessageBox
    )
    from PySide6.QtCore import Signal, Qt
    from PySide6.QtGui import QIcon
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    Signal = None

logger = logging.getLogger(__name__)


class CertWidget(QWidget):
    """
    Widget for displaying a single certificate.

    Features:
    - Certificate type and filename
    - File size and page count
    - View and remove actions

    Signals:
        view_clicked: Emitted when view button clicked
        remove_clicked: Emitted when remove button clicked
    """

    # Signals
    view_clicked = Signal()
    remove_clicked = Signal()

    def __init__(
        self,
        cert_data: dict,
        on_view: Optional[Callable] = None,
        on_remove: Optional[Callable] = None,
        parent=None
    ):
        """
        Initialize certificate widget.

        Args:
            cert_data: Certificate data dict with keys:
                - certificate_type: str
                - original_filename: str
                - file_path: str or Path
                - page_count: int (optional)
                - file_size: int (optional, bytes)
            on_view: Optional callback when view clicked
            on_remove: Optional callback when remove clicked
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.cert_data = cert_data
        self.on_view_callback = on_view
        self.on_remove_callback = on_remove

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Left side - Info
        info_layout = QVBoxLayout()

        # Certificate type
        type_label = QLabel(f"<b>{self.cert_data.get('certificate_type', 'Okänd typ')}</b>")
        info_layout.addWidget(type_label)

        # Filename
        filename = self.cert_data.get('original_filename', 'Okänt filnamn')
        filename_label = QLabel(filename)
        filename_label.setStyleSheet("color: #666;")
        info_layout.addWidget(filename_label)

        # Metadata (page count, file size)
        metadata_parts = []

        page_count = self.cert_data.get('page_count')
        if page_count:
            metadata_parts.append(f"{page_count} sidor")

        file_size = self.cert_data.get('file_size')
        if file_size:
            size_mb = file_size / (1024 * 1024)
            metadata_parts.append(f"{size_mb:.1f} MB")

        if metadata_parts:
            metadata_label = QLabel(" · ".join(metadata_parts))
            metadata_label.setStyleSheet("color: #999; font-size: 11px;")
            info_layout.addWidget(metadata_label)

        layout.addLayout(info_layout, stretch=1)

        # Right side - Actions
        actions_layout = QHBoxLayout()

        # View button
        self.btn_view = QPushButton("Visa")
        self.btn_view.setMaximumWidth(80)
        self.btn_view.clicked.connect(self._on_view_clicked)
        actions_layout.addWidget(self.btn_view)

        # Remove button
        self.btn_remove = QPushButton("Ta bort")
        self.btn_remove.setMaximumWidth(80)
        self.btn_remove.setStyleSheet("color: #f44336;")
        self.btn_remove.clicked.connect(self._on_remove_clicked)
        actions_layout.addWidget(self.btn_remove)

        layout.addLayout(actions_layout)

        self.setLayout(layout)

        # Styling
        self.setProperty("class", "cert-widget")
        self.setStyleSheet("""
            QWidget[class="cert-widget"] {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 5px;
            }
            QWidget[class="cert-widget"]:hover {
                background-color: #eeeeee;
            }
        """)

    def _on_view_clicked(self):
        """Handle view button click."""
        self.view_clicked.emit()

        if self.on_view_callback:
            self.on_view_callback()

        # Try to open file with system default application
        file_path = self.cert_data.get('file_path')
        if file_path:
            self._open_file(Path(file_path))

    def _on_remove_clicked(self):
        """Handle remove button click."""
        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Bekräfta borttagning",
            f"Vill du ta bort certifikatet '{self.cert_data.get('original_filename', 'detta certifikat')}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.remove_clicked.emit()

            if self.on_remove_callback:
                self.on_remove_callback()

    def _open_file(self, file_path: Path):
        """Open file with system default application."""
        import subprocess
        import sys

        try:
            if not file_path.exists():
                QMessageBox.warning(
                    self,
                    "Fil saknas",
                    f"Filen kunde inte hittas: {file_path}"
                )
                return

            # Open with system default application
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(file_path)])
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", str(file_path)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(file_path)])

            logger.info(f"Opened file: {file_path}")

        except Exception as e:
            logger.exception(f"Failed to open file: {file_path}")
            QMessageBox.warning(
                self,
                "Kunde inte öppna fil",
                f"Fel vid öppning av fil: {e}"
            )

    def get_certificate_type(self) -> str:
        """Get certificate type."""
        return self.cert_data.get('certificate_type', '')

    def get_file_path(self) -> Optional[Path]:
        """Get file path."""
        file_path = self.cert_data.get('file_path')
        return Path(file_path) if file_path else None

    def update_certificate_data(self, cert_data: dict):
        """
        Update certificate data and refresh UI.

        Args:
            cert_data: New certificate data
        """
        self.cert_data = cert_data
        # Recreate UI with new data
        # Clear existing layout
        while self.layout().count():
            child = self.layout().takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Setup UI again
        self._setup_ui()
