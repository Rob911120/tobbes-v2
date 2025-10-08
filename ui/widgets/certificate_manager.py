"""
Certificate Manager Widget for Tobbes v2.

Manages certificates for a single article with type dropdown and file selection.
Based on v1's CertificateManagerV5 implementation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
        QComboBox, QFrame, QFileDialog, QMessageBox, QDialog
    )
    from PySide6.QtCore import Signal, Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    QFrame = object
    Signal = None
    Qt = None

from services.certificate_service import create_certificate_service
from data.interface import DatabaseInterface
from ui.dialogs.add_certificate_dialog import AddCertificateDialog

logger = logging.getLogger(__name__)


class CertificateManager(QFrame):
    """
    Manages certificates for an article with dropdown and file selection.

    Features:
    - Dropdown for certificate type selection
    - "Välj intygsfiler..." button for multi-file selection
    - Display list of selected files with remove buttons
    - Status label showing count of selected files
    """

    certificate_added = Signal()  # Emitted when certificates are added

    def __init__(
        self,
        article_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        db: Optional[DatabaseInterface] = None,
        project_id: Optional[int] = None,
        parent=None
    ):
        """
        Initialize certificate manager.

        Args:
            article_data: Article data dict (certificates list will be read/written here)
            config: Config dict with certificate types
            db: Database interface (required for processing certificates)
            project_id: Project ID (required for processing certificates)
            parent: Parent widget
        """
        super().__init__(parent)

        self.article_data = article_data
        self.config = config or {}
        self.db = db
        self.project_id = project_id
        self.selected_files = []  # List of file info dicts

        # Create certificate service
        self.cert_service = create_certificate_service()

        self._setup_ui()
        self._load_existing_certificates()

    def _setup_ui(self):
        """Setup UI components."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            CertificateManager {
                background-color: #ffffff;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                margin: 4px;
                padding: 8px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)

        # Header with label and button
        header_layout = QHBoxLayout()

        self.header_label = QLabel("Intyg:")
        self.header_label.setStyleSheet("font-weight: bold; color: #495057;")
        header_layout.addWidget(self.header_label)

        # Add button
        self.add_button = QPushButton("Lägg till intyg")
        self.add_button.setMaximumWidth(150)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton:pressed {
                background-color: #004085;
            }
        """)
        self.add_button.clicked.connect(self._select_files)
        header_layout.addWidget(self.add_button)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Status label
        self.status_label = QLabel("Inga filer valda")
        self.status_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 4px;")
        layout.addWidget(self.status_label)

        # Container for file list
        self.files_container = QWidget()
        self.files_layout = QVBoxLayout(self.files_container)
        self.files_layout.setContentsMargins(0, 0, 0, 0)
        self.files_layout.setSpacing(2)
        layout.addWidget(self.files_container)

        self.setLayout(layout)

    def _load_existing_certificates(self):
        """Load and display existing certificates from article data."""
        article_number = self.article_data.get('article_number', 'UNKNOWN')
        existing_certificates = self.article_data.get('certificates', [])

        logger.info(f"🔍 CertificateManager._load_existing_certificates for {article_number}: {len(existing_certificates)} certificates")

        if existing_certificates:
            for idx, cert_data in enumerate(existing_certificates):
                logger.debug(f"  Certificate #{idx + 1}: {cert_data}")

                # Normalize database format to UI format
                # Database format: stored_path, certificate_type, stored_name, original_name
                # UI format needs: path, type, name

                normalized_cert = {}

                # Path normalization
                if 'stored_path' in cert_data:
                    normalized_cert['path'] = cert_data['stored_path']
                elif 'path' in cert_data:
                    normalized_cert['path'] = cert_data['path']
                else:
                    logger.warning(f"    ❌ Certificate #{idx + 1} missing path field!")
                    continue

                # Type normalization
                if 'certificate_type' in cert_data:
                    normalized_cert['type'] = cert_data['certificate_type']
                elif 'type' in cert_data:
                    normalized_cert['type'] = cert_data['type']
                else:
                    logger.warning(f"    ❌ Certificate #{idx + 1} missing type field!")
                    continue

                # Name normalization (prefer original_name, fallback to stored_name, fallback to filename)
                if 'original_name' in cert_data:
                    normalized_cert['name'] = cert_data['original_name']
                elif 'stored_name' in cert_data:
                    normalized_cert['name'] = cert_data['stored_name']
                elif 'name' in cert_data:
                    normalized_cert['name'] = cert_data['name']
                else:
                    # Extract from path
                    path = normalized_cert.get('path', '')
                    normalized_cert['name'] = Path(path).name if path else 'Okänd fil'

                # Copy over other fields (id, certificate_id, etc.)
                for key in ['id', 'certificate_id', 'page_count', 'created_at']:
                    if key in cert_data:
                        normalized_cert[key] = cert_data[key]

                logger.info(f"    ✅ Loaded: {normalized_cert['name']} ({normalized_cert['type']})")

                self.selected_files.append(normalized_cert)
                self._add_file_entry(normalized_cert)

            self._update_status()
            # Sync normalized certificates back to article_data (keeps data format consistent)
            self.article_data['certificates'] = self.selected_files

            logger.info(f"✅ CertificateManager loaded {len(self.selected_files)} certificates for {article_number}")
        else:
            logger.debug(f"  ⚠️ No certificates for {article_number}")

    def _select_files(self):
        """Open certificate dialog with auto-suggest and PROCESS certificates (copy, stamp, save)."""
        # Validate that we have database and project_id
        if not self.db or not self.project_id:
            QMessageBox.warning(
                self,
                "Konfigurationsfel",
                "Database eller projekt-ID saknas. Kan inte processa certifikat."
            )
            return

        # Get article number and charge number from article data
        article_number = self.article_data.get('article_number', 'UNKNOWN')
        charge_number = self.article_data.get('charge_number')  # May be None

        # Open new AddCertificateDialog with auto-suggest
        dialog = AddCertificateDialog(
            database=self.db,
            article_number=article_number,
            charge_number=charge_number,
            project_id=self.project_id,
            parent=self
        )

        if dialog.exec() == QDialog.Accepted:
            selected_file = dialog.get_selected_file()
            selected_cert_type = dialog.get_selected_type()

            if selected_file and selected_file.exists():
                try:
                    # Process certificate (V1-style: copy, stamp, save)
                    result = self.cert_service.process_certificate(
                        original_path=selected_file,
                        article_num=article_number,
                        cert_type=selected_cert_type,
                        project_id=self.project_id,
                        db=self.db
                    )

                    if result['success']:
                        logger.info(f"Certificate processed: {result['data']['certificate_id']}")

                        # Reload certificates from database to ensure UI is in sync
                        self._reload_certificates_from_db()

                        # Emit signal that certificates were added
                        self.certificate_added.emit()

                        QMessageBox.information(
                            self,
                            "Klart",
                            f"Certifikat tillagt: {selected_file.name}"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            "Fel",
                            f"Kunde inte processa {selected_file.name}:\n\n{result['message']}"
                        )

                except Exception as e:
                    logger.exception(f"Failed to process certificate: {e}")
                    QMessageBox.critical(
                        self,
                        "Oväntat fel",
                        f"Ett oväntat fel uppstod vid processning av certifikat:\n\n{str(e)}"
                    )

    def _add_file_entry(self, file_info: Dict[str, Any]):
        """Add a file entry to the list."""
        entry_widget = QFrame()
        entry_widget.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 2px;
                padding: 4px;
            }
        """)

        entry_layout = QHBoxLayout(entry_widget)
        entry_layout.setContentsMargins(8, 4, 8, 4)

        # Type label (handle both 'type' and 'certificate_type')
        cert_type = file_info.get('type') or file_info.get('certificate_type', 'Okänd typ')
        type_label = QLabel(f"{cert_type}:")  # Removed [OK] prefix
        type_label.setStyleSheet("color: #28a745; font-weight: bold;")
        entry_layout.addWidget(type_label)

        # Filename - show stored_name (ID-marked) if available, else name
        # Make clickable with custom ClickableLabel
        display_name = file_info.get('stored_name', file_info.get('name', 'Okänd fil'))
        name_label = QLabel(display_name)
        name_label.setStyleSheet("color: #495057;")

        # Enable mouse tracking for hover effects
        name_label.setCursor(Qt.CursorShape.PointingHandCursor)

        # Install event filter for double-click
        name_label.mouseDoubleClickEvent = lambda event: self._open_file(file_info)

        # Tooltip with original name + click instruction
        tooltip_text = "Dubbelklicka för att öppna"
        if 'original_name' in file_info:
            tooltip_text += f"\nUrsprungligt namn: {file_info['original_name']}"
        name_label.setToolTip(tooltip_text)

        entry_layout.addWidget(name_label)

        entry_layout.addStretch()

        # Remove button
        remove_btn = QPushButton("Ta bort")
        remove_btn.setMaximumWidth(80)
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 8px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        remove_btn.clicked.connect(lambda: self._remove_file(file_info, entry_widget))
        entry_layout.addWidget(remove_btn)

        self.files_layout.addWidget(entry_widget)

    def _remove_file(self, file_info: Dict[str, Any], widget: QWidget):
        """Remove file from list."""
        if file_info in self.selected_files:
            self.selected_files.remove(file_info)

        widget.deleteLater()
        self._update_status()

        # Update article_data
        self.article_data['certificates'] = self.selected_files

    def _open_file(self, file_info: Dict[str, Any]):
        """Open certificate file with system default application."""
        import subprocess
        import sys

        # Get file path (handle both 'path' and 'stored_path' keys)
        file_path = Path(file_info.get('path') or file_info.get('stored_path', ''))

        try:
            if not file_path or not file_path.exists():
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

            logger.info(f"Opened certificate file: {file_path}")

        except Exception as e:
            logger.exception(f"Failed to open certificate file: {file_path}")
            QMessageBox.warning(
                self,
                "Kunde inte öppna fil",
                f"Fel vid öppning av fil: {e}"
            )

    def _update_status(self):
        """Update status text."""
        count = len(self.selected_files)
        if count == 0:
            self.status_label.setText("Inga filer valda")
            self.status_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 4px;")
        else:
            self.status_label.setText(f"{count} fil{'er' if count > 1 else ''} vald{'a' if count > 1 else ''}")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; margin: 4px;")

    def _reload_certificates_from_db(self):
        """
        Reload certificates from database after upload.

        This ensures the UI displays the latest certificates from DB,
        including newly uploaded ones.
        """
        if not self.db or not self.project_id:
            logger.warning("Cannot reload certificates - db or project_id missing")
            return

        article_number = self.article_data.get('article_number')
        if not article_number:
            logger.warning("Cannot reload certificates - article_number missing")
            return

        # Fetch fresh certificates from database
        certificates = self.db.get_certificates_for_article(
            project_id=self.project_id,
            article_number=article_number
        )

        # Update internal state
        self.selected_files = certificates
        self.article_data['certificates'] = certificates

        # Clear current file list UI
        while self.files_layout.count() > 0:
            item = self.files_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Rebuild file list UI from fresh data
        for cert in certificates:
            self._add_file_entry(cert)

        # Update status
        self._update_status()

        logger.info(
            f"Reloaded {len(certificates)} certificates for {article_number} from DB"
        )
