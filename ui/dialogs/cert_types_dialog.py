"""
Certificate Types Dialog.

Manage global and project-specific certificate types.
"""

import logging
from typing import List, Optional

try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QPushButton, QListWidget, QLineEdit, QMessageBox,
        QDialogButtonBox, QGroupBox, QTableWidget, QTableWidgetItem,
        QFileDialog, QHeaderView
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QDialog = object

from domain.exceptions import ValidationError, DatabaseError

logger = logging.getLogger(__name__)


class CertTypesDialog(QDialog):
    """
    Dialog for managing certificate types.

    Features:
    - View global certificate types
    - View project-specific certificate types
    - Add new certificate types
    - Remove certificate types
    - Reorder certificate types
    """

    def __init__(self, database, project_id: Optional[int] = None, parent=None):
        """
        Initialize dialog.

        Args:
            database: Database instance
            project_id: Optional project ID for project-specific types
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.database = database
        self.project_id = project_id

        self._setup_ui()
        self._load_certificate_types()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("Hantera certifikattyper")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Global types section (ONLY if no project_id - global mode)
        if not self.project_id:
            global_group = QGroupBox("Globala certifikattyper")
            global_layout = QVBoxLayout()

            global_label = QLabel("Dessa typer är tillgängliga för alla projekt:")
            global_layout.addWidget(global_label)

            # Table with columns: Type, Search Path
            self.global_table = QTableWidget()
            self.global_table.setColumnCount(2)
            self.global_table.setHorizontalHeaderLabels(["Certifikattyp", "Sökväg"])
            self.global_table.horizontalHeader().setStretchLastSection(True)
            self.global_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            self.global_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.global_table.setSelectionMode(QTableWidget.SingleSelection)
            self.global_table.verticalHeader().setVisible(False)  # Hide row numbers
            global_layout.addWidget(self.global_table)

            # Global types buttons
            global_buttons = QHBoxLayout()

            self.btn_add_global = QPushButton("Lägg till")
            self.btn_add_global.clicked.connect(self._add_global_type)
            global_buttons.addWidget(self.btn_add_global)

            self.btn_set_path = QPushButton("Välj mapp...")
            self.btn_set_path.clicked.connect(self._set_search_path)
            self.btn_set_path.setEnabled(False)
            global_buttons.addWidget(self.btn_set_path)

            self.btn_remove_global = QPushButton("Ta bort")
            self.btn_remove_global.clicked.connect(self._remove_global_type)
            self.btn_remove_global.setEnabled(False)
            global_buttons.addWidget(self.btn_remove_global)

            global_buttons.addStretch()
            global_layout.addLayout(global_buttons)

            global_group.setLayout(global_layout)
            layout.addWidget(global_group)

            # Connect selection changed for global table
            self.global_table.itemSelectionChanged.connect(self._on_global_selection_changed)

        # Project-specific types section (ONLY if project_id provided)
        if self.project_id:
            project_group = QGroupBox("Projektspecifika certifikattyper")
            project_layout = QVBoxLayout()

            project_label = QLabel("Dessa typer är bara för detta projekt:")
            project_layout.addWidget(project_label)

            self.project_list = QListWidget()
            project_layout.addWidget(self.project_list)

            # Project types buttons
            project_buttons = QHBoxLayout()

            self.btn_add_project = QPushButton("Lägg till")
            self.btn_add_project.clicked.connect(self._add_project_type)
            project_buttons.addWidget(self.btn_add_project)

            self.btn_remove_project = QPushButton("Ta bort")
            self.btn_remove_project.clicked.connect(self._remove_project_type)
            self.btn_remove_project.setEnabled(False)
            project_buttons.addWidget(self.btn_remove_project)

            project_buttons.addStretch()
            project_layout.addLayout(project_buttons)

            project_group.setLayout(project_layout)
            layout.addWidget(project_group)

            # Connect selection changed
            self.project_list.itemSelectionChanged.connect(self._on_project_selection_changed)

        # Dialog buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.accept)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def _load_certificate_types(self):
        """Load certificate types from database."""
        try:
            if not self.project_id:
                # Global mode: Load global types with paths
                types_with_paths = self.database.get_certificate_types_with_paths(None)

                # Filter to only global types
                global_types = [t for t in types_with_paths if t['is_global']]

                self.global_table.setRowCount(len(global_types))
                for row, cert_type in enumerate(global_types):
                    # Column 0: Type name
                    type_item = QTableWidgetItem(cert_type['type_name'])
                    type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)  # Read-only
                    self.global_table.setItem(row, 0, type_item)

                    # Column 1: Search path
                    path_text = cert_type['search_path'] or ""
                    path_item = QTableWidgetItem(path_text)
                    path_item.setFlags(path_item.flags() & ~Qt.ItemIsEditable)  # Read-only
                    self.global_table.setItem(row, 1, path_item)

                logger.info(f"Loaded {len(global_types)} global certificate types")
            else:
                # Project mode: Load only project-specific types
                project_types = self.database.get_certificate_types(self.project_id)
                self.project_list.clear()
                self.project_list.addItems(project_types)
                logger.info(f"Loaded {len(project_types)} project certificate types")

        except Exception as e:
            logger.exception("Failed to load certificate types")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte ladda certifikattyper: {e}"
            )

    def _on_global_selection_changed(self):
        """Handle global table selection change."""
        has_selection = len(self.global_table.selectedItems()) > 0
        self.btn_remove_global.setEnabled(has_selection)
        self.btn_set_path.setEnabled(has_selection)

    def _on_project_selection_changed(self):
        """Handle project list selection change."""
        has_selection = len(self.project_list.selectedItems()) > 0
        self.btn_remove_project.setEnabled(has_selection)

    def _set_search_path(self):
        """Set search path for selected certificate type."""
        current_row = self.global_table.currentRow()
        if current_row < 0:
            return

        # Get selected type name
        type_name = self.global_table.item(current_row, 0).text()

        # Get current search path (if any)
        current_path = self.global_table.item(current_row, 1).text()

        # Open directory selection dialog
        directory = QFileDialog.getExistingDirectory(
            self,
            f"Välj mapp för {type_name}",
            current_path if current_path else "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if directory:
            try:
                # Update database
                success = self.database.update_certificate_type_search_path(
                    type_name=type_name,
                    search_path=directory
                )

                if success:
                    # Reload table
                    self._load_certificate_types()

                    logger.info(f"Updated search_path for '{type_name}': {directory}")

                    QMessageBox.information(
                        self,
                        "Uppdaterad",
                        f"Sökväg för '{type_name}' har uppdaterats."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Misslyckades",
                        f"Kunde inte uppdatera sökväg för '{type_name}'."
                    )

            except Exception as e:
                logger.exception("Failed to update search path")
                QMessageBox.critical(self, "Fel", f"Kunde inte uppdatera sökväg: {e}")

    def _add_global_type(self):
        """Add new global certificate type."""
        type_name, ok = self._prompt_for_type_name("Lägg till global certifikattyp")

        if ok and type_name:
            try:
                # Check if already exists
                existing_types = [
                    self.global_table.item(row, 0).text()
                    for row in range(self.global_table.rowCount())
                ]

                if type_name in existing_types:
                    QMessageBox.warning(
                        self,
                        "Finns redan",
                        f"Certifikattypen '{type_name}' finns redan i globala typer."
                    )
                    return

                # Add to database (no search_path initially)
                self.database.add_certificate_type(type_name, None, None)

                # Reload table
                self._load_certificate_types()

                logger.info(f"Added global certificate type: {type_name}")

                QMessageBox.information(
                    self,
                    "Tillagd",
                    f"Certifikattypen '{type_name}' har lagts till."
                )

            except Exception as e:
                logger.exception("Failed to add global certificate type")
                QMessageBox.critical(self, "Fel", f"Kunde inte lägga till typ: {e}")

    def _add_project_type(self):
        """Add new project-specific certificate type."""
        type_name, ok = self._prompt_for_type_name("Lägg till projektspecifik certifikattyp")

        if ok and type_name:
            try:
                # Check if already exists (global or project)
                all_types = [
                    self.global_list.item(i).text()
                    for i in range(self.global_list.count())
                ]
                all_types += [
                    self.project_list.item(i).text()
                    for i in range(self.project_list.count())
                ]

                if type_name in all_types:
                    QMessageBox.warning(
                        self,
                        "Finns redan",
                        f"Certifikattypen '{type_name}' finns redan."
                    )
                    return

                # Add to database
                self.database.add_certificate_type(type_name, self.project_id)

                # Reload list
                self._load_certificate_types()

                logger.info(f"Added project certificate type: {type_name} (project_id={self.project_id})")

                QMessageBox.information(
                    self,
                    "Tillagd",
                    f"Certifikattypen '{type_name}' har lagts till för detta projekt."
                )

            except Exception as e:
                logger.exception("Failed to add project certificate type")
                QMessageBox.critical(self, "Fel", f"Kunde inte lägga till typ: {e}")

    def _remove_global_type(self):
        """Remove selected global certificate type."""
        current_row = self.global_table.currentRow()

        if current_row < 0:
            return

        type_name = self.global_table.item(current_row, 0).text()

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Bekräfta borttagning",
            f"Vill du ta bort den globala certifikattypen '{type_name}'?\n\n"
            f"Detta påverkar ALLA projekt.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.database.delete_certificate_type(type_name, None)

                # Reload table
                self._load_certificate_types()

                logger.info(f"Removed global certificate type: {type_name}")

                QMessageBox.information(
                    self,
                    "Borttagen",
                    f"Certifikattypen '{type_name}' har tagits bort."
                )

            except Exception as e:
                logger.exception("Failed to remove global certificate type")
                QMessageBox.critical(self, "Fel", f"Kunde inte ta bort typ: {e}")

    def _remove_project_type(self):
        """Remove selected project-specific certificate type."""
        selected = self.project_list.selectedItems()

        if not selected:
            return

        type_name = selected[0].text()

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Bekräfta borttagning",
            f"Vill du ta bort certifikattypen '{type_name}' från detta projekt?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.database.delete_certificate_type(type_name, self.project_id)

                # Reload list
                self._load_certificate_types()

                logger.info(f"Removed project certificate type: {type_name} (project_id={self.project_id})")

                QMessageBox.information(
                    self,
                    "Borttagen",
                    f"Certifikattypen '{type_name}' har tagits bort från projektet."
                )

            except Exception as e:
                logger.exception("Failed to remove project certificate type")
                QMessageBox.critical(self, "Fel", f"Kunde inte ta bort typ: {e}")

    def _prompt_for_type_name(self, title: str) -> tuple[str, bool]:
        """
        Show dialog to prompt for certificate type name.

        Args:
            title: Dialog title

        Returns:
            (type_name, ok) tuple
        """
        from PySide6.QtWidgets import QInputDialog

        type_name, ok = QInputDialog.getText(
            self,
            title,
            "Certifikattyp:",
            text=""
        )

        return type_name.strip(), ok

    def get_all_types(self) -> List[str]:
        """
        Get all certificate types (global + project).

        Returns:
            List of certificate type names
        """
        types = [
            self.global_list.item(i).text()
            for i in range(self.global_list.count())
        ]

        if self.project_id and hasattr(self, 'project_list'):
            types += [
                self.project_list.item(i).text()
                for i in range(self.project_list.count())
            ]

        return types
