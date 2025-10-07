"""
Certificate Upload Dialog for Tobbes v2.

Upload and manage certificates for articles.
"""

import logging
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QPushButton, QLineEdit, QComboBox,
        QFileDialog, QMessageBox, QDialogButtonBox
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QDialog = object

from operations import guess_certificate_type, validate_certificate_file
from services import FileService
from domain.exceptions import ValidationError, DatabaseError
from config.constants import ALLOWED_CERTIFICATE_EXTENSIONS, DEFAULT_CERTIFICATE_TYPES

logger = logging.getLogger(__name__)


class CertificateUploadDialog(QDialog):
    """
    Dialog for uploading certificates.

    Features:
    - File selection
    - Auto-detect certificate type from filename
    - Manual certificate type selection
    - Copy file to project directory
    - Save reference to database
    """

    def __init__(
        self,
        article_number: str,
        article_description: str,
        project_id: int,
        database,
        file_service: FileService,
        parent=None
    ):
        """
        Initialize certificate upload dialog.

        Args:
            article_number: Article number
            article_description: Article description (for display)
            project_id: Project ID
            database: DatabaseInterface instance
            file_service: FileService instance
            parent: Parent widget
        """
        super().__init__(parent)

        self.article_number = article_number
        self.article_description = article_description
        self.project_id = project_id
        self.database = database
        self.file_service = file_service

        self.selected_file = None
        self.certificate_type = None

        self._setup_ui()
        self._load_certificate_types()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle(f"Ladda upp Certifikat - {self.article_number}")
        self.setModal(True)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Article info
        info_label = QLabel(
            f"<b>Artikel:</b> {self.article_number}<br>"
            f"<b>Benämning:</b> {self.article_description}"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Form
        form_layout = QFormLayout()

        # File selection
        file_row = QHBoxLayout()
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        self.file_edit.setPlaceholderText("Ingen fil vald...")
        file_row.addWidget(self.file_edit)

        self.btn_browse = QPushButton("Bläddra...")
        self.btn_browse.clicked.connect(self._browse_file)
        file_row.addWidget(self.btn_browse)

        form_layout.addRow("Fil*:", file_row)

        # Certificate type
        self.type_combo = QComboBox()
        form_layout.addRow("Certifikattyp*:", self.type_combo)

        layout.addLayout(form_layout)

        # Hint
        hint_label = QLabel(
            "💡 Certifikattypen detekteras automatiskt från filnamnet.\n"
            "Du kan ändra den manuellt om det behövs."
        )
        hint_label.setStyleSheet("color: #666666; font-size: 9pt;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _load_certificate_types(self):
        """Load available certificate types."""
        try:
            # Get certificate types from database
            types = self.database.get_certificate_types(project_id=self.project_id)

            # If no types in database, use defaults
            if not types:
                types = DEFAULT_CERTIFICATE_TYPES

            for cert_type in types:
                self.type_combo.addItem(cert_type)

        except Exception as e:
            logger.exception("Failed to load certificate types")
            # Fallback to defaults
            for cert_type in DEFAULT_CERTIFICATE_TYPES:
                self.type_combo.addItem(cert_type)

    def _browse_file(self):
        """Browse for certificate file."""
        ext_filter = " ".join([f"*{ext}" for ext in ALLOWED_CERTIFICATE_EXTENSIONS])

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj Certifikat",
            "",
            f"Certifikat ({ext_filter})"
        )

        if file_path:
            self.selected_file = Path(file_path)
            self.file_edit.setText(str(self.selected_file))

            # Auto-detect certificate type
            detected_type = guess_certificate_type(self.selected_file.name)

            # Set in combo if exists
            index = self.type_combo.findText(detected_type)
            if index >= 0:
                self.type_combo.setCurrentIndex(index)
            else:
                # Add as new type if not exists
                self.type_combo.addItem(detected_type)
                self.type_combo.setCurrentText(detected_type)

            logger.info(
                f"Selected file: {self.selected_file}, "
                f"detected type: {detected_type}"
            )

    def _accept(self):
        """Validate and accept."""
        try:
            # Validate file selected
            if not self.selected_file:
                raise ValidationError("Ingen fil vald")

            # Validate certificate type
            cert_type = self.type_combo.currentText().strip()
            if not cert_type:
                raise ValidationError("Certifikattyp krävs")

            # Validate file
            validate_certificate_file(self.selected_file)

            # Copy file to project directory
            logger.info(f"Copying certificate file: {self.selected_file}")
            dest_path = self.file_service.copy_certificate(
                source_path=self.selected_file,
                project_id=self.project_id,
                article_number=self.article_number,
                preserve_name=True,
            )

            # Save to database
            logger.info(f"Saving certificate to database: {dest_path}")
            cert_id = self.database.save_certificate(
                project_id=self.project_id,
                article_number=self.article_number,
                certificate_type=cert_type,
                file_path=str(dest_path),
                original_filename=self.selected_file.name,
                page_count=1,  # TODO: Get actual page count from PDF
            )

            logger.info(f"Certificate saved: id={cert_id}, type={cert_type}")

            self.certificate_type = cert_type
            self.accept()

        except ValidationError as e:
            QMessageBox.warning(self, "Valideringsfel", str(e))

        except DatabaseError as e:
            logger.error(f"Database error: {e}")
            QMessageBox.critical(
                self,
                "Databasfel",
                f"Kunde inte spara certifikat:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error uploading certificate")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )
