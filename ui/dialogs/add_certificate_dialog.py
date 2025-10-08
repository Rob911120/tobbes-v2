"""
Add Certificate Dialog with Auto-Suggest.

Allows users to add certificates to articles with automatic file suggestions
based on fuzzy matching.
"""

import logging
from pathlib import Path
from typing import Optional, List, Tuple

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QComboBox, QMessageBox,
        QDialogButtonBox, QGroupBox, QRadioButton,
        QButtonGroup, QFileDialog, QScrollArea, QWidget
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QDialog = object

from services import certificate_scanner

logger = logging.getLogger(__name__)


class AddCertificateDialog(QDialog):
    """
    Dialog for adding certificates with auto-suggestion.

    Workflow:
    1. User selects certificate type
    2. If type has search_path configured: Auto-scan and suggest files
    3. Display suggestions sorted by match score
    4. User can accept suggestion or browse manually
    """

    def __init__(
        self,
        database,
        article_number: str,
        charge_number: Optional[str] = None,
        project_id: Optional[int] = None,
        parent=None
    ):
        """
        Initialize dialog.

        Args:
            database: Database instance
            article_number: Article number
            charge_number: Optional charge number
            project_id: Optional project ID for project-specific types
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.database = database
        self.article_number = article_number
        self.charge_number = charge_number
        self.project_id = project_id

        self.suggestions: List[Tuple[Path, float]] = []
        self.selected_file: Optional[Path] = None

        self._setup_ui()
        self._load_certificate_types()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("Lägg till certifikat")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Article info
        info_group = QGroupBox("Artikel")
        info_layout = QVBoxLayout()

        article_label = QLabel(f"<b>Artikelnummer:</b> {self.article_number}")
        info_layout.addWidget(article_label)

        if self.charge_number:
            charge_label = QLabel(f"<b>Chargenummer:</b> {self.charge_number}")
            info_layout.addWidget(charge_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Certificate type selection
        type_group = QGroupBox("Certifikattyp")
        type_layout = QVBoxLayout()

        self.cert_type_combo = QComboBox()
        self.cert_type_combo.currentTextChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.cert_type_combo)

        type_group.setLayout(type_layout)
        layout.addWidget(type_group)

        # Suggestions section (initially hidden)
        self.suggestions_group = QGroupBox("Förslag")
        self.suggestions_layout = QVBoxLayout()

        # Scroll area for suggestions
        self.suggestions_scroll = QScrollArea()
        self.suggestions_scroll.setWidgetResizable(True)
        self.suggestions_scroll.setMinimumHeight(200)

        self.suggestions_widget = QWidget()
        self.suggestions_widget_layout = QVBoxLayout()
        self.suggestions_widget.setLayout(self.suggestions_widget_layout)
        self.suggestions_scroll.setWidget(self.suggestions_widget)

        self.suggestions_layout.addWidget(self.suggestions_scroll)

        # Manual file selection button
        manual_button_layout = QHBoxLayout()
        self.btn_browse = QPushButton("Byt fil...")
        self.btn_browse.clicked.connect(self._browse_file)
        manual_button_layout.addWidget(self.btn_browse)
        manual_button_layout.addStretch()
        self.suggestions_layout.addLayout(manual_button_layout)

        self.suggestions_group.setLayout(self.suggestions_layout)
        self.suggestions_group.setVisible(False)
        layout.addWidget(self.suggestions_group)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _load_certificate_types(self):
        """Load certificate types into combo box."""
        try:
            # Get certificate types (global + project-specific)
            types = self.database.get_certificate_types(self.project_id)

            self.cert_type_combo.clear()
            self.cert_type_combo.addItems(types)

            logger.info(f"Loaded {len(types)} certificate types")

        except Exception as e:
            logger.exception("Failed to load certificate types")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte ladda certifikattyper: {e}"
            )

    def _on_type_changed(self, cert_type: str):
        """Handle certificate type selection change."""
        if not cert_type:
            return

        logger.info(f"Certificate type changed to: {cert_type}")

        # Get search path for this type (if configured)
        search_path = self._get_search_path(cert_type)

        if search_path:
            logger.info(f"Search path configured: {search_path}")
            self._scan_for_suggestions(search_path)
        else:
            logger.info("No search path configured - showing manual browse only")
            self.suggestions_group.setVisible(False)
            self.selected_file = None

    def _get_search_path(self, cert_type: str) -> Optional[Path]:
        """
        Get search path for certificate type.

        Args:
            cert_type: Certificate type name

        Returns:
            Path object if search_path is configured, otherwise None
        """
        try:
            types_with_paths = self.database.get_certificate_types_with_paths(
                self.project_id
            )

            for type_info in types_with_paths:
                if type_info['type_name'] == cert_type:
                    search_path_str = type_info.get('search_path')
                    if search_path_str:
                        return Path(search_path_str)
                    break

            return None

        except Exception as e:
            logger.exception(f"Error getting search path: {e}")
            return None

    def _scan_for_suggestions(self, search_path: Path):
        """
        Scan directory for certificate suggestions.

        Args:
            search_path: Directory to scan
        """
        logger.info(
            f"Scanning for suggestions: article={self.article_number}, "
            f"charge={self.charge_number}, path={search_path}"
        )

        try:
            # Use certificate_scanner service
            self.suggestions = certificate_scanner.suggest_certificates(
                search_path=search_path,
                article_number=self.article_number,
                charge_number=self.charge_number,
                min_score=70.0,  # Show all matches above 70%
            )

            logger.info(f"Found {len(self.suggestions)} suggestions")

            if self.suggestions:
                self._display_suggestions()
            else:
                self._show_no_suggestions()

        except Exception as e:
            logger.exception("Error scanning for suggestions")
            QMessageBox.warning(
                self,
                "Varning",
                f"Kunde inte scanna efter förslag: {e}\n\n"
                f"Du kan välja fil manuellt genom att klicka på 'Byt fil'."
            )
            self.suggestions_group.setVisible(False)

    def _display_suggestions(self):
        """Display file suggestions to user."""
        # Clear previous suggestions
        while self.suggestions_widget_layout.count():
            child = self.suggestions_widget_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Create radio button group
        self.suggestion_button_group = QButtonGroup(self)

        # Add radio button for each suggestion
        for i, (file_path, score) in enumerate(self.suggestions):
            radio = QRadioButton(f"{file_path.name} ({score:.0f}%)")
            radio.setToolTip(str(file_path))  # Show full path on hover

            # Store file path in radio button
            radio.setProperty("file_path", str(file_path))

            self.suggestion_button_group.addButton(radio, i)
            self.suggestions_widget_layout.addWidget(radio)

            # Auto-select first suggestion if score >= 85
            if i == 0 and score >= 85:
                radio.setChecked(True)
                self.selected_file = file_path
                logger.info(f"Auto-selected: {file_path.name} (score: {score}%)")

        # Connect selection change
        self.suggestion_button_group.buttonClicked.connect(self._on_suggestion_selected)

        # Show suggestions group
        self.suggestions_group.setVisible(True)
        self.suggestions_group.setTitle(f"✅ Hittade {len(self.suggestions)} förslag")

    def _show_no_suggestions(self):
        """Show message when no suggestions found."""
        self.suggestions_group.setVisible(True)
        self.suggestions_group.setTitle("❌ Inga förslag hittades")

        # Clear previous widgets
        while self.suggestions_widget_layout.count():
            child = self.suggestions_widget_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        no_match_label = QLabel(
            "Inga matchande filer hittades.\n\n"
            "Klicka på 'Byt fil...' för att välja fil manuellt."
        )
        no_match_label.setWordWrap(True)
        self.suggestions_widget_layout.addWidget(no_match_label)

    def _on_suggestion_selected(self, button):
        """Handle suggestion selection."""
        file_path_str = button.property("file_path")
        self.selected_file = Path(file_path_str)
        logger.info(f"User selected suggestion: {self.selected_file.name}")

    def _browse_file(self):
        """Open file browser for manual file selection."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj certifikatfil",
            "",
            "PDF-filer (*.pdf);;Alla filer (*)"
        )

        if file_path:
            self.selected_file = Path(file_path)
            logger.info(f"User manually selected: {self.selected_file.name}")

            # Update UI to show manual selection
            QMessageBox.information(
                self,
                "Fil vald",
                f"Vald fil: {self.selected_file.name}"
            )

    def _on_accept(self):
        """Handle OK button click."""
        if not self.selected_file:
            QMessageBox.warning(
                self,
                "Ingen fil vald",
                "Välj en fil från förslagen eller klicka på 'Byt fil...' "
                "för att välja fil manuellt."
            )
            return

        if not self.selected_file.exists():
            QMessageBox.critical(
                self,
                "Fel",
                f"Filen finns inte: {self.selected_file}"
            )
            return

        # Accept dialog
        self.accept()

    def get_selected_file(self) -> Optional[Path]:
        """
        Get selected certificate file.

        Returns:
            Path to selected file, or None if dialog was cancelled
        """
        return self.selected_file

    def get_selected_type(self) -> str:
        """
        Get selected certificate type.

        Returns:
            Certificate type name
        """
        return self.cert_type_combo.currentText()
