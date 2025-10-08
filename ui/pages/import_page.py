"""
Import Page for Tobbes v2 Wizard.

Recreates the exact UI from Tobbes v1 with Monitor links and multi-file import.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QGroupBox, QFileDialog, QMessageBox,
        QListWidget, QListWidgetItem, QProgressBar
    )
    from PySide6.QtCore import Qt, QUrl
    from PySide6.QtGui import QFont, QDesktopServices, QCursor
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

    Features (matching v1):
    - Monitor links to open files directly in Monitor app
    - Single "Bläddra efter filer..." button for multiple files
    - Auto file type detection
    - QListWidget display with color-coding
    - "Rensa alla" button
    - Progress bar
    - Both files required for completion
    """

    def __init__(self, wizard):
        """Initialize import page."""
        super().__init__()

        self.wizard_ref = wizard
        self.imported_files = []  # List of {'path': Path, 'type': str, 'name': str}

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components matching v1."""
        self.setTitle("Importera filer")
        self.setSubTitle("Öppna filer via Monitor-länkarna eller välj lokala filer")

        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _create_widgets(self):
        """Create all widgets."""

        # Instructions
        self.instructions_label = QLabel("""
        <h3>Importera obligatoriska filtyper:</h3>
        <ul>
        <li><b>Nivålista</b> - Hierarkisk struktur av komponenter (KRÄVS)</li>
        <li><b>Lagerlogg</b> - Chargenummer och operationer (KRÄVS)</li>
        </ul>
        <p><i>Båda filer måste importeras för att fortsätta till bearbetning.</i></p>
        <p><i>Använd Monitor-länkarna nedan eller klicka på "Bläddra efter filer"</i></p>
        """)
        self.instructions_label.setWordWrap(True)

        # Monitor links area
        self.monitor_links_widget = QGroupBox("Monitor-länkar")
        self._create_monitor_links()

        # File display area (read-only)
        self.file_display_area = QListWidget()
        self.file_display_area.setMinimumHeight(200)
        self.file_display_area.setSelectionMode(QListWidget.NoSelection)

        # Style for file display area
        self.file_display_area.setStyleSheet("""
            QListWidget {
                border: 2px solid #cccccc;
                border-radius: 5px;
                background-color: #fafafa;
                font-size: 14px;
                color: #666666;
            }

            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #eeeeee;
            }
        """)

        # Add placeholder text initially
        self._add_placeholder_text()

        # Buttons
        self.browse_button = QPushButton("Bläddra efter filer...")
        self.clear_button = QPushButton("Rensa alla")
        self.clear_button.setEnabled(False)

        # Progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)

        # Status label
        self.status_label = QLabel("Inga filer importerade")
        self.status_label.setAlignment(Qt.AlignCenter)

        # File info group
        self.file_info_group = QGroupBox("Importerade filer")

    def _setup_layout(self):
        """Setup layout matching v1."""
        main_layout = QVBoxLayout()

        # Instructions
        main_layout.addWidget(self.instructions_label)

        # Monitor links and file display
        file_info_layout = QVBoxLayout()
        file_info_layout.addWidget(self.monitor_links_widget)
        file_info_layout.addWidget(self.file_display_area)

        # Progress bar
        file_info_layout.addWidget(self.progress_bar)

        # Status
        file_info_layout.addWidget(self.status_label)

        self.file_info_group.setLayout(file_info_layout)
        main_layout.addWidget(self.file_info_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.browse_button)
        button_layout.addWidget(self.clear_button)
        button_layout.addStretch()

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connect signals."""
        self.browse_button.clicked.connect(self._browse_files)
        self.clear_button.clicked.connect(self._clear_files)

        # Connect Monitor link signals
        self.nivalista_link.clicked.connect(self._open_nivalista_in_monitor)
        self.lagerlogg_link.clicked.connect(self._open_lagerlogg_in_monitor)

    def _create_monitor_links(self):
        """Create Monitor links widget with styled buttons."""
        layout = QVBoxLayout()

        # Nivålista link (blue)
        self.nivalista_link = QPushButton("Öppna Nivålista i Monitor")
        self.nivalista_link.setStyleSheet("""
            QPushButton {
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
                border-radius: 5px;
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #bbdefb;
            }
            QPushButton:pressed {
                background-color: #90caf9;
            }
        """)
        self.nivalista_link.setCursor(QCursor(Qt.PointingHandCursor))

        # Lagerlogg link (green)
        self.lagerlogg_link = QPushButton("Öppna Lagerlogg i Monitor")
        self.lagerlogg_link.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e8;
                border: 2px solid #4caf50;
                border-radius: 5px;
                padding: 10px;
                text-align: left;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
            QPushButton:pressed {
                background-color: #a5d6a7;
            }
        """)
        self.lagerlogg_link.setCursor(QCursor(Qt.PointingHandCursor))

        # Info text
        info_label = QLabel("<i>Klicka på länkarna ovan för att öppna filer direkt i Monitor</i>")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("color: #666666; margin: 5px;")

        layout.addWidget(self.nivalista_link)
        layout.addWidget(self.lagerlogg_link)
        layout.addWidget(info_label)

        self.monitor_links_widget.setLayout(layout)

    def _open_nivalista_in_monitor(self):
        """Open nivålista in Monitor app."""
        monitor_url = "mond://001.1/9f24436a-2e31-4bf5-9311-4e95abc4f8e7"
        if not QDesktopServices.openUrl(QUrl(monitor_url)):
            QMessageBox.warning(
                self,
                "Monitor ej tillgänglig",
                "Kunde inte öppna Monitor. Kontrollera att Monitor är installerat och körs."
            )

    def _open_lagerlogg_in_monitor(self):
        """Open lagerlogg in Monitor app."""
        monitor_url = "mond://001.1/ff3993a8-6baa-431e-9c79-aa47a3e2685a"
        if not QDesktopServices.openUrl(QUrl(monitor_url)):
            QMessageBox.warning(
                self,
                "Monitor ej tillgänglig",
                "Kunde inte öppna Monitor. Kontrollera att Monitor är installerat och körs."
            )

    def _add_placeholder_text(self):
        """Add placeholder text to file display area."""
        placeholder_texts = [
            "[INFO] Inga filer importerade ännu",
            "",
            "Använd Monitor-länkarna ovan eller 'Bläddra efter filer'-knappen",
            "",
            "Nödvändiga filer:",
            "• Nivålista (.xlsx, .xls, .csv) - KRÄVS",
            "• Lagerlogg (.xlsx, .xls) - KRÄVS"
        ]

        for text in placeholder_texts:
            item = QListWidgetItem(text)
            item.setFlags(Qt.NoItemFlags)  # Make item non-selectable

            if text.startswith("[INFO]"):
                font = QFont()
                font.setBold(True)
                font.setPointSize(12)
                item.setFont(font)
                item.setForeground(Qt.darkBlue)
            elif text.startswith("•"):
                item.setForeground(Qt.darkGreen)

            self.file_display_area.addItem(item)

    def _browse_files(self):
        """Open file browser dialog for multiple files."""
        try:
            filter_str = f"Excel-filer (*{' *'.join(EXCEL_EXTENSIONS)})"

            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Välj Excel-filer att importera",
                "",
                filter_str
            )

            if file_paths:
                valid_files = [Path(p) for p in file_paths if Path(p).exists()]
                if valid_files:
                    self._import_files(valid_files)
                else:
                    QMessageBox.warning(
                        self,
                        "Inga giltiga filer",
                        "Inga av de valda filerna kunde hittas."
                    )

        except Exception as e:
            logger.exception("Error browsing files")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte öppna filbläddring: {e}"
            )

    def _import_files(self, file_paths: List[Path]):
        """Import multiple files automatically with type detection."""
        try:
            logger.info(f"Importing {len(file_paths)} files")

            # Show progress
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, len(file_paths))
            self.progress_bar.setValue(0)

            # Clear placeholder text on first import
            if not self.imported_files:
                self.file_display_area.clear()

            imported_count = 0

            for i, file_path in enumerate(file_paths):
                try:
                    # Identify file type
                    file_type = self._identify_file_type(file_path)

                    # Check if this type already exists
                    existing = [f for f in self.imported_files if f['type'] == file_type]
                    if existing:
                        reply = QMessageBox.question(
                            self,
                            "Ersätt fil?",
                            f"{file_type} finns redan importerad.\n\n"
                            f"Vill du ersätta med '{file_path.name}'?",
                            QMessageBox.Yes | QMessageBox.No
                        )

                        if reply == QMessageBox.No:
                            self.progress_bar.setValue(i + 1)
                            continue

                        # Remove old file from list and UI
                        self.imported_files = [f for f in self.imported_files if f['type'] != file_type]
                        for j in range(self.file_display_area.count()):
                            item = self.file_display_area.item(j)
                            if item and file_type in item.text():
                                self.file_display_area.takeItem(j)
                                break

                    # Import based on type
                    success = False
                    if file_type == "NIVÅLISTA":
                        success = self._import_nivalista_file(file_path)
                    elif file_type == "LAGERLOGG":
                        success = self._import_lagerlogg_file(file_path)
                    else:
                        logger.warning(f"Unknown file type: {file_type}")

                    if success:
                        # Add to UI
                        item = QListWidgetItem(f"[OK] {file_type}: {file_path.name}")
                        item.setData(Qt.UserRole, str(file_path))

                        # Color coding
                        if file_type in ["NIVÅLISTA", "LAGERLOGG"]:
                            item.setForeground(Qt.darkGreen)
                        else:
                            item.setForeground(Qt.darkRed)

                        self.file_display_area.addItem(item)

                        # Add to imported files list
                        self.imported_files.append({
                            'path': file_path,
                            'type': file_type,
                            'name': file_path.name
                        })

                        imported_count += 1

                except Exception as e:
                    logger.exception(f"Error importing {file_path}")
                    # Add as error
                    item = QListWidgetItem(f"[FEL] {file_path.name}: {str(e)}")
                    item.setForeground(Qt.red)
                    self.file_display_area.addItem(item)

                # Update progress
                self.progress_bar.setValue(i + 1)

            # Update status
            self.status_label.setText(f"Importerade {imported_count} av {len(file_paths)} filer")
            self.clear_button.setEnabled(len(self.imported_files) > 0)

            # Hide progress after delay
            self.progress_bar.setVisible(False)

            # Notify wizard that page completion may have changed
            self.completeChanged.emit()

            logger.info(f"Import complete: {imported_count} files")

        except Exception as e:
            logger.exception("Error during import")
            QMessageBox.critical(
                self,
                "Import misslyckades",
                f"Kunde inte importera filer: {e}"
            )
            self.progress_bar.setVisible(False)

    def _identify_file_type(self, file_path: Path) -> str:
        """
        Identify file type based on filename.

        Returns:
            File type string (NIVÅLISTA, LAGERLOGG, BOM, PLM, OKÄND)
        """
        file_name = file_path.name.lower()

        if 'nivå' in file_name or 'level' in file_name:
            return "NIVÅLISTA"
        elif 'lager' in file_name or 'stock' in file_name:
            return "LAGERLOGG"
        elif 'bom' in file_name or 'bill' in file_name:
            return "BOM"
        elif 'plm' in file_name:
            return "PLM"
        else:
            return "OKÄND"

    def _import_nivalista_file(self, file_path: Path) -> bool:
        """Import nivålista file and save to database."""
        try:
            logger.info(f"Importing nivålista: {file_path}")
            articles = import_nivalista(file_path)

            # Save to database
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database
            db.save_project_articles(project_id, articles)

            logger.info(f"Imported {len(articles)} articles from nivålista")
            return True

        except (ImportValidationError, DatabaseError) as e:
            logger.error(f"Import error: {e}")
            QMessageBox.warning(
                self,
                "Import misslyckades",
                f"Kunde inte importera nivålista:\n\n{e.message}"
            )
            return False
        except Exception as e:
            logger.exception("Unexpected error importing nivålista")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Kunde inte importera nivålista:\n\n{str(e)}"
            )
            return False

    def _import_lagerlogg_file(self, file_path: Path) -> bool:
        """Import lagerlogg file and save to database."""
        try:
            logger.info(f"Importing lagerlogg: {file_path}")
            inventory = import_lagerlogg(file_path)

            # Save to database
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database
            db.save_inventory_items(project_id, inventory)

            logger.info(f"Imported {len(inventory)} inventory items from lagerlogg")
            return True

        except (ImportValidationError, DatabaseError) as e:
            logger.error(f"Import error: {e}")
            QMessageBox.warning(
                self,
                "Import misslyckades",
                f"Kunde inte importera lagerlogg:\n\n{e.message}"
            )
            return False
        except Exception as e:
            logger.exception("Unexpected error importing lagerlogg")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Kunde inte importera lagerlogg:\n\n{str(e)}"
            )
            return False

    def _clear_files(self):
        """Clear all imported files."""
        reply = QMessageBox.question(
            self,
            "Rensa filer",
            "Är du säker på att du vill rensa alla importerade filer?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.imported_files.clear()
            self.file_display_area.clear()
            self._add_placeholder_text()
            self.status_label.setText("Inga filer importerade")
            self.clear_button.setEnabled(False)

            # Notify wizard that page is no longer complete
            self.completeChanged.emit()

            logger.info("All files cleared")

    def initializePage(self):
        """Initialize page when entering."""
        # Clear previous imports if user goes back
        self.imported_files = []
        self.file_display_area.clear()
        self._add_placeholder_text()
        self.status_label.setText("Inga filer importerade")
        self.clear_button.setEnabled(False)

        # Verify project is selected
        try:
            project_id = self.wizard_ref.context.require_project()
            logger.info(f"Import page initialized for project: {project_id}")
        except ValueError:
            QMessageBox.critical(
                self,
                "Fel",
                "Inget projekt valt. Gå tillbaka och välj ett projekt."
            )

    def isComplete(self):
        """Page is complete when BOTH nivålista AND lagerlogg are imported."""
        has_nivalista = any(f['type'] == 'NIVÅLISTA' for f in self.imported_files)
        has_lagerlogg = any(f['type'] == 'LAGERLOGG' for f in self.imported_files)
        return has_nivalista and has_lagerlogg

    def start_processing(self):
        """
        Start processing imported files (called by wizard button).

        Validates files are imported, then navigates to PROCESS page.
        """
        try:
            if not self.isComplete():
                QMessageBox.warning(
                    self,
                    "Validering misslyckades",
                    "Du måste importera både nivålista och lagerlogg innan du kan fortsätta."
                )
                return

            logger.info("Starting processing - navigating to PROCESS page")
            self.wizard_ref.setCurrentId(self.wizard_ref.PAGE_PROCESS)

        except Exception as e:
            logger.exception("Failed to start processing")
            QMessageBox.critical(self, "Fel", f"Kunde inte starta bearbetning: {e}")
