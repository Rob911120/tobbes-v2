"""
Progress View Widget.

Displays progress during long-running operations.
"""

import logging
from typing import Optional

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QLabel,
        QProgressBar, QTextEdit
    )
    from PySide6.QtCore import Qt, Signal, Slot
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    Signal = None
    Slot = None

logger = logging.getLogger(__name__)


class ProgressView(QWidget):
    """
    Progress view widget for long-running operations.

    Features:
    - Progress bar (0-100%)
    - Status message
    - Log output (optional)
    - Cancel support (optional)

    Signals:
        cancelled: Emitted when user cancels operation
    """

    # Signals
    cancelled = Signal()

    def __init__(
        self,
        title: str = "Pågår...",
        show_log: bool = False,
        parent=None
    ):
        """
        Initialize progress view.

        Args:
            title: Title text
            show_log: Show log output area
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.title = title
        self.show_log = show_log

        self._setup_ui()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setProperty("class", "header")
        layout.addWidget(self.title_label)

        # Status message
        self.status_label = QLabel("Startar...")
        layout.addWidget(self.status_label)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Log output (optional)
        if self.show_log:
            log_label = QLabel("Logg:")
            layout.addWidget(log_label)

            self.log_output = QTextEdit()
            self.log_output.setReadOnly(True)
            self.log_output.setMaximumHeight(150)
            layout.addWidget(self.log_output)

        layout.addStretch()

        self.setLayout(layout)

    @Slot(int)
    def set_progress(self, value: int):
        """
        Set progress value (0-100).

        Args:
            value: Progress percentage
        """
        self.progress_bar.setValue(max(0, min(100, value)))

    @Slot(str)
    def set_status(self, message: str):
        """
        Set status message.

        Args:
            message: Status message
        """
        self.status_label.setText(message)
        logger.debug(f"Progress status: {message}")

    @Slot(str)
    def append_log(self, message: str):
        """
        Append message to log output.

        Args:
            message: Log message
        """
        if self.show_log and hasattr(self, 'log_output'):
            self.log_output.append(message)

    @Slot()
    def set_indeterminate(self):
        """Set progress bar to indeterminate mode (spinning)."""
        self.progress_bar.setRange(0, 0)

    @Slot()
    def set_determinate(self):
        """Set progress bar to determinate mode (percentage)."""
        self.progress_bar.setRange(0, 100)

    @Slot()
    def reset(self):
        """Reset progress view."""
        self.progress_bar.setValue(0)
        self.status_label.setText("Startar...")

        if self.show_log and hasattr(self, 'log_output'):
            self.log_output.clear()

    @Slot()
    def set_complete(self, message: str = "Klart!"):
        """
        Mark operation as complete.

        Args:
            message: Completion message
        """
        self.progress_bar.setValue(100)
        self.status_label.setText(message)
        logger.info(f"Progress complete: {message}")

    @Slot()
    def set_error(self, message: str):
        """
        Mark operation as failed.

        Args:
            message: Error message
        """
        self.status_label.setText(f"❌ {message}")
        self.status_label.setStyleSheet("color: #f44336;")
        logger.error(f"Progress error: {message}")

    def get_progress(self) -> int:
        """Get current progress value."""
        return self.progress_bar.value()

    def is_complete(self) -> bool:
        """Check if progress is complete (100%)."""
        return self.progress_bar.value() == 100
