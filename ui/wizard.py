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
        self.setOption(QWizard.NoBackButtonOnStartPage, True)

        # Window size
        self.resize(
            self.context.settings.window_width,
            self.context.settings.window_height,
        )

        # Use Windows native theme (light mode)
        # No custom stylesheet - rely on system theme for clean Windows look

    def _add_pages(self):
        """Add wizard pages."""
        # Import pages here to avoid circular imports
        from ui.pages.start_page import StartPage
        from ui.pages.import_page import ImportPage
        from ui.pages.process_page import ProcessPage
        from ui.pages.export_page import ExportPage
        from ui.pages.update_page import UpdatePage

        # Add pages
        self.start_page_id = self.addPage(StartPage(self))
        self.import_page_id = self.addPage(ImportPage(self))
        self.process_page_id = self.addPage(ProcessPage(self))
        self.export_page_id = self.addPage(ExportPage(self))
        self.update_page_id = self.addPage(UpdatePage(self))

        logger.info("Wizard pages added")

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

    def closeEvent(self, event):
        """Handle wizard close event."""
        # TODO: Add confirmation dialog if work in progress

        logger.info("Wizard closing")
        event.accept()
