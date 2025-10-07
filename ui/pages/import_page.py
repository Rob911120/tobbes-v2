"""
Import Page for Tobbes v2 Wizard.

File import for nivålista (BOM) and lagerlogg (inventory).
"""

import logging
from pathlib import Path

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QGroupBox, QLineEdit, QFileDialog, QTextEdit,
        QMessageBox
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from operations import import_nivalista, import_lagerlogg, get_import_summary
from domain.exceptions import ImportValidationError, DatabaseError
from config.constants import EXCEL_EXTENSIONS

logger = logging.getLogger(__name__)


class ImportPage(QWizardPage):
    """
    Import page - Import nivålista and lagerlogg files.

    Features:
    - File selection for nivålista (required)
    - File selection for lagerlogg (optional)
    - Import and save to database
    - Display import summary
    """

    def __init__(self, wizard):
        """Initialize import page."""
        super().__init__()

        self.wizard_ref = wizard
        self.nivalista_path = None
        self.lagerlogg_path = None
        self.imported_articles = []
        self.imported_inventory = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Importera Filer")
        self.setSubTitle("Välj nivålista (obligatorisk) och lagerlogg (valfri).")

        layout = QVBoxLayout()

        # Nivålista section
        nivalista_group = QGroupBox("Nivålista (BOM) - Obligatorisk")
        nivalista_layout = QVBoxLayout()

        nivalista_row = QHBoxLayout()
        self.nivalista_edit = QLineEdit()
        self.nivalista_edit.setReadOnly(True)
        self.nivalista_edit.setPlaceholderText("Ingen fil vald...")
        nivalista_row.addWidget(self.nivalista_edit)

        self.btn_browse_nivalista = QPushButton("Bläddra...")
        self.btn_browse_nivalista.clicked.connect(self._browse_nivalista)
        nivalista_row.addWidget(self.btn_browse_nivalista)

        self.btn_import_nivalista = QPushButton("Importera")
        self.btn_import_nivalista.clicked.connect(self._import_nivalista)
        self.btn_import_nivalista.setEnabled(False)
        nivalista_row.addWidget(self.btn_import_nivalista)

        nivalista_layout.addLayout(nivalista_row)
        nivalista_group.setLayout(nivalista_layout)
        layout.addWidget(nivalista_group)

        # Lagerlogg section
        lagerlogg_group = QGroupBox("Lagerlogg (Inventory) - Valfri")
        lagerlogg_layout = QVBoxLayout()

        lagerlogg_row = QHBoxLayout()
        self.lagerlogg_edit = QLineEdit()
        self.lagerlogg_edit.setReadOnly(True)
        self.lagerlogg_edit.setPlaceholderText("Ingen fil vald...")
        lagerlogg_row.addWidget(self.lagerlogg_edit)

        self.btn_browse_lagerlogg = QPushButton("Bläddra...")
        self.btn_browse_lagerlogg.clicked.connect(self._browse_lagerlogg)
        lagerlogg_row.addWidget(self.btn_browse_lagerlogg)

        self.btn_import_lagerlogg = QPushButton("Importera")
        self.btn_import_lagerlogg.clicked.connect(self._import_lagerlogg)
        self.btn_import_lagerlogg.setEnabled(False)
        lagerlogg_row.addWidget(self.btn_import_lagerlogg)

        lagerlogg_layout.addLayout(lagerlogg_row)
        lagerlogg_group.setLayout(lagerlogg_layout)
        layout.addWidget(lagerlogg_group)

        # Summary section
        summary_group = QGroupBox("Sammanfattning")
        summary_layout = QVBoxLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlaceholderText("Importera filer för att se sammanfattning...")
        self.summary_text.setMaximumHeight(150)
        summary_layout.addWidget(self.summary_text)

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

        layout.addStretch()
        self.setLayout(layout)

    def _browse_nivalista(self):
        """Browse for nivålista file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj Nivålista",
            "",
            f"Excel-filer ({' '.join(['*' + ext for ext in EXCEL_EXTENSIONS])})"
        )

        if file_path:
            self.nivalista_path = Path(file_path)
            self.nivalista_edit.setText(str(self.nivalista_path))
            self.btn_import_nivalista.setEnabled(True)
            logger.info(f"Selected nivålista: {self.nivalista_path}")

    def _browse_lagerlogg(self):
        """Browse for lagerlogg file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Välj Lagerlogg",
            "",
            f"Excel-filer ({' '.join(['*' + ext for ext in EXCEL_EXTENSIONS])})"
        )

        if file_path:
            self.lagerlogg_path = Path(file_path)
            self.lagerlogg_edit.setText(str(self.lagerlogg_path))
            self.btn_import_lagerlogg.setEnabled(True)
            logger.info(f"Selected lagerlogg: {self.lagerlogg_path}")

    def _import_nivalista(self):
        """Import nivålista file."""
        if not self.nivalista_path:
            return

        try:
            # Import articles using operation
            logger.info(f"Importing nivålista: {self.nivalista_path}")
            articles = import_nivalista(self.nivalista_path)

            # Save to database
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()

            db = ctx.database
            db.save_project_articles(project_id, articles)

            self.imported_articles = articles

            # Update summary
            self._update_summary()

            # Enable next button
            self.completeChanged.emit()

            logger.info(f"Imported {len(articles)} articles from nivålista")

            QMessageBox.information(
                self,
                "Import Lyckades",
                f"Importerade {len(articles)} artiklar från nivålista."
            )

        except ImportValidationError as e:
            logger.error(f"Import validation error: {e}")
            QMessageBox.warning(
                self,
                "Valideringsfel",
                f"Import misslyckades:\n\n{e.message}\n\nDetaljer: {e.details}"
            )

        except DatabaseError as e:
            logger.error(f"Database error during import: {e}")
            QMessageBox.critical(
                self,
                "Databasfel",
                f"Kunde inte spara till databas:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error during import")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

    def _import_lagerlogg(self):
        """Import lagerlogg file."""
        if not self.lagerlogg_path:
            return

        try:
            # Import inventory using operation
            logger.info(f"Importing lagerlogg: {self.lagerlogg_path}")
            inventory = import_lagerlogg(self.lagerlogg_path)

            # Save to database
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()

            db = ctx.database
            db.save_inventory_items(project_id, inventory)

            self.imported_inventory = inventory

            # Update summary
            self._update_summary()

            logger.info(f"Imported {len(inventory)} inventory items from lagerlogg")

            QMessageBox.information(
                self,
                "Import Lyckades",
                f"Importerade {len(inventory)} lagerrader från lagerlogg."
            )

        except ImportValidationError as e:
            logger.error(f"Import validation error: {e}")
            QMessageBox.warning(
                self,
                "Valideringsfel",
                f"Import misslyckades:\n\n{e.message}\n\nDetaljer: {e.details}"
            )

        except DatabaseError as e:
            logger.error(f"Database error during import: {e}")
            QMessageBox.critical(
                self,
                "Databasfel",
                f"Kunde inte spara till databas:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error during import")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

    def _update_summary(self):
        """Update import summary display."""
        summary_lines = []

        if self.imported_articles:
            summary = get_import_summary(self.imported_articles)
            summary_lines.append("=== NIVÅLISTA ===")
            summary_lines.append(f"Totalt artiklar: {summary['total_count']}")
            summary_lines.append(f"Unika artiklar: {summary['unique_articles']}")
            summary_lines.append(f"Artiklar med nivå: {summary['articles_with_level']}")
            summary_lines.append("")

        if self.imported_inventory:
            summary_lines.append("=== LAGERLOGG ===")
            summary_lines.append(f"Totalt lagerrader: {len(self.imported_inventory)}")

            unique_articles = len(set(item["article_number"] for item in self.imported_inventory))
            summary_lines.append(f"Unika artiklar: {unique_articles}")

            unique_charges = len(set(item["charge_number"] for item in self.imported_inventory if item.get("charge_number")))
            summary_lines.append(f"Unika charger: {unique_charges}")

        if summary_lines:
            self.summary_text.setText("\n".join(summary_lines))

    def isComplete(self):
        """Page is complete when nivålista is imported."""
        return len(self.imported_articles) > 0

    def initializePage(self):
        """Initialize page when entering."""
        # Clear previous imports if user goes back
        self.imported_articles = []
        self.imported_inventory = []
        self.summary_text.clear()

        # Verify project is selected
        try:
            project_id = self.wizard_ref.context.require_project()
            logger.info(f"Import page initialized for project: {project_id}")
        except ValueError as e:
            QMessageBox.critical(
                self,
                "Fel",
                "Inget projekt valt. Gå tillbaka och välj ett projekt."
            )
