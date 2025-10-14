"""
Update Page for Tobbes v2 Wizard.

Import and apply updates from new nivålista/lagerlogg.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
        QFileDialog, QCheckBox, QGroupBox, QHeaderView
    )
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from operations import update_ops, import_ops
from domain.exceptions import ImportValidationError, DatabaseError

logger = logging.getLogger(__name__)


class UpdatePage(QWizardPage):
    """
    Update page - Import and apply updates.

    Features:
    - Import new nivålista or lagerlogg
    - Compare with existing data
    - Show detected changes
    - Select which updates to apply
    - Apply selected updates
    """

    def __init__(self, wizard):
        """Initialize update page."""
        super().__init__()

        self.wizard_ref = wizard
        self.selected_file = None
        self.update_type = None  # 'nivalista' or 'lagerlogg'
        self.detected_updates = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Uppdatera projekt")
        self.setSubTitle("Importera ny nivålista eller lagerlogg och välj vilka uppdateringar som ska tillämpas.")

        layout = QVBoxLayout()

        # File selection section
        file_group = QGroupBox("Välj fil att importera")
        file_layout = QHBoxLayout()

        self.file_label = QLabel("Ingen fil vald")
        file_layout.addWidget(self.file_label)

        self.btn_select_nivalista = QPushButton("Välj nivålista")
        self.btn_select_nivalista.clicked.connect(lambda: self._select_file('nivalista'))
        file_layout.addWidget(self.btn_select_nivalista)

        self.btn_select_lagerlogg = QPushButton("Välj lagerlogg")
        self.btn_select_lagerlogg.clicked.connect(lambda: self._select_file('lagerlogg'))
        file_layout.addWidget(self.btn_select_lagerlogg)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Updates table section
        updates_label = QLabel("Upptäckta uppdateringar:")
        layout.addWidget(updates_label)

        self.updates_table = QTableWidget()
        self.updates_table.setColumnCount(5)
        self.updates_table.setHorizontalHeaderLabels([
            "Tillämpa", "Artikelnummer", "Fält", "Gammalt värde", "Nytt värde"
        ])
        self.updates_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.updates_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.updates_table)

        # Action buttons
        button_layout = QHBoxLayout()

        self.btn_select_all = QPushButton("Välj alla")
        self.btn_select_all.clicked.connect(self._select_all_updates)
        self.btn_select_all.setEnabled(False)
        button_layout.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Avmarkera alla")
        self.btn_deselect_all.clicked.connect(self._deselect_all_updates)
        self.btn_deselect_all.setEnabled(False)
        button_layout.addWidget(self.btn_deselect_all)

        button_layout.addStretch()

        self.btn_apply = QPushButton("Tillämpa valda uppdateringar")
        self.btn_apply.clicked.connect(self._apply_updates)
        self.btn_apply.setEnabled(False)
        button_layout.addWidget(self.btn_apply)

        layout.addLayout(button_layout)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(self.info_label)

        layout.addStretch()

        self.setLayout(layout)

    def _select_file(self, update_type: str):
        """
        Select file for import.

        Args:
            update_type: 'nivalista' or 'lagerlogg'
        """
        file_filter = "Excel-filer (*.xlsx *.xls)" if update_type == 'nivalista' else "Excel-filer (*.xlsx *.xls)"

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Välj {update_type}",
            str(Path.home()),
            file_filter
        )

        if file_path:
            self.selected_file = Path(file_path)
            self.update_type = update_type
            self.file_label.setText(f"{self.selected_file.name} ({update_type})")

            # Analyze updates
            self._analyze_updates()

    def _analyze_updates(self):
        """Analyze file and detect updates."""
        try:
            ctx = self.wizard_ref.context

            # Import new data
            if self.update_type == 'nivalista':
                new_data = import_ops.import_nivalista(self.selected_file)
            else:
                new_data = import_ops.import_lagerlogg(self.selected_file)

            # Get current articles
            current_articles = ctx.database.get_project_articles(ctx.current_project_id)

            # Compare and detect updates
            self.detected_updates = update_ops.compare_articles_for_update(
                current_articles=current_articles,
                new_data=new_data,
                update_type=self.update_type
            )

            # Display updates in table
            self._populate_updates_table()

            logger.info(f"Detected {len(self.detected_updates)} updates from {self.update_type}")

        except ImportValidationError as e:
            logger.error(f"Import validation error: {e}")
            QMessageBox.warning(
                self,
                "Importfel",
                f"Kunde inte importera fil:\n\n{e}"
            )

        except Exception as e:
            logger.exception("Failed to analyze updates")
            QMessageBox.critical(
                self,
                "Fel",
                f"Oväntat fel vid analys: {e}"
            )

    def _populate_updates_table(self):
        """Populate updates table with detected updates."""
        self.updates_table.setRowCount(len(self.detected_updates))

        for row, update in enumerate(self.detected_updates):
            # Checkbox for "Tillämpa"
            checkbox = QCheckBox()
            checkbox.setChecked(True)
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.updates_table.setCellWidget(row, 0, checkbox_widget)

            # Article number
            self.updates_table.setItem(row, 1, QTableWidgetItem(update.article_number))

            # Field name
            field_display = self._get_field_display_name(update.field_name)
            self.updates_table.setItem(row, 2, QTableWidgetItem(field_display))

            # Old value
            old_value_item = QTableWidgetItem(str(update.old_value) if update.old_value else "-")
            self.updates_table.setItem(row, 3, old_value_item)

            # New value
            new_value_item = QTableWidgetItem(str(update.new_value) if update.new_value else "-")
            self.updates_table.setItem(row, 4, new_value_item)

            # Highlight if affects certificates
            if update.affects_certificates:
                for col in range(1, 5):
                    item = self.updates_table.item(row, col)
                    if item:
                        item.setBackground(QColor("#fff3cd"))  # Light yellow

        # Enable buttons
        self.btn_select_all.setEnabled(True)
        self.btn_deselect_all.setEnabled(True)
        self.btn_apply.setEnabled(True)

        # Update info label
        cert_affecting = sum(1 for u in self.detected_updates if u.affects_certificates)
        self.info_label.setText(
            f"Hittade {len(self.detected_updates)} uppdateringar. "
            f"{cert_affecting} påverkar certifikat (gul markering) och kommer ta bort dem."
        )

    def _get_field_display_name(self, field_name: str) -> str:
        """Get display name for field."""
        field_names = {
            'charge_number': 'Chargenummer',
            'batch_id': 'Batchnummer',
            'quantity': 'Antal',
            'description': 'Beskrivning',
            'level_number': 'Nivå',
        }
        return field_names.get(field_name, field_name)

    def _select_all_updates(self):
        """Select all updates."""
        for row in range(self.updates_table.rowCount()):
            checkbox_widget = self.updates_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(True)

    def _deselect_all_updates(self):
        """Deselect all updates."""
        for row in range(self.updates_table.rowCount()):
            checkbox_widget = self.updates_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)
            if checkbox:
                checkbox.setChecked(False)

    def _apply_updates(self):
        """Apply selected updates."""
        # Get selected updates
        selected_updates = []

        for row in range(self.updates_table.rowCount()):
            checkbox_widget = self.updates_table.cellWidget(row, 0)
            checkbox = checkbox_widget.findChild(QCheckBox)

            if checkbox and checkbox.isChecked():
                selected_updates.append(self.detected_updates[row])

        if not selected_updates:
            QMessageBox.information(
                self,
                "Inga uppdateringar",
                "Inga uppdateringar valda att tillämpa."
            )
            return

        # Confirmation
        cert_affecting = sum(1 for u in selected_updates if u.affects_certificates)
        message = f"Tillämpa {len(selected_updates)} uppdateringar?"

        if cert_affecting > 0:
            message += f"\n\n⚠️ {cert_affecting} uppdateringar kommer ta bort befintliga certifikat."

        reply = QMessageBox.question(
            self,
            "Bekräfta uppdateringar",
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                ctx = self.wizard_ref.context

                # Apply updates
                result = update_ops.apply_updates(
                    db=ctx.database,
                    project_id=ctx.current_project_id,
                    selected_updates=selected_updates
                )

                logger.info(f"Applied {result['applied_count']} updates, removed {result['certificates_removed']} certificates")

                QMessageBox.information(
                    self,
                    "Uppdateringar tillämpade",
                    f"Tillämpade {result['applied_count']} uppdateringar.\n"
                    f"Tog bort {result['certificates_removed']} certifikat."
                )

                # Clear table
                self.updates_table.setRowCount(0)
                self.detected_updates = []
                self.selected_file = None
                self.file_label.setText("Ingen fil vald")
                self.info_label.setText("")

                # Disable buttons
                self.btn_select_all.setEnabled(False)
                self.btn_deselect_all.setEnabled(False)
                self.btn_apply.setEnabled(False)

            except Exception as e:
                logger.exception("Failed to apply updates")
                QMessageBox.critical(
                    self,
                    "Fel",
                    f"Kunde inte tillämpa uppdateringar: {e}"
                )
