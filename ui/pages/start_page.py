"""
Start Page for Tobbes v2 Wizard.

Recreates v1 UI with inline project creation and 7-column project list.
"""

import logging
import subprocess
from pathlib import Path
from datetime import datetime, timezone

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton,
        QLabel, QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit,
        QComboBox, QGroupBox, QFrame, QHeaderView
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from domain.validators import validate_order_number, validate_project_name
from domain.exceptions import ValidationError, DatabaseError
from ui.dialogs import CertTypesDialog
from config.paths import get_project_path

logger = logging.getLogger(__name__)


class StartPage(QWizardPage):
    """
    Start page - Project selection and creation.

    Matches Tobbes v1 UI:
    - Welcome section with bullet points
    - Inline project creation form (not dialog)
    - 7-column project table with verification status
    - Multiple action buttons
    """

    def __init__(self, wizard):
        """Initialize start page."""
        super().__init__()

        self.wizard_ref = wizard
        self.selected_project_id = None

        self._setup_ui()
        self._load_projects()

    def initializePage(self):
        """
        Called when page is shown.

        Reload projects to show any updates made while in project view.
        """
        logger.debug("Initializing start page - reloading projects")
        self._load_projects()

    def _setup_ui(self):
        """Setup UI components matching v1 layout."""
        self.setTitle("Tobbes - Spårbarhetsguiden")

        layout = QVBoxLayout()

        # Welcome section with HTML bullets
        welcome_html = """
        <h3>Välkommen till Spårbarhetsguiden</h3>
        <p>Denna guide hjälper dig att:</p>
        <ul style="margin-left: 20px;">
            <li>Importera nivålistor och lagerloggar</li>
            <li>Matcha artiklar med chargenummer</li>
            <li>Bifoga certifikat och intyg</li>
            <li>Generera färdiga PDF-rapporter</li>
        </ul>
        """
        welcome_label = QLabel(welcome_html)
        welcome_label.setWordWrap(True)
        layout.addWidget(welcome_label)

        # Separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # === PROJECT CREATION GROUP ===
        create_group = QGroupBox("Skapa nytt projekt")
        create_layout = QGridLayout()

        # Row 0: Artikelbenämning (project_name)
        create_layout.addWidget(QLabel("Artikelbenämning:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("T.ex. 'Stålkonstruktion'")
        create_layout.addWidget(self.name_edit, 0, 1, 1, 3)

        # Row 1: Ordernummer
        create_layout.addWidget(QLabel("Ordernummer:"), 1, 0)
        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("T.ex. 'TO-2024-001'")
        create_layout.addWidget(self.order_edit, 1, 1, 1, 3)

        # Row 2: Beställningsnummer (NEW)
        create_layout.addWidget(QLabel("Beställningsnummer:"), 2, 0)
        self.purchase_order_edit = QLineEdit()
        self.purchase_order_edit.setPlaceholderText("T.ex. 'BI-2024-001' (valfritt)")
        create_layout.addWidget(self.purchase_order_edit, 2, 1, 1, 3)

        # Row 3: Typ + Kund (on same row)
        create_layout.addWidget(QLabel("Typ:"), 3, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Doc", "Ej Doc"])
        create_layout.addWidget(self.type_combo, 3, 1)

        create_layout.addWidget(QLabel("Kund:"), 3, 2)
        self.customer_edit = QLineEdit()
        self.customer_edit.setPlaceholderText("T.ex. 'Volvo AB'")
        self.customer_edit.returnPressed.connect(self._create_project_from_form)
        create_layout.addWidget(self.customer_edit, 3, 3)

        # Row 4: Create button
        self.btn_create = QPushButton("Skapa projekt")
        self.btn_create.clicked.connect(self._create_project_from_form)
        create_layout.addWidget(self.btn_create, 4, 0, 1, 4)

        create_group.setLayout(create_layout)
        layout.addWidget(create_group)

        # === RECENT PROJECTS GROUP ===
        projects_group = QGroupBox("Senaste projekt")
        projects_layout = QVBoxLayout()

        # Projects table - 7 columns
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(7)
        self.projects_table.setHorizontalHeaderLabels([
            "Beställningsnr", "Ordernr", "Artikelbenämning",
            "Typ", "Kund", "Verifierade", "Senast ändrad"
        ])
        self.projects_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.projects_table.setSelectionMode(QTableWidget.SingleSelection)
        self.projects_table.doubleClicked.connect(self._open_selected_project)
        self.projects_table.itemSelectionChanged.connect(self._on_selection_changed)

        # Enable sorting by clicking column headers
        self.projects_table.setSortingEnabled(True)

        # Hide vertical header (row numbers)
        self.projects_table.verticalHeader().setVisible(False)

        # Configure column resize behavior
        header = self.projects_table.horizontalHeader()

        # Fixed-width columns (resize to content)
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Beställningsnr
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Ordernr
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Typ
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Verifierade
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Senast ändrad

        # Stretch columns (expand with window)
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Artikelbenämning (huvudkolumn)
        header.setSectionResizeMode(4, QHeaderView.Stretch)  # Kund (kan vara lång)

        projects_layout.addWidget(self.projects_table)

        # Action buttons (aligned to right)
        button_layout = QHBoxLayout()

        # Stretch first to push buttons to the right
        button_layout.addStretch()

        self.btn_cert_types = QPushButton("Redigera intygstyper")
        self.btn_cert_types.clicked.connect(self._edit_certificate_types)
        button_layout.addWidget(self.btn_cert_types)

        self.btn_open_folder = QPushButton("Öppna projektmapp")
        self.btn_open_folder.clicked.connect(self._open_project_folder)
        self.btn_open_folder.setEnabled(False)
        button_layout.addWidget(self.btn_open_folder)

        projects_layout.addLayout(button_layout)

        projects_group.setLayout(projects_layout)
        layout.addWidget(projects_group)

        self.setLayout(layout)

    def _load_projects(self):
        """Load projects from database with statistics."""
        try:
            db = self.wizard_ref.context.database

            # Load projects (default sort: newest first)
            projects = db.list_projects(limit=100, order_by="updated_at DESC")

            self.projects_table.setRowCount(len(projects))

            for row, project in enumerate(projects):
                # Get statistics for verification count
                try:
                    stats = db.get_project_statistics(project["id"])
                    verified_text = f"{stats['verified_articles']}/{stats['total_articles']}"
                except Exception as e:
                    logger.warning(f"Could not get stats for project {project['id']}: {e}")
                    verified_text = "0/0"

                # Column 0: Beställningsnummer
                purchase_order = project.get("purchase_order_number") or ""
                item_0 = QTableWidgetItem(purchase_order)
                item_0.setData(Qt.UserRole, project["id"])  # Store project ID in first column
                self.projects_table.setItem(row, 0, item_0)

                # Column 1: Ordernummer
                self.projects_table.setItem(row, 1, QTableWidgetItem(project["order_number"]))

                # Column 2: Artikelbenämning
                self.projects_table.setItem(row, 2, QTableWidgetItem(project["project_name"]))

                # Column 3: Typ
                project_type = project.get("project_type", "Doc")
                self.projects_table.setItem(row, 3, QTableWidgetItem(project_type))

                # Column 4: Kund
                self.projects_table.setItem(row, 4, QTableWidgetItem(project["customer"]))

                # Column 5: Verifierade (X/Y)
                self.projects_table.setItem(row, 5, QTableWidgetItem(verified_text))

                # Column 6: Senast ändrad
                updated = project.get("updated_at", project["created_at"])
                # Format datetime if it's a string
                if isinstance(updated, str):
                    try:
                        # Parse timestamp (SQLite returns naive UTC string without timezone marker)
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))

                        # If naive datetime, assume it's UTC (SQLite's CURRENT_TIMESTAMP is always UTC)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)

                        # Convert to local timezone
                        local_dt = dt.astimezone()
                        updated = local_dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        pass  # Keep as-is if parsing fails
                self.projects_table.setItem(row, 6, QTableWidgetItem(str(updated)))

            logger.info(f"Loaded {len(projects)} projects")

        except Exception as e:
            logger.exception("Failed to load projects")
            QMessageBox.critical(self, "Fel", f"Kunde inte ladda projekt: {e}")

    def _on_selection_changed(self):
        """Handle table selection change."""
        has_selection = len(self.projects_table.selectedItems()) > 0
        self.btn_open_folder.setEnabled(has_selection)

    def _create_project_from_form(self):
        """Create project from inline form (not dialog)."""
        try:
            # Get values from form
            project_name = self.name_edit.text().strip()
            order_number = self.order_edit.text().strip()
            purchase_order_number = self.purchase_order_edit.text().strip() or None
            project_type = self.type_combo.currentText()
            customer = self.customer_edit.text().strip()

            # Debug: Log form values
            logger.debug(
                f"Creating project with values: "
                f"name='{project_name}', order='{order_number}', "
                f"purchase_order='{purchase_order_number}', type='{project_type}', "
                f"customer='{customer}'"
            )

            # Validate
            validate_project_name(project_name)
            validate_order_number(order_number)
            if not customer:
                raise ValidationError("Kundnamn krävs")

            # Create project
            db = self.wizard_ref.context.database
            project_id = db.save_project(
                project_name=project_name,
                order_number=order_number,
                customer=customer,
                created_by=self.wizard_ref.context.user_name,
                purchase_order_number=purchase_order_number,
                project_type=project_type,
            )

            logger.info(f"Created project: id={project_id}, name={project_name}")

            # Clear form
            self.name_edit.clear()
            self.order_edit.clear()
            self.purchase_order_edit.clear()
            self.customer_edit.clear()
            self.type_combo.setCurrentIndex(0)  # Reset to "Doc"

            # Reload projects
            self._load_projects()

            # Select the new project
            for row in range(self.projects_table.rowCount()):
                item = self.projects_table.item(row, 0)
                if item and item.data(Qt.UserRole) == project_id:
                    self.projects_table.selectRow(row)
                    break

        except (ValidationError, DatabaseError) as e:
            logger.error(f"Failed to create project: {e}")
            QMessageBox.warning(self, "Fel", str(e))

            # Add red border to invalid fields (v1 feature)
            if "project_name" in str(e).lower():
                self.name_edit.setStyleSheet("border: 1px solid red;")
            if "order" in str(e).lower():
                self.order_edit.setStyleSheet("border: 1px solid red;")
            if "kund" in str(e).lower():
                self.customer_edit.setStyleSheet("border: 1px solid red;")

        except Exception as e:
            logger.exception("Unexpected error creating project")
            QMessageBox.critical(self, "Fel", f"Oväntat fel: {e}")

    def _open_selected_project(self):
        """Open selected project (navigate to project view page in same window)."""
        selected = self.projects_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        project_id_item = self.projects_table.item(row, 0)
        project_id = project_id_item.data(Qt.UserRole)
        project_name = self.projects_table.item(row, 2).text()  # Column 2 is name

        # Set current project in wizard context
        self.wizard_ref.set_current_project(project_id, project_name)
        logger.info(f"Opening project: id={project_id}, name={project_name}")

        # Navigate to project view page (same window!)
        self.wizard_ref.setCurrentId(self.wizard_ref.PAGE_PROJECT_VIEW)

        logger.info(f"Navigated to project view for: {project_name}")


    def _edit_certificate_types(self):
        """Edit global certificate types."""
        try:
            dialog = CertTypesDialog(
                database=self.wizard_ref.context.database,
                project_id=None,  # None = global types only
                parent=self
            )
            dialog.exec()
            logger.info("Certificate types dialog closed")
        except Exception as e:
            logger.exception("Failed to open certificate types dialog")
            QMessageBox.critical(self, "Fel", f"Kunde inte öppna dialog: {e}")

    def _open_project_folder(self):
        """Open project folder in file explorer."""
        selected = self.projects_table.selectedItems()
        if not selected:
            return

        row = selected[0].row()
        order_number = self.projects_table.item(row, 1).text()  # Ordernr (column 1)

        try:
            # Get project folder path (projects/{order_number}/)
            project_folder = get_project_path(order_number)

            # Open folder in file explorer (cross-platform)
            import platform
            system = platform.system()

            if system == "Windows":
                subprocess.run(["explorer", str(project_folder)])
            elif system == "Darwin":  # macOS
                subprocess.run(["open", str(project_folder)])
            else:  # Linux
                subprocess.run(["xdg-open", str(project_folder)])

            logger.info(f"Opened project folder: {project_folder}")

        except Exception as e:
            logger.exception("Failed to open project folder")
            QMessageBox.warning(
                self,
                "Fel",
                f"Kunde inte öppna projektmapp: {e}"
            )
