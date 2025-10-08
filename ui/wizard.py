"""
Main Wizard for Tobbes v2.

QWizard-based UI with AppContext for dependency injection.
"""

import logging
from pathlib import Path

try:
    from PySide6.QtWidgets import QWizard, QMessageBox
    from PySide6.QtCore import Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWizard = object
    QMessageBox = None
    Qt = None

from config import AppContext, create_app_context, get_settings, APP_NAME, APP_VERSION
from data import create_database

logger = logging.getLogger(__name__)


class TobbesWizard(QWizard):
    """
    Main wizard for Tobbes v2 - Spårbarhetsguiden.

    Manages:
    - AppContext (dependency injection)
    - Page navigation
    - Database connection
    - Project state

    Usage:
        >>> app = QApplication(sys.argv)
        >>> wizard = TobbesWizard()
        >>> wizard.show()
        >>> sys.exit(app.exec())
    """

    # Page IDs - SIMPLIFIED (only 2 pages)
    PAGE_START = 0          # Projektoversikt
    PAGE_PROJECT_VIEW = 1   # Artiklar + Imports (tab-based)

    def __init__(self, parent=None):
        """Initialize wizard with AppContext."""
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError(
                "PySide6 is not installed. Install with: pip install PySide6"
            )

        super().__init__(parent)

        # Initialize application context
        self._init_context()

        # Setup wizard UI
        self._setup_ui()

        # Add wizard pages (placeholders for now)
        self._add_pages()

        logger.info("TobbesWizard initialized successfully")

    def _init_context(self):
        """Initialize AppContext with database and settings."""
        try:
            # Load settings
            settings = get_settings()

            # Create database
            db = create_database(
                backend="sqlite",
                path=settings.database_path
            )

            # Create AppContext
            self.context = create_app_context(
                database=db,
                settings=settings,
                user_name=settings.user_name,
            )

            logger.info(f"AppContext initialized: user={self.context.user_name}, db={settings.database_path}")

        except Exception as e:
            logger.exception("Failed to initialize AppContext")
            raise

    def _setup_ui(self):
        """Setup wizard UI properties."""
        # Window properties
        self.setWindowTitle(f"{APP_NAME} - v{APP_VERSION}")
        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.HaveHelpButton, False)

        # Window size
        self.resize(
            self.context.settings.window_width,
            self.context.settings.window_height,
        )

        # Use Windows native theme (light mode)
        # No custom stylesheet - rely on system theme for clean Windows look

        # Configure custom buttons (matching v1)
        # CustomButton1 = "Tillbaka till projektoversikt" (left)
        # CustomButton2 = Dynamic text (right): "Bearbeta filer och fortsätt" / "Skapa rapport"
        self.setButtonLayout([
            QWizard.CustomButton1,
            QWizard.Stretch,
            QWizard.CustomButton2
        ])

        self.setButtonText(QWizard.CustomButton1, "Tillbaka till projektoversikt")
        self.setButtonText(QWizard.CustomButton2, "Nästa")  # Will be updated per page

        self.setOption(QWizard.HaveCustomButton1, True)
        self.setOption(QWizard.HaveCustomButton2, True)

        # Hide default navigation buttons
        self.setOption(QWizard.NoDefaultButton, True)
        if self.button(QWizard.NextButton):
            self.button(QWizard.NextButton).hide()
        if self.button(QWizard.BackButton):
            self.button(QWizard.BackButton).hide()
        if self.button(QWizard.FinishButton):
            self.button(QWizard.FinishButton).hide()

        # Connect signals
        self.currentIdChanged.connect(self._update_page_buttons)

        # Connect button actions
        back_button = self.button(QWizard.CustomButton1)
        if back_button:
            back_button.clicked.connect(self._back_to_project_overview)

        action_button = self.button(QWizard.CustomButton2)
        if action_button:
            action_button.clicked.connect(self._smart_button_action)

    def _add_pages(self):
        """Add wizard pages (SIMPLIFIED - only 2 pages)."""
        # Import pages here to avoid circular imports
        from ui.pages.start_page import StartPage
        from ui.pages.project_view_page import ProjectViewPage

        # Add pages using consistent IDs
        self.setPage(self.PAGE_START, StartPage(self))
        self.setPage(self.PAGE_PROJECT_VIEW, ProjectViewPage(self))

        logger.info("Wizard pages added (2 pages: Start + ProjectView)")

    def set_current_project(self, project_id: int, project_name: str = None):
        """
        Set current project in context.

        Called by pages when user selects/creates a project.

        Args:
            project_id: Project ID
            project_name: Optional project name for display
        """
        self.context = self.context.with_project(
            project_id=project_id,
            project_name=project_name
        )

        logger.info(f"Current project set: id={project_id}, name={project_name}")

    def clear_current_project(self):
        """Clear current project from context."""
        self.context = self.context.clear_project()
        logger.info("Current project cleared")

    def _update_page_buttons(self, page_id: int):
        """Update footer buttons based on current page (SIMPLIFIED)."""
        back_button = self.button(QWizard.CustomButton1)
        action_button = self.button(QWizard.CustomButton2)

        if not back_button or not action_button:
            return

        if page_id == self.PAGE_START:
            # Start page: No wizard buttons (just project list buttons)
            back_button.setVisible(False)
            action_button.setVisible(False)
            logger.debug("START page: Buttons hidden")

        elif page_id == self.PAGE_PROJECT_VIEW:
            # Project view: Hide all wizard buttons (page has own header navigation)
            back_button.setVisible(False)
            action_button.setVisible(False)
            logger.debug("PROJECT_VIEW page: All buttons hidden (page has own header nav)")

    def _back_to_project_overview(self):
        """Navigate back to start page (project overview)."""
        try:
            # Auto-save current page if supported
            current_page = self.currentPage()
            if hasattr(current_page, 'auto_save'):
                current_page.auto_save()
                logger.debug("Auto-saved before navigation")

            logger.info("Navigating back to project overview")
            self.setCurrentId(self.PAGE_START)

            # Reload project list
            start_page = self.page(self.PAGE_START)
            if hasattr(start_page, '_load_projects'):
                start_page._load_projects()
                logger.debug("Project list reloaded")

        except Exception as e:
            logger.exception("Failed to navigate to project overview")
            QMessageBox.critical(self, "Fel", f"Kunde inte navigera: {e}")

    def _smart_button_action(self):
        """Smart action button - different behavior per page (SIMPLIFIED)."""
        # Note: With only 2 pages, this is rarely used now
        # Project actions are handled within tabs themselves
        try:
            page_id = self.currentId()
            logger.warning(f"Smart button clicked on page {page_id} (not expected in 2-page design)")

        except Exception as e:
            logger.exception("Failed to execute smart button action")
            QMessageBox.critical(self, "Fel", f"Kunde inte utföra åtgärd: {e}")

    def closeEvent(self, event):
        """Handle wizard close event."""
        # TODO: Add confirmation dialog if work in progress

        logger.info("Wizard closing")
        event.accept()
