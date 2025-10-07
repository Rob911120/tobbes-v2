"""
Start Page for Tobbes v2 Wizard.

Project selection and creation.
"""

import logging
from datetime import datetime

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QTableWidget, QTableWidgetItem, QMessageBox,
        QDialog, QFormLayout, QLineEdit, QTextEdit, QDialogButtonBox
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from domain.validators import validate_order_number, validate_project_name
from domain.exceptions import ValidationError, DatabaseError

logger = logging.getLogger(__name__)


class StartPage(QWizardPage):
    """
    Start page - Project selection and creation.

    Features:
    - List existing projects
    - Create new project
    - Open existing project
    - Delete project
    """

    def __init__(self, wizard):
        """Initialize start page."""
        super().__init__()

        self.wizard_ref = wizard
        self.selected_project_id = None

        self._setup_ui()
        self._load_projects()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Välkommen till Tobbes - Spårbarhetsguiden")
        self.setSubTitle("Välj ett befintligt projekt eller skapa ett nytt.")

        layout = QVBoxLayout()

        # Header
        header = QLabel("Mina Projekt")
        header.setProperty("class", "header")
        layout.addWidget(header)

        # Projects table
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(4)
        self.projects_table.setHorizontalHeaderLabels([
            "Projektnamn", "Ordernummer", "Kund", "Senast uppdaterad"
        ])
        self.projects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.projects_table.setSelectionMode(QTableWidget.SingleSelection)
        self.projects_table.doubleClicked.connect(self._open_selected_project)
        layout.addWidget(self.projects_table)

        # Buttons
        button_layout = QHBoxLayout()

        self.btn_new = QPushButton("Nytt Projekt")
        self.btn_new.clicked.connect(self._create_new_project)
        button_layout.addWidget(self.btn_new)

        self.btn_open = QPushButton("Öppna")
        self.btn_open.clicked.connect(self._open_selected_project)
        self.btn_open.setEnabled(False)
        button_layout.addWidget(self.btn_open)

        self.btn_delete = QPushButton("Radera")
        self.btn_delete.clicked.connect(self._delete_selected_project)
        self.btn_delete.setEnabled(False)
        button_layout.addWidget(self.btn_delete)

        button_layout.addStretch()
        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Connect selection changed
        self.projects_table.itemSelectionChanged.connect(self._on_selection_changed)

    def _load_projects(self):
        """Load projects from database."""
        try:
            db = self.wizard_ref.context.database
            projects = db.list_projects(limit=100, order_by="updated_at DESC")

            self.projects_table.setRowCount(len(projects))

            for row, project in enumerate(projects):
                # Project name
                name_item = QTableWidgetItem(project["project_name"])
                name_item.setData(Qt.UserRole, project["id"])  # Store project ID
                self.projects_table.setItem(row, 0, name_item)

                # Order number
                self.projects_table.setItem(row, 1, QTableWidgetItem(project["order_number"]))

                # Customer
                self.projects_table.setItem(row, 2, QTableWidgetItem(project["customer"]))

                # Updated at
                updated = project.get("updated_at", project["created_at"])
                self.projects_table.setItem(row, 3, QTableWidgetItem(updated))

            self.projects_table.resizeColumnsToContents()

            logger.info(f"Loaded {len(projects)} projects")

        except Exception as e:
            logger.exception("Failed to load projects")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte ladda projekt: {e}"
            )

    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.projects_table.selectedItems()) > 0
        self.btn_open.setEnabled(has_selection)
        self.btn_delete.setEnabled(has_selection)

    def _create_new_project(self):
        """Show dialog to create new project."""
        dialog = NewProjectDialog(self)

        if dialog.exec() == QDialog.Accepted:
            try:
                db = self.wizard_ref.context.database

                # Create project
                project_id = db.save_project(
                    project_name=dialog.project_name,
                    order_number=dialog.order_number,
                    customer=dialog.customer,
                    created_by=self.wizard_ref.context.user_name,
                    description=dialog.description,
                )

                logger.info(f"Created new project: id={project_id}, name={dialog.project_name}")

                # Reload projects
                self._load_projects()

                # Select the new project
                for row in range(self.projects_table.rowCount()):
                    item = self.projects_table.item(row, 0)
                    if item and item.data(Qt.UserRole) == project_id:
                        self.projects_table.selectRow(row)
                        break

                QMessageBox.information(
                    self,
                    "Projekt skapat",
                    f"Projektet '{dialog.project_name}' har skapats."
                )

            except (ValidationError, DatabaseError) as e:
                logger.error(f"Failed to create project: {e}")
                QMessageBox.warning(self, "Fel", str(e))

            except Exception as e:
                logger.exception("Unexpected error creating project")
                QMessageBox.critical(self, "Fel", f"Oväntat fel: {e}")

    def _open_selected_project(self):
        """Open selected project."""
        selected = self.projects_table.selectedItems()

        if not selected:
            return

        # Get project ID from first column
        row = selected[0].row()
        project_id_item = self.projects_table.item(row, 0)
        project_id = project_id_item.data(Qt.UserRole)
        project_name = project_id_item.text()

        # Set current project in wizard context
        self.wizard_ref.set_current_project(project_id, project_name)

        logger.info(f"Opened project: id={project_id}, name={project_name}")

        # Move to next page
        self.wizard_ref.next()

    def _delete_selected_project(self):
        """Delete selected project after confirmation."""
        selected = self.projects_table.selectedItems()

        if not selected:
            return

        row = selected[0].row()
        project_name = self.projects_table.item(row, 0).text()
        project_id = self.projects_table.item(row, 0).data(Qt.UserRole)

        # Confirmation dialog
        reply = QMessageBox.question(
            self,
            "Bekräfta radering",
            f"Är du säker på att du vill radera projektet '{project_name}'?\n\n"
            f"Detta kommer radera alla artiklar, certifikat och rapporter.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                db = self.wizard_ref.context.database
                db.delete_project(project_id)

                logger.info(f"Deleted project: id={project_id}, name={project_name}")

                # Reload projects
                self._load_projects()

                QMessageBox.information(
                    self,
                    "Projekt raderat",
                    f"Projektet '{project_name}' har raderats."
                )

            except Exception as e:
                logger.exception("Failed to delete project")
                QMessageBox.critical(self, "Fel", f"Kunde inte radera projekt: {e}")


class NewProjectDialog(QDialog):
    """Dialog for creating a new project."""

    def __init__(self, parent=None):
        """Initialize dialog."""
        super().__init__(parent)

        self.project_name = ""
        self.order_number = ""
        self.customer = ""
        self.description = ""

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setWindowTitle("Nytt Projekt")
        self.setModal(True)

        layout = QFormLayout()

        # Project name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("T.ex. 'Stålkonstruktion Göteborg'")
        layout.addRow("Projektnamn*:", self.name_edit)

        # Order number
        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("T.ex. 'TO-2024-001'")
        layout.addRow("Ordernummer*:", self.order_edit)

        # Customer
        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("T.ex. 'Volvo AB'")
        layout.addRow("Kund*:", self.customer_edit)

        # Description (optional)
        self.desc_edit = QTextEdit()
        self.desc_edit.setPlaceholderText("Beskrivning av projektet (valfritt)")
        self.desc_edit.setMaximumHeight(100)
        layout.addRow("Beskrivning:", self.desc_edit)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def _accept(self):
        """Validate and accept."""
        try:
            # Get values
            self.project_name = self.name_edit.text().strip()
            self.order_number = self.order_edit.text().strip()
            self.customer = self.customer_edit.text().strip()
            self.description = self.desc_edit.toPlainText().strip()

            # Validate
            validate_project_name(self.project_name)
            validate_order_number(self.order_number)

            if not self.customer:
                raise ValidationError("Kundnamn krävs")

            self.accept()

        except ValidationError as e:
            QMessageBox.warning(self, "Valideringsfel", str(e))
