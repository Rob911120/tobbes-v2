"""
Project View Page for Tobbes v2 Wizard.

Tab-based UI for article management and imports.
"""

import logging

try:
    from PySide6.QtWidgets import (
        QWizardPage, QVBoxLayout, QHBoxLayout, QTabWidget, QMessageBox,
        QPushButton, QLabel, QFrame
    )
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizardPage = object

from ui.tabs import ArticlesTab, ImportsTab

logger = logging.getLogger(__name__)


class ProjectViewPage(QWizardPage):
    """
    Project view page with tab-based UI.

    Features:
    - Tab 1: Artiklar (article management, verification, certificates)
    - Tab 2: Imports (file import, processing)
    - Navigation via wizard buttons (Tillbaka till projektoversikt)
    """

    def __init__(self, wizard):
        """Initialize project view page."""
        super().__init__()

        self.wizard_ref = wizard
        self.articles_tab = None
        self.imports_tab = None

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        # Don't use setTitle - we'll create custom header

        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with back button
        header_layout = QHBoxLayout()

        # Back button - icon only, flat style
        self.btn_back = QPushButton("←")
        self.btn_back.setToolTip("Tillbaka till projektoversikt")
        self.btn_back.clicked.connect(self._go_back)
        self.btn_back.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                font-weight: bold;
                border: none;
                background: transparent;
                padding: 4px 8px;
                color: #0066cc;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            QPushButton:pressed {
                background-color: #e0e0e0;
            }
        """)
        self.btn_back.setFixedWidth(40)
        header_layout.addWidget(self.btn_back)

        # Project title label
        self.project_label = QLabel("Projektvy")
        self.project_label.setStyleSheet("QLabel { font-size: 16px; font-weight: bold; }")
        header_layout.addWidget(self.project_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)

        layout.addWidget(self.tab_widget)
        self.setLayout(layout)

        # Note: Tabs will be created in initializePage() when page is shown
        # This ensures we have the current project context

    def initializePage(self):
        """
        Called automatically when page is shown.

        Creates tabs with current project context from wizard.
        """
        logger.info("Initializing project view page")

        # Clear old tabs if they exist
        self.tab_widget.clear()

        # Get context from wizard
        context = self.wizard_ref.context

        # Verify we have a project selected
        if not context.current_project_id:
            logger.error("No project selected in context")
            QMessageBox.critical(
                self,
                "Fel",
                "Inget projekt valt. Gå tillbaka till projektoversikten."
            )
            return

        try:
            # Create tabs with current project context
            self.articles_tab = ArticlesTab(context, parent=self)
            self.imports_tab = ImportsTab(context, parent=self)

            # Add tabs to widget
            self.tab_widget.addTab(self.articles_tab, "Artiklar")
            self.tab_widget.addTab(self.imports_tab, "Imports")

            # Connect signals
            if hasattr(self.imports_tab, 'processing_complete'):
                self.imports_tab.processing_complete.connect(self._on_processing_complete)

            # Update project label with project name
            project_name = context.project_name or f"Projekt {context.current_project_id}"
            self.project_label.setText(f"Projekt: {project_name}")

            logger.info(f"Project view initialized for: {project_name}")

        except Exception as e:
            logger.exception("Failed to initialize project view")
            QMessageBox.critical(
                self,
                "Fel",
                f"Kunde inte ladda projektvyn:\n\n{str(e)}"
            )

    def _go_back(self):
        """Navigate back to project overview."""
        logger.info("Back button clicked - navigating to project overview")
        self.wizard_ref._back_to_project_overview()

    def _on_processing_complete(self):
        """Handle processing complete signal from imports tab."""
        logger.info("Processing complete - refreshing articles tab")

        # Refresh articles tab to show updated data
        if self.articles_tab and hasattr(self.articles_tab, 'refresh_articles'):
            self.articles_tab.refresh_articles()

        # Switch to articles tab to show results
        self.tab_widget.setCurrentIndex(0)

    def cleanupPage(self):
        """
        Called when leaving this page.

        Auto-save any pending changes.
        """
        logger.info("Cleaning up project view page")

        # Auto-save articles tab if it has unsaved changes
        if self.articles_tab and hasattr(self.articles_tab, 'auto_save'):
            try:
                self.articles_tab.auto_save()
                logger.debug("Auto-saved articles before leaving page")
            except Exception as e:
                logger.exception("Failed to auto-save")
