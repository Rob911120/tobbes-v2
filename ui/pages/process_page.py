"""
Process Page for Tobbes v2 Wizard.

Matching articles with inventory charges.
"""

import logging

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QTableWidget, QTableWidgetItem, QComboBox,
        QMessageBox, QGroupBox
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from operations import (
    match_articles_with_charges,
    apply_charge_selection,
    get_matching_summary,
    get_unmatched_articles,
    get_articles_needing_manual_selection,
)
from domain.exceptions import DatabaseError
from ui.styles import get_charge_selector_style

logger = logging.getLogger(__name__)


class ProcessPage(QWizardPage):
    """
    Process page - Match articles with charges.

    Features:
    - Automatic matching of articles with inventory
    - Manual charge selection for articles with multiple options
    - Display matching statistics
    - Apply selections to database
    """

    def __init__(self, wizard):
        """Initialize process page."""
        super().__init__()

        self.wizard_ref = wizard
        self.match_results = []
        self.charge_selectors = {}  # article_number -> QComboBox

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Matchning av Artiklar och Charger")
        self.setSubTitle("Granska matchningar och välj charger för artiklar.")

        layout = QVBoxLayout()

        # Statistics section
        stats_group = QGroupBox("Statistik")
        stats_layout = QVBoxLayout()

        self.stats_label = QLabel("Laddar matchningsresultat...")
        stats_layout.addWidget(self.stats_label)

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Matching results table
        results_group = QGroupBox("Matchningsresultat")
        results_layout = QVBoxLayout()

        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Artikelnummer", "Benämning", "Antal", "Status", "Charge-val"
        ])
        results_layout.addWidget(self.results_table)

        results_group.setLayout(results_layout)
        layout.addWidget(results_group)

        # Apply button
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_apply = QPushButton("Applicera Val")
        self.btn_apply.clicked.connect(self._apply_selections)
        self.btn_apply.setEnabled(False)
        button_layout.addWidget(self.btn_apply)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def initializePage(self):
        """Initialize page when entering - run matching."""
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()

            # Get articles and inventory from database
            db = ctx.database
            articles = db.get_project_articles(project_id)
            inventory = db.get_inventory_items(project_id)

            if not articles:
                QMessageBox.warning(
                    self,
                    "Inga artiklar",
                    "Inga artiklar hittades. Gå tillbaka och importera nivålista."
                )
                return

            # Run matching
            logger.info(f"Running matching: {len(articles)} articles, {len(inventory)} inventory items")
            self.match_results = match_articles_with_charges(articles, inventory, auto_match_single=True)

            # Display results
            self._display_results()
            self._display_statistics()

            # Enable apply button if there are results
            self.btn_apply.setEnabled(len(self.match_results) > 0)

        except ValueError as e:
            QMessageBox.critical(self, "Fel", str(e))
        except Exception as e:
            logger.exception("Error during matching")
            QMessageBox.critical(self, "Fel", f"Matchning misslyckades: {e}")

    def _display_results(self):
        """Display matching results in table."""
        self.results_table.setRowCount(len(self.match_results))
        self.charge_selectors.clear()

        for row, result in enumerate(self.match_results):
            article = result.article

            # Article number
            self.results_table.setItem(row, 0, QTableWidgetItem(article.article_number))

            # Description
            self.results_table.setItem(row, 1, QTableWidgetItem(article.description))

            # Quantity
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{article.quantity:.1f}"))

            # Status
            if result.is_matched:
                if result.auto_matched:
                    status = "✓ Auto-matchad"
                else:
                    status = "✓ Vald"
            elif result.needs_manual_selection:
                status = "⚠ Välj charge"
            else:
                status = "✗ Ingen charge"

            status_item = QTableWidgetItem(status)
            if result.is_matched:
                status_item.setForeground(Qt.darkGreen)
            elif result.needs_manual_selection:
                status_item.setForeground(Qt.darkYellow)
            else:
                status_item.setForeground(Qt.red)

            self.results_table.setItem(row, 3, status_item)

            # Charge selector
            charge_combo = QComboBox()

            if not result.available_charges:
                # No charges - disabled, gray
                charge_combo.addItem("(Ingen charge tillgänglig)")
                charge_combo.setEnabled(False)
                charge_combo.setStyleSheet(get_charge_selector_style("gray"))

            elif len(result.available_charges) == 1:
                # Single charge - auto-selected, green
                charge_combo.addItem(result.available_charges[0])
                charge_combo.setCurrentIndex(0)
                charge_combo.setEnabled(False)
                charge_combo.setStyleSheet(get_charge_selector_style("green"))

            else:
                # Multiple charges - manual selection needed, yellow
                charge_combo.addItem("-- Välj charge --")
                for charge in result.available_charges:
                    charge_combo.addItem(charge)

                # Set current selection if exists
                if result.selected_charge:
                    index = charge_combo.findText(result.selected_charge)
                    if index >= 0:
                        charge_combo.setCurrentIndex(index)

                charge_combo.setStyleSheet(get_charge_selector_style("yellow"))
                charge_combo.currentIndexChanged.connect(
                    lambda idx, row=row: self._on_charge_selected(row, idx)
                )

            self.results_table.setCellWidget(row, 4, charge_combo)
            self.charge_selectors[article.article_number] = charge_combo

        self.results_table.resizeColumnsToContents()

    def _display_statistics(self):
        """Display matching statistics."""
        summary = get_matching_summary(self.match_results)

        stats_text = (
            f"Totalt artiklar: {summary['total_count']}\n"
            f"Auto-matchade: {summary['auto_matched_count']}\n"
            f"Kräver manuellt val: {summary['needs_manual_count']}\n"
            f"Inga charger: {summary['unmatched_count']}"
        )

        self.stats_label.setText(stats_text)

    def _on_charge_selected(self, row, combo_index):
        """Handle charge selection change."""
        if combo_index <= 0:  # "-- Välj charge --" selected
            return

        result = self.match_results[row]
        combo = self.charge_selectors[result.article.article_number]
        selected_charge = combo.currentText()

        # Update result
        result.selected_charge = selected_charge

        # Change combo style to green (now selected)
        combo.setStyleSheet(get_charge_selector_style("green"))

        logger.info(f"User selected charge for {result.article.article_number}: {selected_charge}")

        # Update statistics
        self._display_statistics()

    def _apply_selections(self):
        """Apply charge selections to database."""
        try:
            # Collect selections
            selections = {}
            for result in self.match_results:
                if result.selected_charge:
                    selections[result.article.article_number] = result.selected_charge

            if not selections:
                QMessageBox.information(
                    self,
                    "Inga val",
                    "Inga charger har valts."
                )
                return

            # Apply to database
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Use operation to apply selections
            success_count = apply_charge_selection(
                db=db,
                project_id=project_id,
                selections=selections
            )

            logger.info(f"Applied {success_count} charge selections")

            # Enable next button
            self.completeChanged.emit()

            QMessageBox.information(
                self,
                "Klart",
                f"Applicerade {success_count} charge-val till databasen."
            )

        except DatabaseError as e:
            logger.error(f"Database error during apply: {e}")
            QMessageBox.critical(
                self,
                "Databasfel",
                f"Kunde inte spara val:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error during apply")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

    def isComplete(self):
        """Page is complete when all required charges are selected."""
        if not self.match_results:
            return False

        # Check if all articles requiring manual selection have been handled
        needing_selection = get_articles_needing_manual_selection(self.match_results)

        return len(needing_selection) == 0
