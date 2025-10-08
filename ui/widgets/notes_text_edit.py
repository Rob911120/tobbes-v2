"""
Notes Text Edit Widget for Tobbes v2.

Custom QTextEdit that saves on focus loss (blur) instead of every keystroke.
SQLite-optimized - no debouncing timer needed.
"""

import logging

try:
    from PySide6.QtWidgets import QTextEdit
    from PySide6.QtCore import Signal
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QTextEdit = object
    Signal = None

logger = logging.getLogger(__name__)


class NotesTextEdit(QTextEdit):
    """
    Custom QTextEdit that emits signal on focus loss.

    Designed for SQLite backends where saves are fast and
    debouncing is not necessary.

    Signals:
        focus_lost(str): Emitted when widget loses focus, with current text
    """

    focus_lost = Signal(str)

    def __init__(self, parent=None):
        """
        Initialize NotesTextEdit.

        Args:
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self._last_saved_text = ""

    def focusOutEvent(self, event):
        """
        Handle focus loss - emit signal if text changed.

        Args:
            event: QFocusEvent
        """
        super().focusOutEvent(event)

        current_text = self.toPlainText()

        # Only emit if text actually changed
        if current_text != self._last_saved_text:
            logger.debug(f"Notes text changed on blur (length: {len(current_text)})")
            self.focus_lost.emit(current_text)
            self._last_saved_text = current_text

    def setText(self, text: str):
        """
        Set text and update last saved state.

        Args:
            text: Text to set
        """
        self.setPlainText(text)
        self._last_saved_text = text
