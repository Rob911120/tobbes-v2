"""
Export Page for Tobbes v2 Wizard.

Article card-based verification and certificate management with SQLite persistence.
Based on v1's verify_export_page design.
"""

import logging
from typing import List, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QGroupBox, QMessageBox, QCheckBox,
        QScrollArea, QWidget
    )
    from PySide6.QtCore import Qt, QThread, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object
    QThread = object
    Signal = object

from pathlib import Path
from operations import get_articles_for_project
from operations.report_ops import get_report_summary
from domain.exceptions import DatabaseError, ReportGenerationError
from services.pdf_service import create_pdf_service
from ui.widgets import ArticleCard
from ui.dialogs import ReportProgressDialog
from config.paths import get_project_reports_path

logger = logging.getLogger(__name__)


class ReportGenerationWorker(QThread):
    """
    Worker thread for PDF report generation.

    Runs report generation in background to keep UI responsive.
    """

    # Signals
    progress = Signal(int, str)  # (progress_value, status_message)
    finished = Signal(Path)  # (report_path)
    error = Signal(str)  # (error_message)

    def __init__(
        self,
        pdf_service,
        project,
        articles,
        certificates,
        output_path,
        base_dir,
    ):
        """Initialize worker thread."""
        super().__init__()

        self.pdf_service = pdf_service
        self.project = project
        self.articles = articles
        self.certificates = certificates
        self.output_path = output_path
        self.base_dir = base_dir

    def run(self):
        """Run report generation."""
        try:
            from operations.report_ops import generate_report_with_toc

            # Generate report with progress callback
            def progress_callback(value):
                # Map progress to status messages
                status_messages = {
                    5: "Skapar materialspecifikation...",
                    20: "Konverterar till PDF...",
                    30: "Grupperar certifikat...",
                    50: "Slår samman dokument...",
                    60: "Skapar sammanslagen PDF...",
                    70: "Extraherar metadata...",
                    80: "Bygger innehållsförteckning...",
                    90: "Lägger till sidnummer...",
                    100: "Klar!"
                }

                status = status_messages.get(value, f"Bearbetar... {value}%")
                self.progress.emit(value, status)

            pdf_path = generate_report_with_toc(
                pdf_service=self.pdf_service,
                project=self.project,
                articles=self.articles,
                certificates=self.certificates,
                output_path=self.output_path,
                base_dir=self.base_dir,
                progress_callback=progress_callback,
            )

            self.finished.emit(pdf_path)

        except Exception as e:
            logger.exception("Report generation failed in worker thread")
            self.error.emit(str(e))


