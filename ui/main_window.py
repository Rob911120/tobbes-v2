"""
Main Window for Tobbes v2.

Replaces wizard flow with tab-based UI:
- Tab 1: Artiklar (article management, verification, certificates)
- Tab 2: Imports (file import, processing, updates)
"""

import logging
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QMainWindow, QTabWidget, QWidget, QVBoxLayout,
        QToolBar, QPushButton, QMessageBox, QLabel,
        QSizePolicy
    )
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QAction
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QMainWindow = object

from config import AppContext, APP_NAME, APP_VERSION

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window with tab-based UI.

    Replaces QWizard with simpler tab navigation.

    Features:
    - Two tabs: Artiklar (articles) + Imports (file management)
    - Toolbar with "Back to project overview" button
    - Status bar with project info
    - No forced navigation flow
    """

    # Signal to indicate user wants to return to project overview
    back_to_overview = Signal()

    def __init__(self, context: AppContext, parent=None):
        """
        Initialize main window.

        Args:
            context: AppContext with project_id and database
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError(
                "PySide6 is not installed. Install with: pip install PySide6"
            )

        super().__init__(parent)

        self.context = context

        # Verify we have a project selected
        try:
            project_id = context.require_project()
            logger.info(f"MainWindow initialized for project: {project_id}")
        except Exception as e:
            logger.error(f"MainWindow requires project context: {e}")
            raise

        self._setup_ui()
        self._create_tabs()
        self._setup_toolbar()
        self._setup_statusbar()

        logger.info("MainWindow initialized successfully")

    def _setup_ui(self):
        """Setup main window properties."""
        # Window title
        project_name = self.context.project_name or f"Project {self.context.current_project_id}"
        self.setWindowTitle(f"{APP_NAME} - {project_name} - v{APP_VERSION}")

        # Window size
        self.resize(
            self.context.settings.window_width,
            self.context.settings.window_height,
        )

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

    def _create_tabs(self):
        """Create tab widget with two tabs."""
        # Import tab classes here to avoid circular imports
        from ui.tabs import ArticlesTab, ImportsTab

        # Create tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        self.tab_widget.setMovable(False)

        # Tab 1: Artiklar (primary workspace)
        self.articles_tab = ArticlesTab(self.context, parent=self)
        self.tab_widget.addTab(self.articles_tab, "Artiklar")

        # Tab 2: Imports (file management + processing)
        self.imports_tab = ImportsTab(self.context, parent=self)
        self.tab_widget.addTab(self.imports_tab, "Imports")

        # Connect signal from imports tab to refresh articles tab
        self.imports_tab.processing_complete.connect(self._on_processing_complete)

        # Add to main layout
        self.main_layout.addWidget(self.tab_widget)

        logger.debug("Tabs created: Artiklar + Imports")

    def _setup_toolbar(self):
        """Create toolbar with navigation buttons."""
        toolbar = QToolBar("Navigation")
        toolbar.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, toolbar)

        # Back to project overview button
        back_action = QAction("← Tillbaka till projektoversikt", self)
        back_action.triggered.connect(self._back_to_overview_clicked)
        toolbar.addAction(back_action)

        toolbar.addSeparator()

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred
        )
        toolbar.addWidget(spacer)

        # Project info label
        project_name = self.context.project_name or f"Project {self.context.current_project_id}"
        self.project_label = QLabel(f"<b>{project_name}</b>")
        toolbar.addWidget(self.project_label)

    def _setup_statusbar(self):
        """Create status bar."""
        statusbar = self.statusBar()

        # Show current tab
        self.tab_widget.currentChanged.connect(self._update_statusbar)
        self._update_statusbar(0)  # Initial status

    def _update_statusbar(self, index: int):
        """Update status bar when tab changes."""
        tab_names = ["Artiklar", "Imports"]
        if 0 <= index < len(tab_names):
            self.statusBar().showMessage(f"Aktiv flik: {tab_names[index]}")

    def _back_to_overview_clicked(self):
        """Handle back to overview button click."""
        # Auto-save any pending changes
        try:
            if hasattr(self.articles_tab, 'auto_save'):
                self.articles_tab.auto_save()

            # Emit signal (StartPage will handle closing this window)
            self.back_to_overview.emit()

            # Note: self.close() removed - StartPage handles window closing

        except Exception as e:
            logger.exception("Failed to return to overview")
            QMessageBox.warning(
                self,
                "Fel",
                f"Kunde inte återgå till projektoversikt: {e}"
            )

    def _on_processing_complete(self):
        """Handle processing complete signal from imports tab."""
        # Refresh articles tab to show updated data
        if hasattr(self.articles_tab, 'refresh_articles'):
            self.articles_tab.refresh_articles()
            logger.info("Articles tab refreshed after processing")

        # Switch to articles tab to show results
        self.tab_widget.setCurrentIndex(0)

        logger.info("Processing complete - switched to articles tab")

    def closeEvent(self, event):
        """Handle window close event."""
        # TODO: Check for unsaved changes
        logger.info("MainWindow closing")
        event.accept()
