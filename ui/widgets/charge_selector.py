"""
Charge Selector Widget.

Smart dropdown med färgkodning:
- Grå: Manuell inmatning (inga val)
- Grön: Matchad (ett val)
- Gul: Val krävs (flera val)
"""

import logging
from typing import List, Optional, Callable

try:
    from PySide6.QtWidgets import QWidget, QHBoxLayout, QComboBox, QLineEdit, QLabel
    from PySide6.QtCore import Signal, Qt
    from PySide6.QtGui import QColor, QPalette
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    Signal = None

logger = logging.getLogger(__name__)


class ChargeSelector(QWidget):
    """
    Smart charge selector widget med färgkodning.

    States:
    - GRAY (no options): Manual input required
    - GREEN (single option): Auto-matched
    - YELLOW (multiple options): User selection required

    Signals:
        charge_changed: Emitted when charge value changes
    """

    # Signals
    charge_changed = Signal(str)  # New charge value

    # Color states
    COLOR_GRAY = "#9E9E9E"      # No options
    COLOR_GREEN = "#4CAF50"     # Single option (matched)
    COLOR_YELLOW = "#FFC107"    # Multiple options (needs selection)

    def __init__(
        self,
        available_charges: List[str],
        current_value: str = "",
        on_change: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        """
        Initialize charge selector.

        Args:
            available_charges: List of available charge numbers
            current_value: Current charge value
            on_change: Optional callback when charge changes
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.available_charges = available_charges
        self.current_value = current_value
        self.on_change_callback = on_change

        self._setup_ui()
        self._apply_state()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Label
        self.label = QLabel("Charge:")
        layout.addWidget(self.label)

        # ComboBox for selections
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.currentTextChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo)

        # Status indicator (colored dot)
        self.status_label = QLabel("●")
        self.status_label.setFixedWidth(20)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _apply_state(self):
        """Apply color state based on available charges."""
        num_charges = len(self.available_charges)

        if num_charges == 0:
            self._set_gray_state()
        elif num_charges == 1:
            self._set_green_state()
        else:
            self._set_yellow_state()

    def _set_gray_state(self):
        """Set gray state (no options - manual input)."""
        self.combo.clear()
        self.combo.setEditable(True)
        self.combo.setPlaceholderText("Ange chargenummer manuellt...")

        if self.current_value:
            self.combo.setCurrentText(self.current_value)

        self._set_status_color(self.COLOR_GRAY, "Ingen match - manuell inmatning")

    def _set_green_state(self):
        """Set green state (single option - auto-matched)."""
        self.combo.clear()
        self.combo.addItem(self.available_charges[0])
        self.combo.setCurrentIndex(0)
        self.combo.setEditable(False)

        self._set_status_color(self.COLOR_GREEN, "Automatiskt matchad")

    def _set_yellow_state(self):
        """Set yellow state (multiple options - user selection required)."""
        self.combo.clear()
        self.combo.addItem("")  # Empty option
        self.combo.addItems(self.available_charges)
        self.combo.setEditable(True)

        # Set current value if it exists
        if self.current_value and self.current_value in self.available_charges:
            self.combo.setCurrentText(self.current_value)
        else:
            self.combo.setCurrentIndex(0)  # Empty

        self._set_status_color(self.COLOR_YELLOW, "Välj chargenummer")

    def _set_status_color(self, color: str, tooltip: str):
        """Set status indicator color."""
        self.status_label.setStyleSheet(f"color: {color}; font-size: 16px;")
        self.status_label.setToolTip(tooltip)

    def _on_combo_changed(self, text: str):
        """Handle combo box value change."""
        self.current_value = text.strip()

        # Emit signal
        self.charge_changed.emit(self.current_value)

        # Call callback
        if self.on_change_callback:
            self.on_change_callback(self.current_value)

        logger.debug(f"Charge changed: {self.current_value}")

    def get_value(self) -> str:
        """Get current charge value."""
        return self.current_value

    def set_value(self, value: str):
        """Set charge value programmatically."""
        self.current_value = value
        self.combo.setCurrentText(value)

    def update_available_charges(self, charges: List[str], current_value: str = ""):
        """
        Update available charges and refresh state.

        Args:
            charges: New list of available charges
            current_value: New current value (optional)
        """
        self.available_charges = charges

        if current_value:
            self.current_value = current_value

        self._apply_state()

        logger.debug(f"Updated charges: {len(charges)} options")

    def is_valid(self) -> bool:
        """Check if current value is valid."""
        # Empty is invalid
        if not self.current_value:
            return False

        # If there are available charges, value must be in list
        if self.available_charges:
            return self.current_value in self.available_charges

        # Manual input is valid if not empty
        return True

    def get_state(self) -> str:
        """
        Get current state.

        Returns:
            'gray', 'green', or 'yellow'
        """
        num_charges = len(self.available_charges)

        if num_charges == 0:
            return "gray"
        elif num_charges == 1:
            return "green"
        else:
            return "yellow"
