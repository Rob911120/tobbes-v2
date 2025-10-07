"""
Export Page for Tobbes v2 Wizard.

Article verification, certificate management, and report generation.
"""

import logging

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QPushButton,
        QLabel, QTableWidget, QTableWidgetItem, QGroupBox,
        QMessageBox, QCheckBox, QFileDialog
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from pathlib import Path
from operations import get_articles_for_project
from operations.report_ops import (
    generate_material_specification_html,
    generate_pdf_report,
    get_report_summary,
)
from domain.exceptions import DatabaseError, ReportGenerationError
from services import FileService
from services.pdf_service import create_pdf_service
from ui.dialogs.certificate_upload_dialog import CertificateUploadDialog

logger = logging.getLogger(__name__)


class ExportPage(QWizardPage):
    """
    Export page - Verify articles, manage certificates, generate report.

    Features (basic implementation):
    - Display all project articles with charges
    - Show verification status
    - Placeholder for certificate management (TODO: Widget)
    - Placeholder for report generation (TODO: report_ops)
    """

    def __init__(self, wizard):
        """Initialize export page."""
        super().__init__()

        self.wizard_ref = wizard
        self.articles = []

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        self.setTitle("Export och Rapport")
        self.setSubTitle("Granska artiklar, hantera certifikat och generera rapport.")

        layout = QVBoxLayout()

        # Articles section
        articles_group = QGroupBox("Artiklar i Projekt")
        articles_layout = QVBoxLayout()

        self.articles_table = QTableWidget()
        self.articles_table.setColumnCount(7)
        self.articles_table.setHorizontalHeaderLabels([
            "Artikelnummer", "Benämning", "Antal", "Nivå", "Charge", "Certifikat", "Åtgärd"
        ])
        articles_layout.addWidget(self.articles_table)

        articles_group.setLayout(articles_layout)
        layout.addWidget(articles_group)

        # Certificate section (placeholder)
        cert_group = QGroupBox("Certifikathantering")
        cert_layout = QVBoxLayout()

        cert_label = QLabel(
            "Certifikathantering kommer i nästa version.\n"
            "Funktioner som kommer:\n"
            "• Ladda upp certifikat per artikel\n"
            "• Auto-detektering av certifikattyp\n"
            "• Visa certifikat-status"
        )
        cert_label.setProperty("class", "subheader")
        cert_layout.addWidget(cert_label)

        cert_group.setLayout(cert_layout)
        layout.addWidget(cert_group)

        # Report section (placeholder)
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
        layout.addWidget(report_group)

        layout.addStretch()
        self.setLayout(layout)

    def initializePage(self):
        """Initialize page when entering."""
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()

            # Get articles with global data (includes notes, description)
            db = ctx.database
            self.articles = get_articles_for_project(db, project_id)

            if not self.articles:
                QMessageBox.warning(
                    self,
                    "Inga artiklar",
                    "Inga artiklar hittades i projektet."
                )
                return

            # Display articles
            self._display_articles()

        except ValueError as e:
            QMessageBox.critical(self, "Fel", str(e))
        except Exception as e:
            logger.exception("Error loading articles")
            QMessageBox.critical(self, "Fel", f"Kunde inte ladda artiklar: {e}")

    def _display_articles(self):
        """Display articles in table."""
        self.articles_table.setRowCount(len(self.articles))

        for row, article in enumerate(self.articles):
            # Article number
            self.articles_table.setItem(row, 0, QTableWidgetItem(article["article_number"]))

            # Description (global)
            desc = article.get("global_description", article.get("description", ""))
            self.articles_table.setItem(row, 1, QTableWidgetItem(desc))

            # Quantity
            qty = article.get("quantity", 0.0)
            self.articles_table.setItem(row, 2, QTableWidgetItem(f"{qty:.1f}"))

            # Level
            level = article.get("level", "")
            self.articles_table.setItem(row, 3, QTableWidgetItem(level))

            # Charge
            charge = article.get("charge_number", "")
            charge_item = QTableWidgetItem(charge if charge else "(Ingen charge)")
            if not charge:
                charge_item.setForeground(Qt.red)
            self.articles_table.setItem(row, 4, charge_item)

            # Certificates - Get actual count from database
            try:
                ctx = self.wizard_ref.context
                project_id = ctx.require_project()
                db = ctx.database
                certs = db.get_certificates_for_article(project_id, article["article_number"])
                cert_count = len(certs)
            except:
                cert_count = 0

            cert_text = f"{cert_count} st" if cert_count > 0 else "(Inga)"
            cert_item = QTableWidgetItem(cert_text)
            if cert_count == 0:
                cert_item.setForeground(Qt.darkYellow)
            else:
                cert_item.setForeground(Qt.darkGreen)
            self.articles_table.setItem(row, 5, cert_item)

            # Upload button
            upload_btn = QPushButton("Ladda upp")
            upload_btn.clicked.connect(
                lambda checked, r=row: self._upload_certificate(r)
            )
            self.articles_table.setCellWidget(row, 6, upload_btn)

        self.articles_table.resizeColumnsToContents()

    def _upload_certificate(self, row: int):
        """Upload certificate for article at given row."""
        try:
            article = self.articles[row]
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Create file service
            file_service = FileService(ctx.settings.certificates_dir)

            # Open upload dialog
            dialog = CertificateUploadDialog(
                article_number=article["article_number"],
                article_description=article.get("global_description", article.get("description", "")),
                project_id=project_id,
                database=db,
                file_service=file_service,
                parent=self
            )

            if dialog.exec() == CertificateUploadDialog.Accepted:
                # Refresh the row to show updated certificate count
                self._refresh_article_row(row)

                QMessageBox.information(
                    self,
                    "Certifikat laddat upp",
                    f"Certifikatet har laddats upp för {article['article_number']}."
                )

        except Exception as e:
            logger.exception("Error uploading certificate")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte ladda upp certifikat:\n\n{str(e)}"
            )

    def _refresh_article_row(self, row: int):
        """Refresh certificate count for article at given row."""
        try:
            article = self.articles[row]
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            certs = db.get_certificates_for_article(project_id, article["article_number"])
            cert_count = len(certs)

            cert_text = f"{cert_count} st" if cert_count > 0 else "(Inga)"
            cert_item = QTableWidgetItem(cert_text)
            if cert_count == 0:
                cert_item.setForeground(Qt.darkYellow)
            else:
                cert_item.setForeground(Qt.darkGreen)
            self.articles_table.setItem(row, 5, cert_item)

        except Exception as e:
            logger.exception("Error refreshing article row")

    def _generate_report(self):
        """Generate PDF report."""
        try:
            ctx = self.wizard_ref.context
            project_id = ctx.require_project()
            db = ctx.database

            # Get project info
            project = db.get_project(project_id)
            if not project:
                QMessageBox.warning(self, "Fel", "Projektet kunde inte hittas.")
                return

            # Ask user where to save PDF
            default_filename = f"{project.project_name}_materialspecifikation.pdf"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Spara PDF-rapport",
                default_filename,
                "PDF-filer (*.pdf)"
            )

            if not file_path:
                return  # User cancelled

            output_path = Path(file_path)

            # Get certificates
            certificates = db.get_certificates_for_project(project_id)

            # Generate HTML
            logger.info("Generating HTML material specification...")
            html_content = generate_material_specification_html(
                project=project,
                articles=self.articles,
                certificates=certificates,
                include_watermark=self.watermark_checkbox.isChecked(),
            )

            # Generate PDF
            logger.info("Converting HTML to PDF...")
            pdf_service = create_pdf_service(enable_watermark=self.watermark_checkbox.isChecked())

            pdf_path = generate_pdf_report(
                pdf_service=pdf_service,
                html_content=html_content,
                output_path=output_path,
            )

            # Show summary
            summary = get_report_summary(self.articles, certificates)
            QMessageBox.information(
                self,
                "Rapport genererad",
                f"PDF-rapporten har genererats:\n\n"
                f"Fil: {pdf_path.name}\n"
                f"Artiklar: {summary['article_count']}\n"
                f"Certifikat: {summary['certificate_count']}\n"
                f"Artiklar med charge: {summary['articles_with_charge']}\n"
                f"Watermark: {'Ja' if self.watermark_checkbox.isChecked() else 'Nej'}"
            )

        except ReportGenerationError as e:
            logger.error(f"Report generation failed: {e}")
            QMessageBox.critical(
                self,
                "Rapportgenerering misslyckades",
                f"{e.message}\n\nDetaljer: {e.details}"
            )

        except Exception as e:
            logger.exception("Unexpected error generating report")
            QMessageBox.critical(
                self,
                "Oväntat fel",
                f"Ett oväntat fel uppstod:\n\n{str(e)}"
            )

    def export_report(self):
        """
        Export report (called by wizard button).

        This is a simple wrapper around _generate_report() for consistency
        with wizard button callback naming.
        """
        logger.info("export_report() triggered from wizard button")
        self._generate_report()

    def isComplete(self):
        """Page is complete when articles are loaded."""
        return len(self.articles) > 0
