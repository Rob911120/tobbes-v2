"""
Articles Tab for Tobbes v2 Main Window.

Article card-based verification and certificate management with SQLite persistence.
Based on ExportPage from wizard design.
"""

import logging
from typing import List, Dict, Any

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QGroupBox, QMessageBox, QCheckBox,
        QScrollArea
    )
    from PySide6.QtCore import Qt, QThread, Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    QThread = object
    Signal = object

from pathlib import Path
from config import AppContext
from operations import get_articles_for_project
from operations.article_ops import update_article_notes
from operations.report_ops import get_report_summary
from domain.exceptions import DatabaseError, ReportGenerationError, ValidationError
from services.pdf_service import create_pdf_service
from ui.widgets import ArticleCard
from ui.dialogs import ReportProgressDialog, CertTypesDialog
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


class ArticlesTab(QWidget):
    """
    Articles tab - Article card-based verification with SQLite persistence.

    Features:
    - Scrollable article cards with full editing
    - Real-time SQLite saves
    - Dynamic verification status
    - Filter to hide verified articles
    - PDF report generation
    """

    def __init__(self, context: AppContext, parent=None):
        """Initialize articles tab."""
        super().__init__(parent)

        self.context = context
        self.articles = []
        self.article_cards: List[ArticleCard] = []
        self.config = {}  # Will be populated with certificate types, etc.

        self._setup_ui()
        self.load_articles()  # Load articles immediately

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout(self)

        # Verification section (main area)
        self.verification_group = QGroupBox("Verifiera och exportera")
        verification_layout = QVBoxLayout()

        # Status label (replaces wizard subtitle)
        self.status_label = QLabel("Laddar artiklar...")
        self.status_label.setStyleSheet("font-weight: bold; color: #666;")
        verification_layout.addWidget(self.status_label)

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

        self.verification_group.setLayout(verification_layout)
        layout.addWidget(self.verification_group, stretch=1)  # Expand to fill

        # Bottom action bar (checkbox left, buttons right)
        action_bar = QHBoxLayout()

        # Filter checkbox (left-aligned)
        self.hide_verified_checkbox = QCheckBox("Dölj verifierade artiklar")
        self.hide_verified_checkbox.stateChanged.connect(self._filter_articles)
        action_bar.addWidget(self.hide_verified_checkbox)

        # Stretch to push buttons to the right
        action_bar.addStretch()

        # Certificate types button
        self.btn_cert_types = QPushButton("Redigera intygstyper")
        self.btn_cert_types.clicked.connect(self._edit_project_certificate_types)
        action_bar.addWidget(self.btn_cert_types)

        # Generate report button (watermark always enabled)
        self.btn_generate_report = QPushButton("Generera Rapport (PDF)")
        self.btn_generate_report.clicked.connect(self._generate_report)
        action_bar.addWidget(self.btn_generate_report)

        layout.addLayout(action_bar)

    def load_articles(self):
        """Load articles from database."""
        try:
            project_id = self.context.require_project()
            db = self.context.database

            logger.info(f"🔍 ArticlesTab.load_articles: Loading articles for project {project_id}")

            # Get articles with global data
            self.articles = get_articles_for_project(db, project_id)
            logger.info(f"  ✅ Loaded {len(self.articles)} articles from database")

            # Populate with certificates so CertificateManager can display them
            from operations.article_ops import populate_articles_with_certificates
            self.articles = populate_articles_with_certificates(db, self.articles, project_id)

            # DEBUG: Log certificate summary
            total_certs = sum(len(a.get('certificates', [])) for a in self.articles)
            articles_with_certs = sum(1 for a in self.articles if a.get('certificates'))
            logger.info(f"  ✅ After populate: {total_certs} total certificates across {articles_with_certs} articles")

            # Log sample article with certificates
            for article in self.articles:
                if article.get('certificates'):
                    logger.info(f"    Example: {article['article_number']} has {len(article['certificates'])} certificates")
                    break

            if not self.articles:
                self.status_label.setText("0/0 artiklar verifierade • [INFO] Inga artiklar ännu - importera filer i 'Imports'-fliken")
                logger.info("No articles found - user should import files")
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

            # Update status
            self._update_status()

        except ValueError as e:
            QMessageBox.critical(self, "Fel", str(e))
        except Exception as e:
            logger.exception("Error loading articles")
            QMessageBox.critical(self, "Fel", f"Kunde inte ladda artiklar: {e}")

    def refresh_articles(self):
        """Refresh articles from database (called after processing)."""
        logger.info("Refreshing articles from database...")
        self.load_articles()

    def _display_articles(self):
        """Display articles as cards in scroll area."""
        # Clear existing cards
        for card in self.article_cards:
            card.deleteLater()
        self.article_cards.clear()

        # Get database and project_id from context
        project_id = self.context.current_project_id
        db = self.context.database

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
            card.notes_changed.connect(self._on_notes_changed)

            # Add to layout (before stretch)
            self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
            self.article_cards.append(card)

        logger.info(f"Displayed {len(self.article_cards)} article cards")

    def _update_status(self):
        """Update status label with verification status."""
        total = len(self.articles)
        verified = sum(1 for a in self.articles if a.get('verified', False))

        if verified == total and total > 0:
            status = "[OK] Alla artiklar verifierade"
        elif verified == 0:
            status = "[VARNING] Inga verifieringar ännu"
        else:
            status = "[VARNING] Fler verifieringar behövs"

        self.status_label.setText(f"{verified}/{total} artiklar verifierade • {status}")

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

    def _edit_project_certificate_types(self):
        """Edit project-specific certificate types."""
        try:
            dialog = CertTypesDialog(
                database=self.context.database,
                project_id=self.context.current_project_id,
                parent=self
            )
            dialog.exec()
            logger.info("Project certificate types dialog closed")

            # Refresh articles to update available certificate types in cards
            if hasattr(self, 'refresh_articles'):
                self.refresh_articles()

        except Exception as e:
            logger.exception("Failed to open project certificate types dialog")
            QMessageBox.critical(self, "Fel", f"Kunde inte öppna dialog: {e}")

    def _on_verified_changed(self, verified: bool):
        """Handle when an article's verification status changes."""
        # Update status
        self._update_status()
        logger.info(f"Article verification changed: {verified}")

        # INSTANT hide if verified and filter is active
        if verified and self.hide_verified_checkbox.isChecked():
            # Find the card that was just verified and hide it
            sender = self.sender()  # This is the card that emitted the signal
            if sender and isinstance(sender, ArticleCard):
                sender.hide()
                logger.debug(f"Hid verified card for {sender.get_article_id()}")

    def _on_notes_changed(self, article_number: str, notes: str):
        """
        Handle when article notes change.

        Save notes GLOBALLY (shared across ALL projects).
        SQLite-optimized - no debouncing needed!

        Args:
            article_number: Article number
            notes: New notes text
        """
        try:
            db = self.context.database

            # Update global notes (shared across all projects)
            update_article_notes(
                db=db,
                article_number=article_number,
                notes=notes,
                changed_by="user"
            )

            logger.info(
                f"Saved global notes for {article_number} "
                f"(length: {len(notes)})"
            )

        except ValidationError as e:
            logger.error(f"Validation error saving notes: {e}")
            QMessageBox.warning(
                self,
                "Valideringsfel",
                f"Kunde inte spara anteckning:\n\n{e.message}"
            )

        except DatabaseError as e:
            logger.error(f"Database error saving notes: {e}")
            QMessageBox.warning(
                self,
                "Databasfel",
                f"Kunde inte spara anteckning:\n\n{e.message}"
            )

        except Exception as e:
            logger.exception("Unexpected error saving notes")
            QMessageBox.warning(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod vid sparning:\n\n{str(e)}"
            )

    def _on_save_required(self, article_card: ArticleCard):
        """
        Handle when article card requires save.

        Direct SQLite save - no debouncing needed!
        """
        try:
            project_id = self.context.require_project()
            db = self.context.database

            # Get updated article data
            article_data = article_card.get_article_data()
            article_number = article_data['article_number']

            # Save to database immediately
            # TODO: Implement update_project_article in database interface

            logger.info(f"Saved article data for {article_number} to SQLite")

            # Update status if verification changed
            self._update_status()

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
            project_id = self.context.require_project()
            db = self.context.database

            # Get project info
            project = db.get_project(project_id)
            if not project:
                QMessageBox.warning(self, "Fel", "Projektet kunde inte hittas.")
                return

            # Create automatic filename: Spårbarhetsrapport-{order_number}-{project_id}.pdf
            order_number = project.get('order_number', 'unknown')
            filename = f"Spårbarhetsrapport-{order_number}-{project_id}.pdf"

            # Get automatic output path: projects/{order_number}/reports/
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

            # Create PDF service (watermark always enabled)
            pdf_service = create_pdf_service(enable_watermark=True)

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

    def auto_save(self):
        """Auto-save any pending changes (called before navigation)."""
        # Cards auto-save to SQLite already, so nothing to do here
        logger.debug("Auto-save called (no-op - cards save automatically)")
