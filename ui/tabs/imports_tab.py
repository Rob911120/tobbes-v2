"""
Imports Tab for Tobbes v2 Main Window.

File import, processing, and updates with MANUAL processing trigger.
Merges functionality from ImportPage, ProcessPage, and UpdatePage.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QGroupBox, QMessageBox, QFileDialog,
        QListWidget, QListWidgetItem, QProgressBar,
        QTableWidget, QTableWidgetItem, QComboBox, QCheckBox
    )
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QColor
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object

from config import AppContext
from operations import (
    import_nivalista,
    import_lagerlogg,
    match_articles_with_charges,
    apply_charge_selection,
    get_matching_summary,
    compare_import_with_existing,
    get_articles_for_project,
)
from domain.exceptions import ImportValidationError, DatabaseError
from config.constants import EXCEL_EXTENSIONS

logger = logging.getLogger(__name__)


class ImportsTab(QWidget):
    """
    Imports tab - File import, processing, and updates.

    Key Features:
    - File selection (NO automatic processing!)
    - Manual processing trigger: "Bearbeta filer nu" button
    - Show matching results
    - Manual charge selection for multiple matches
    - Update functionality (import new versions)

    Signals:
    - processing_complete: Emitted when processing is done
    """

    processing_complete = Signal()

    def __init__(self, context: AppContext, parent=None):
        """Initialize imports tab."""
        super().__init__(parent)

        self.context = context
        self.selected_files = []  # List of {'path': Path, 'type': str, 'name': str}
        self.match_results = []
        self.diff_result = None  # Diff between existing and new data
        self.charge_selectors = {}  # article_number -> QComboBox

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # ========== SECTION 1: FILE SELECTION ==========
        files_group = QGroupBox("1. Välj filer att importera")
        files_layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "<b>Välj filer att importera:</b><br>"
            "• Nivålista - Uppdaterar struktur (nivåer, quantity, nya/borttagna artiklar)<br>"
            "• Lagerlogg - Uppdaterar charges och batch-nummer<br>"
            "• Båda - Fullständig import/uppdatering<br><br>"
            "<i>Du kan importera en fil åt gången eller båda samtidigt.</i>"
        )
        instructions.setWordWrap(True)
        files_layout.addWidget(instructions)

        # File display area
        self.file_list = QListWidget()
        self.file_list.setMinimumHeight(150)
        self.file_list.setSelectionMode(QListWidget.NoSelection)
        files_layout.addWidget(self.file_list)

        # Buttons
        buttons_layout = QHBoxLayout()

        self.btn_browse = QPushButton("Bläddra efter filer...")
        self.btn_browse.clicked.connect(self._browse_files)
        buttons_layout.addWidget(self.btn_browse)

        self.btn_clear = QPushButton("Rensa alla")
        self.btn_clear.clicked.connect(self._clear_files)
        self.btn_clear.setEnabled(False)
        buttons_layout.addWidget(self.btn_clear)

        buttons_layout.addStretch()
        files_layout.addLayout(buttons_layout)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # ========== SECTION 2: PROCESSING (MANUAL TRIGGER!) ==========
        process_group = QGroupBox("2. Bearbeta filer")
        process_layout = QVBoxLayout()

        process_info = QLabel(
            "<i>Bearbetning visar en diff-vy av ändringar. "
            "Du kan välja vilka ändringar som ska appliceras.</i>"
        )
        process_info.setWordWrap(True)
        process_layout.addWidget(process_info)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        process_layout.addWidget(self.progress_bar)

        # Process button
        process_button_layout = QHBoxLayout()
        process_button_layout.addStretch()

        self.btn_process = QPushButton("🔄 Bearbeta filer nu")
        self.btn_process.clicked.connect(self._process_files)
        self.btn_process.setEnabled(False)
        self.btn_process.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        process_button_layout.addWidget(self.btn_process)

        process_layout.addLayout(process_button_layout)

        process_group.setLayout(process_layout)
        layout.addWidget(process_group)

        # ========== SECTION 3: DIFF & MATCHING RESULTS ==========
        results_group = QGroupBox("3. Ändringar & Matchning")
        results_layout = QVBoxLayout()

        self.results_status = QLabel("Inga resultat ännu - välj filer och bearbeta dem.")
        self.results_status.setStyleSheet("color: #666; font-style: italic;")
        results_layout.addWidget(self.results_status)

        # Results table (unified diff view)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Status", "Artikelnummer", "Benämning", "Tidigare → Nytt", "Verifierad", "Välj"
        ])
        self.results_table.setVisible(False)
        results_layout.addWidget(self.results_table)

        # Apply button
        apply_layout = QHBoxLayout()
        apply_layout.addStretch()

        self.btn_apply = QPushButton("✓ Applicera valda ändringar")
        self.btn_apply.clicked.connect(self._apply_selections)
        self.btn_apply.setEnabled(False)
        self.btn_apply.setVisible(False)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        apply_layout.addWidget(self.btn_apply)

        results_layout.addLayout(apply_layout)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # ========== SECTION 4: UPDATE (TODO - FUTURE) ==========
        # update_group = QGroupBox("4. Uppdatera projekt")
        # TODO: Add update functionality

        layout.addStretch()

    def _browse_files(self):
        """Open file dialog to select files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Välj Excel-filer",
            "",
            "Excel-filer (*.xlsx *.xls);;Alla filer (*.*)"
        )

        if not file_paths:
            return

        for file_path in file_paths:
            path = Path(file_path)

            # Detect file type (simple detection)
            file_name = path.name.lower()
            if 'nivå' in file_name or 'bom' in file_name:
                file_type = 'Nivålista'
            elif 'lager' in file_name or 'inventory' in file_name:
                file_type = 'Lagerlogg'
            else:
                file_type = 'Okänd typ'

            # Add to selected files
            self.selected_files.append({
                'path': path,
                'type': file_type,
                'name': path.name
            })

        # Update UI
        self._update_file_list()
        self._update_buttons()

        logger.info(f"Selected {len(file_paths)} files")

    def _update_file_list(self):
        """Update file list display."""
        self.file_list.clear()

        for file_info in self.selected_files:
            item_text = f"📄 {file_info['name']} ({file_info['type']})"
            item = QListWidgetItem(item_text)

            # Color-code by type
            if file_info['type'] == 'Nivålista':
                item.setForeground(Qt.blue)
            elif file_info['type'] == 'Lagerlogg':
                item.setForeground(Qt.darkGreen)
            else:
                item.setForeground(Qt.gray)

            self.file_list.addItem(item)

    def _update_buttons(self):
        """Update button states based on selected files."""
        has_files = len(self.selected_files) > 0
        self.btn_clear.setEnabled(has_files)

        # Enable process button if we have AT LEAST ONE file
        has_nivalista = any(f['type'] == 'Nivålista' for f in self.selected_files)
        has_lagerlogg = any(f['type'] == 'Lagerlogg' for f in self.selected_files)
        self.btn_process.setEnabled(has_nivalista or has_lagerlogg)

        # Update button text dynamically
        if has_nivalista and has_lagerlogg:
            self.btn_process.setText("🔄 Bearbeta filer nu")
        elif has_nivalista:
            self.btn_process.setText("🔄 Uppdatera struktur")
        elif has_lagerlogg:
            self.btn_process.setText("🔄 Uppdatera lager")
        else:
            self.btn_process.setText("🔄 Bearbeta filer nu")

    def _clear_files(self):
        """Clear all selected files."""
        self.selected_files.clear()
        self._update_file_list()
        self._update_buttons()

    def _process_files(self):
        """
        Process selected files (MANUAL TRIGGER!).

        This is the key difference from wizard - user explicitly triggers processing.
        """
        try:
            self.btn_process.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            project_id = self.context.require_project()
            db = self.context.database

            # Find nivalista and lagerlogg files
            nivalista_file = next(
                (f for f in self.selected_files if f['type'] == 'Nivålista'),
                None
            )
            lagerlogg_file = next(
                (f for f in self.selected_files if f['type'] == 'Lagerlogg'),
                None
            )

            # Get existing data from DB
            logger.info("Getting existing project data...")
            self.progress_bar.setValue(10)
            existing_articles = get_articles_for_project(db, project_id)
            existing_inventory = db.get_inventory_items(project_id)

            # SCENARIO A: Only nivålista - update structure
            if nivalista_file and not lagerlogg_file:
                logger.info("Partial import: Nivålista only (updating structure)")
                self.progress_bar.setValue(20)
                new_articles = import_nivalista(nivalista_file['path'])
                self.progress_bar.setValue(60)

                # Use existing inventory for matching
                self.diff_result = compare_import_with_existing(
                    existing_articles=existing_articles,
                    new_articles=new_articles,
                    new_inventory=existing_inventory,  # ← Use existing!
                )
                self.progress_bar.setValue(90)
                logger.info(f"Structure update: {len(new_articles)} articles")

            # SCENARIO B: Only lagerlogg - update charges/batches
            elif lagerlogg_file and not nivalista_file:
                logger.info("Partial import: Lagerlogg only (updating charges/batches)")
                self.progress_bar.setValue(20)
                new_inventory = import_lagerlogg(lagerlogg_file['path'])
                self.progress_bar.setValue(60)

                # Use existing articles structure
                # Convert existing to new_articles format for diff
                new_articles_from_existing = [
                    {
                        'article_number': a.get('article_number'),
                        'description': a.get('description', ''),
                        'quantity': a.get('quantity', 0.0),
                        'level': a.get('level', ''),
                    }
                    for a in existing_articles
                ]

                self.diff_result = compare_import_with_existing(
                    existing_articles=existing_articles,
                    new_articles=new_articles_from_existing,  # ← Same structure!
                    new_inventory=new_inventory,  # ← New inventory!
                )
                self.progress_bar.setValue(90)
                logger.info(f"Lager update: {len(new_inventory)} inventory items")

            # SCENARIO C: Both files - full import
            else:
                logger.info("Full import: Both nivålista and lagerlogg")
                self.progress_bar.setValue(20)
                new_articles = import_nivalista(nivalista_file['path'])
                self.progress_bar.setValue(40)
                new_inventory = import_lagerlogg(lagerlogg_file['path'])
                self.progress_bar.setValue(60)

                self.diff_result = compare_import_with_existing(
                    existing_articles=existing_articles,
                    new_articles=new_articles,
                    new_inventory=new_inventory,
                )
                self.progress_bar.setValue(90)
                logger.info(
                    f"Full import: {len(new_articles)} articles, "
                    f"{len(new_inventory)} inventory items"
                )

            # Display unified diff results (100%)
            self._display_diff_results()
            self.progress_bar.setValue(100)

        except ImportValidationError as e:
            logger.error(f"Import validation failed: {e}")
            QMessageBox.critical(
                self,
                "Importfel",
                f"{e.message}\n\nDetaljer: {e.details}"
            )

        except DatabaseError as e:
            logger.error(f"Database error: {e}")
            QMessageBox.critical(
                self,
                "Databasfel",
                f"{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error during processing")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

        finally:
            self.progress_bar.setVisible(False)
            self.btn_process.setEnabled(True)

    def _display_diff_results(self):
        """Display unified diff results (new + updated + removed articles)."""
        if not self.diff_result:
            self.results_status.setText("Inga resultat att visa.")
            return

        # Calculate summary
        new_count = len(self.diff_result['new'])
        updated_count = len(self.diff_result['updated'])
        removed_count = len(self.diff_result['removed'])
        unchanged_count = len(self.diff_result['unchanged'])
        total = new_count + updated_count + removed_count + unchanged_count

        # Update status with color-coded summary
        self.results_status.setText(
            f"<span style='color: #28a745;'>🆕 {new_count} nya</span>, "
            f"<span style='color: #ffc107;'>📝 {updated_count} uppdaterade</span>, "
            f"<span style='color: #dc3545;'>❌ {removed_count} borttagna</span>, "
            f"<span style='color: #6c757d;'>{unchanged_count} oförändrade</span>"
        )

        # Show table
        self.results_table.setVisible(True)

        # Calculate row count (only show new, updated, removed - skip unchanged)
        display_rows = new_count + updated_count + removed_count
        self.results_table.setRowCount(display_rows)

        # Clear charge selectors
        self.charge_selectors.clear()

        row = 0

        # NEW articles (green rows)
        for article in self.diff_result['new']:
            self._add_diff_row(
                row, article, "🆕 NY", "#e8f5e9", article.get('article_number', ''),
                article.get('description', ''), "Ny artikel", False, True
            )
            row += 1

        # UPDATED articles (yellow if can_update, gray if verified)
        for update_info in self.diff_result['updated']:
            article = update_info['article']
            changes = update_info['changes']
            is_verified = update_info['is_verified']
            can_update = update_info['can_update']

            # Build change summary
            change_text = ", ".join([
                f"{field}: {ch['old']} → {ch['new']}"
                for field, ch in changes.items()
            ])

            bg_color = "#d3d3d3" if is_verified else "#fff3cd"  # Gray if verified, yellow if not
            status_icon = "🔒 LÅST" if is_verified else "📝 UPPDATERAD"

            self._add_diff_row(
                row, article, status_icon, bg_color, article.get('article_number', ''),
                article.get('description', ''), change_text, is_verified, can_update
            )
            row += 1

        # REMOVED articles (red rows)
        for article in self.diff_result['removed']:
            self._add_diff_row(
                row, article, "❌ BORTTAGEN", "#f8d7da", article.get('article_number', ''),
                article.get('description', ''), "Finns ej i ny fil", False, False
            )
            row += 1

        # Enable apply button
        self.btn_apply.setVisible(True)
        self.btn_apply.setEnabled(True)

        logger.info(f"Displayed diff: {new_count} new, {updated_count} updated, {removed_count} removed")

    def _add_diff_row(self, row: int, article: Dict, status: str, bg_color: str,
                      article_num: str, description: str, changes: str,
                      is_verified: bool, can_update: bool):
        """Add a single row to diff table with color coding."""
        color = QColor(bg_color)

        # Column 0: Status icon
        status_item = QTableWidgetItem(status)
        status_item.setBackground(color)
        self.results_table.setItem(row, 0, status_item)

        # Column 1: Article number
        article_item = QTableWidgetItem(article_num)
        article_item.setBackground(color)
        self.results_table.setItem(row, 1, article_item)

        # Column 2: Description
        desc_item = QTableWidgetItem(description)
        desc_item.setBackground(color)
        self.results_table.setItem(row, 2, desc_item)

        # Column 3: Changes (Previous → New)
        changes_item = QTableWidgetItem(changes)
        changes_item.setBackground(color)
        self.results_table.setItem(row, 3, changes_item)

        # Column 4: Verified status
        verified_text = "Ja" if is_verified else "Nej"
        verified_item = QTableWidgetItem(verified_text)
        verified_item.setBackground(color)
        self.results_table.setItem(row, 4, verified_item)

        # Column 5: Apply checkbox (disabled if verified)
        checkbox = QCheckBox()
        checkbox.setChecked(can_update)  # Auto-check if can update
        checkbox.setEnabled(can_update)  # Disable if verified
        self.results_table.setCellWidget(row, 5, checkbox)

    def _apply_selections(self):
        """Apply selected diff changes to database."""
        try:
            project_id = self.context.require_project()
            db = self.context.database

            if not self.diff_result:
                logger.warning("No diff result to apply")
                return

            # Determine import mode
            nivalista_file = next(
                (f for f in self.selected_files if f['type'] == 'Nivålista'),
                None
            )
            lagerlogg_file = next(
                (f for f in self.selected_files if f['type'] == 'Lagerlogg'),
                None
            )

            # Step 1: Apply nivålista changes FIRST (so articles exist in DB)
            # NOTE: Articles already imported and stored in self.diff_result during _process_files()
            applied_count = 0
            skipped_verified = 0

            if nivalista_file:
                row = 0
                # Process NEW articles
                for article in self.diff_result['new']:
                    checkbox = self.results_table.cellWidget(row, 5)
                    if checkbox and checkbox.isChecked():
                        # Add new article
                        db.save_project_articles(project_id, [article])
                        applied_count += 1
                    row += 1

                # Process UPDATED articles
                for update_info in self.diff_result['updated']:
                    checkbox = self.results_table.cellWidget(row, 5)
                    if checkbox and checkbox.isChecked() and update_info['can_update']:
                        # Update article (UPSERT will handle it)
                        db.save_project_articles(project_id, [update_info['article']])
                        applied_count += 1
                    elif update_info['is_verified']:
                        skipped_verified += 1
                    row += 1

                # Process REMOVED articles (skip for now - let user manually delete)
                # TODO: Add delete confirmation dialog

            # Step 2: Handle lagerlogg AFTER nivålista (so sync_charges can copy to existing articles)
            if lagerlogg_file:
                logger.info("Deleting old inventory items...")
                db.delete_inventory_items(project_id)

                new_inventory = import_lagerlogg(lagerlogg_file['path'])
                logger.info(f"Saving {len(new_inventory)} inventory items...")
                db.save_inventory_items(project_id, new_inventory)
                logger.info("Lagerlogg synced - charges/batches copied to project_articles")

            # Emit signal to refresh articles tab
            self.processing_complete.emit()

            # Build success message based on what was imported
            message_parts = []
            if nivalista_file:
                message_parts.append(f"Applicerade {applied_count} artikeländringar")
                if skipped_verified > 0:
                    message_parts.append(f"Hoppade över {skipped_verified} verifierade")
            if lagerlogg_file:
                message_parts.append("Uppdaterade lager (charges/batches)")

            QMessageBox.information(
                self,
                "Import klar",
                "\n".join(message_parts) if message_parts else "Inga ändringar applicerades"
            )

            logger.info(f"Applied {applied_count} changes, skipped {skipped_verified} verified")

        except Exception as e:
            logger.exception("Failed to apply selections")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte applicera ändringar:\n\n{str(e)}"
            )