class ExportPage(QWizardPage):
    """
    Export page - Article card-based verification with SQLite persistence.

    Features:
    - Scrollable article cards with full editing
    - Real-time SQLite saves (no debouncing)
    - Dynamic verification status in subtitle
    - Filter to hide verified articles
    - PDF report generation
    """

    def __init__(self, wizard):
        """Initialize export page."""
        super().__init__()

        self.wizard_ref = wizard
        self.articles = []
        self.article_cards: List[ArticleCard] = []
        self.config = {}  # Will be populated with certificate types, etc.

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Verifiera och exportera")
        # Initial subtitle - will be updated dynamically
        self.setSubTitle("Laddar artiklar...")

        layout = QVBoxLayout()

        # Verification section (main area)
        self.verification_group = QGroupBox("Artiklar från nivålista")
        verification_layout = QVBoxLayout()

        # Scroll area for article cards
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # Container for article cards
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()  # Push cards to top

        self.scroll_area.setWidget(self.cards_container)
        verification_layout.addWidget(self.scroll_area)

        # Controls below scroll area
        controls_layout = QHBoxLayout()

        # Filter checkbox
        self.hide_verified_checkbox = QCheckBox("Dölj verifierade artiklar")
        self.hide_verified_checkbox.stateChanged.connect(self._filter_articles)
        controls_layout.addWidget(self.hide_verified_checkbox)

        controls_layout.addStretch()
        verification_layout.addLayout(controls_layout)

        self.verification_group.setLayout(verification_layout)
        layout.addWidget(self.verification_group, stretch=1)  # Expand to fill

        # Report generation section (compact, at bottom)
        report_group = QGroupBox("Rapportgenerering")
        report_layout = QVBoxLayout()

        self.watermark_checkbox = QCheckBox("Inkludera FA-TEC watermark")
        self.watermark_checkbox.setChecked(True)
        report_layout.addWidget(self.watermark_checkbox)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.btn_generate_report = QPushButton("Generera Rapport (PDF)")
        self.btn_generate_report.clicked.connect(self._generate_report)
        self.btn_generate_report.setEnabled(True)
        button_layout.addWidget(self.btn_generate_report)

        report_layout.addLayout(button_layout)
        report_group.setLayout(report_layout)
        layout.addWidget(report_group, stretch=0)  # Fixed size

        self.setLayout(layout)

    def initializePage(self):
        """Initialize page when entering."""
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Get articles with global data
            self.articles = get_articles_for_project(db, project_id)

            # Populate with certificates so CertificateManager can display them
            from operations.article_ops import populate_articles_with_certificates
            self.articles = populate_articles_with_certificates(db, self.articles, project_id)

            if not self.articles:
                QMessageBox.warning(
                    self,
                    "Inga artiklar",
                    "Inga artiklar hittades i projektet."
                )
                return

            # Load config (certificate types, etc.)
            # TODO: Load from database or config file
            self.config = {
                'certificates': {
                    'types': ['Material Specification', 'Materialintyg', 'Svetslogg', 'Övriga dokument']
                }
            }

            # Display articles as cards
            self._display_articles()

            # Update subtitle with verification status
            self._update_subtitle()

        except ValueError as e:
            QMessageBox.critical(self, "Fel", str(e))
        except Exception as e:
            logger.exception("Error loading articles")
            QMessageBox.critical(self, "Fel", f"Kunde inte ladda artiklar: {e}")

    def _display_articles(self):
        """Display articles as cards in scroll area."""
        # Clear existing cards
        for card in self.article_cards:
            card.deleteLater()
        self.article_cards.clear()

        # Get database and project_id from context
        ctx = self.wizard_ref.context
        project_id = ctx.current_project_id
        db = ctx.database

        # Create article card for each article
        for article in self.articles:
            card = ArticleCard(
                article_data=article,
                config=self.config,
                db=db,
                project_id=project_id,
                parent=self
            )

            # Connect signals for live updates
            card.verified_changed.connect(self._on_verified_changed)
            card.save_required.connect(lambda c=card: self._on_save_required(c))

            # Add to layout (before stretch)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self.article_cards.append(card)

        logger.info(f"Displayed {len(self.article_cards)} article cards")

    def _update_subtitle(self):
        """Update subtitle with verification status."""
        total = len(self.articles)
        verified = sum(1 for a in self.articles if a.get('verified', False))

        if verified == total:
            status = "[OK] Alla artiklar verifierade"
            self.setSubTitle(f"{verified}/{total} artiklar verifierade • {status}")
        elif verified == 0:
            status = "[VARNING] Inga verifieringar ännu"
            self.setSubTitle(f"{verified}/{total} artiklar verifierade • {status}")
        else:
            status = "[VARNING] Fler verifieringar behövs"
            self.setSubTitle(f"{verified}/{total} artiklar verifierade • {status}")

    def _filter_articles(self, state):
        """Filter articles based on hide verified checkbox."""
        hide_verified = self.hide_verified_checkbox.isChecked()

        for card in self.article_cards:
            article_data = card.get_article_data()
            is_verified = article_data.get('verified', False)

            if hide_verified and is_verified:
                card.hide()
            else:
                card.show()

    def _on_verified_changed(self, verified: bool):
        """Handle when an article's verification status changes."""
        # Update subtitle
        self._update_subtitle()

        logger.info(f"Article verification changed: {verified}")

    def _on_save_required(self, article_card: ArticleCard):
        """
        Handle when article card requires save.

        Direct SQLite save - no debouncing needed!
        """
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Get updated article data
            article_data = article_card.get_article_data()
            article_number = article_data['article_number']

            # Save to database immediately
            success = db.update_project_article(
                project_id=project_id,
                article_number=article_number,
                article_data=article_data
            )

            if success:
                logger.info(f"Saved article data for {article_number} to SQLite")
            else:
                logger.warning(f"Failed to save article {article_number}")

            # Update subtitle if verification changed
            self._update_subtitle()

        except DatabaseError as e:
            logger.error(f"Database error saving article: {e}")
            QMessageBox.warning(
                self,
                "Sparningsfel",
                f"Kunde inte spara artikel:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error saving article")
            QMessageBox.warning(
                self,
                "Sparningsfel",
                f"Ett oväntat fel uppstod vid sparning:\n\n{str(e)}"
            )

    def _generate_report(self):
        """Generate PDF report with TOC using progress dialog."""
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Get project info
            project = db.get_project(project_id)
            if not project:
                QMessageBox.warning(self, "Fel", "Projektet kunde inte hittas.")
                return

            # Create automatic filename: Spårbarhetsrapport-{order_number}-{project_id}.pdf
            order_number = project.get('order_number', 'unknown')
            filename = f"Spårbarhetsrapport-{order_number}-{project_id}.pdf"

            # Get automatic output path: projects/{order_number}/rapports/
            reports_path = get_project_reports_path(order_number)
            output_path = reports_path / filename

            logger.info(f"Generating report to: {output_path}")

            # Get fresh article data from cards
            articles_data = [card.get_article_data() for card in self.article_cards]

            # Get certificates
            certificates = db.get_certificates_for_project(project_id)

            # Get base_dir for certificates (projects/{order_number}/certificates)
            from config.paths import get_project_certificates_path
            base_dir = get_project_certificates_path(order_number)

            # Create PDF service
            pdf_service = create_pdf_service(enable_watermark=self.watermark_checkbox.isChecked())

            # Create progress dialog
            progress_dialog = ReportProgressDialog(self)

            # Create worker thread
            self.worker = ReportGenerationWorker(
                pdf_service=pdf_service,
                project=project,
                articles=articles_data,
                certificates=certificates,
                output_path=output_path,
                base_dir=base_dir,
            )

            # Connect signals
            self.worker.progress.connect(progress_dialog.update_progress)
            self.worker.finished.connect(lambda path: self._on_report_finished(progress_dialog, path))
            self.worker.error.connect(lambda err: self._on_report_error(progress_dialog, err))

            # Start worker and show dialog
            self.worker.start()
            progress_dialog.exec()

        except Exception as e:
            logger.exception("Unexpected error generating report")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

    def _on_report_finished(self, dialog: ReportProgressDialog, report_path: Path):
        """Handle successful report generation."""
        logger.info(f"Report generated successfully: {report_path}")
        dialog.set_complete(report_path)

    def _on_report_error(self, dialog: ReportProgressDialog, error_message: str):
        """Handle report generation error."""
        logger.error(f"Report generation failed: {error_message}")
        dialog.set_error(error_message)

    def export_report(self):
        """
        Export report (called by wizard button).

        Wrapper around _generate_report() for consistency.
        """
        logger.info("export_report() triggered from wizard button")
        self._generate_report()

    def isComplete(self):
        """Page is complete when articles are loaded."""
        return len(self.articles) > 0
