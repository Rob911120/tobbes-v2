"""
Batch Selector Widget.

Smart dropdown med färgkodning:
- Röd: Inget batch valt (kritiskt)
- Grön: Batch vald (OK)
- Gul: Flera val tillgängliga (användaren måste välja)
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


class BatchSelector(QWidget):
    """
    Smart batch selector widget med färgkodning.

    States:
    - RED (no value selected): Critical - must select
    - GREEN (value selected): OK
    - YELLOW (multiple options): User selection required

    Signals:
        batch_changed: Emitted when batch value changes
    """

    # Signals
    batch_changed = Signal(str)  # New batch value

    # Color states
    COLOR_RED = "#dc3545"        # No value selected
    COLOR_GREEN = "#4CAF50"     # Value selected (matched)
    COLOR_YELLOW = "#FFC107"    # Multiple options (needs selection)

    def __init__(
        self,
        available_batches: List[str],
        current_value: str = "",
        on_change: Optional[Callable[[str], None]] = None,
        parent=None
    ):
        """
        Initialize batch selector.

        Args:
            available_batches: List of available batch numbers
            current_value: Current batch value
            on_change: Optional callback when batch changes
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.available_batches = available_batches
        self.current_value = current_value
        self.on_change_callback = on_change

        self._setup_ui()
        self._apply_state()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        # Status indicator (icon before combo)
        self.status_label = QLabel()
        self.status_label.setMaximumWidth(20)
        layout.addWidget(self.status_label)

        # ComboBox for selections
        self.combo = QComboBox()
        self.combo.setEditable(True)
        self.combo.currentTextChanged.connect(self._on_combo_changed)
        layout.addWidget(self.combo)

        # Count label for multiple batches
        self.count_label = QLabel()
        self.count_label.setStyleSheet("color: #666; font-size: 11px; margin-left: 4px;")
        self.count_label.setVisible(False)
        layout.addWidget(self.count_label)

        self.setLayout(layout)

    def _apply_state(self):
        """Apply color state based on available batches and current value."""
        # Priority 1: If we HAVE a value - always green! (regardless of available options)
        if self.current_value:
            self._set_green_state_with_value()
            return

        # Priority 2: No value - check available options
        num_batches = len(self.available_batches)

        if num_batches == 0:
            self._set_red_state()
        elif num_batches == 1:
            self._set_green_state()
        else:
            # Multiple options - needs selection
            self._set_yellow_state()

    def _set_red_state(self):
        """Set red state (no value selected - critical)."""
        self.combo.clear()
        self.combo.setEditable(True)
        self.combo.setPlaceholderText("Ange batchnummer manuellt...")

        if self.current_value:
            self.combo.setCurrentText(self.current_value)

        # Always add "Manual entry" option
        self.combo.addItem("-- Ange manuellt --")

        self._set_status_icon("✗", "Inget batch valt", "red")
        self._set_combo_style("#ffe6e6", "#dc3545")
        self.count_label.setVisible(False)

    def _set_green_state(self):
        """Set green state (value selected - OK)."""
        self.combo.clear()
        self.combo.addItem(self.available_batches[0] if len(self.available_batches) == 1 else self.current_value)

        # Add manual entry option
        self.combo.addItem("-- Ange manuellt --")

        self.combo.setCurrentIndex(0)
        self.combo.setEditable(True)

        self._set_status_icon("✓", "Batch valt", "green")
        self._set_combo_style("#e8f5e9", "#4caf50")
        self.count_label.setVisible(False)

    def _set_green_state_with_value(self):
        """Set green state when current_value exists (manual or from options)."""
        self.combo.clear()

        # Add current value first
        self.combo.addItem(self.current_value)

        # Add other available batches if they exist
        for batch in self.available_batches:
            if batch != self.current_value:
                self.combo.addItem(batch)

        # Add manual entry option
        self.combo.addItem("-- Ange manuellt --")

        self.combo.setCurrentIndex(0)  # Select current value
        self.combo.setEditable(True)

        self._set_status_icon("✓", "Batch valt", "green")
        self._set_combo_style("#e8f5e9", "#4caf50")
        self.count_label.setVisible(False)

    def _set_yellow_state(self):
        """Set yellow state (multiple options - user selection required)."""
        self.combo.clear()
        self.combo.addItems(self.available_batches)

        # Add manual entry option
        self.combo.addItem("-- Ange manuellt --")

        self.combo.setEditable(True)

        # Set current value if it exists and matches
        if self.current_value and self.current_value in self.available_batches:
            self.combo.setCurrentText(self.current_value)
            self._set_status_icon("✓", "Batch valt", "green")
            self._set_combo_style("#e8f5e9", "#4caf50")
        else:
            self.combo.setCurrentText("")
            self._set_status_icon("⚠", f"{len(self.available_batches)} alternativ - välj ett", "orange")
            self._set_combo_style("#fff3cd", "#ffc107")

        # Show count label for multiple options
        self.count_label.setText(f"({len(self.available_batches)} alt.)")
        self.count_label.setVisible(True)

    def _set_status_icon(self, icon: str, tooltip: str, color: str):
        """Set status indicator icon and color."""
        self.status_label.setText(icon)
        self.status_label.setToolTip(tooltip)

        color_map = {
            "red": "#dc3545",
            "green": "#4caf50",
            "orange": "#ffc107"
        }

        style = f"color: {color_map.get(color, color)};"
        if color in ["green", "orange", "red"]:
            style += " font-weight: bold;"
        self.status_label.setStyleSheet(style)

    def _set_combo_style(self, bg_color: str, border_color: str):
        """Set combo box background and border styling."""
        self.combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {bg_color};
                border: 1px solid {border_color};
            }}
        """)

    def _on_combo_changed(self, text: str):
        """Handle combo box value change."""
        # Handle manual entry selection
        if text == "-- Ange manuellt --":
            self.combo.setCurrentText("")
            # Update style based on original number of batches
            if len(self.available_batches) == 0:
                self._set_status_icon("✗", "Inget batch valt", "red")
                self._set_combo_style("#ffe6e6", "#dc3545")
            else:
                self._set_status_icon("⚠", f"{len(self.available_batches)} alternativ - välj ett", "orange")
                self._set_combo_style("#fff3cd", "#ffc107")
            return

        self.current_value = text.strip()

        # Update styling based on value
        if text.strip():
            # Value exists - set green style
            self._set_status_icon("✓", "Batch valt", "green")
            self._set_combo_style("#e8f5e9", "#4caf50")
        else:
            # Empty value - set style based on number of batches
            if len(self.available_batches) == 0:
                self._set_status_icon("✗", "Inget batch valt", "red")
                self._set_combo_style("#ffe6e6", "#dc3545")
            elif len(self.available_batches) > 1:
                self._set_status_icon("⚠", f"{len(self.available_batches)} alternativ - välj ett", "orange")
                self._set_combo_style("#fff3cd", "#ffc107")
            # For 1 batch keep green since auto-match exists

        # Emit signal
        self.batch_changed.emit(self.current_value)

        # Call callback
        if self.on_change_callback:
            self.on_change_callback(self.current_value)

        logger.debug(f"Batch changed: {self.current_value}")

    def get_value(self) -> str:
        """Get current batch value."""
        return self.current_value

    def set_value(self, value: str):
        """Set batch value programmatically."""
        self.current_value = value
        self.combo.setCurrentText(value)

    def update_available_batches(self, batches: List[str], current_value: str = ""):
        """
        Update available batches and refresh state.

        Args:
            batches: New list of available batches
            current_value: New current value (optional)
        """
        self.available_batches = batches

        if current_value:
            self.current_value = current_value

        self._apply_state()

        logger.debug(f"Updated batches: {len(batches)} options")

    def is_valid(self) -> bool:
        """Check if current value is valid."""
        # Empty is invalid
        if not self.current_value:
            return False

        # If there are available batches, value must be in list
        if self.available_batches:
            return self.current_value in self.available_batches

        # Manual input is valid if not empty
        return True

    def get_state(self) -> str:
        """
        Get current state.

        Returns:
            'red', 'green', or 'yellow'
        """
        num_batches = len(self.available_batches)

        if num_batches == 0:
            return "red"
        elif num_batches == 1:
            return "green"
        else:
            # Multiple - check if value selected
            if self.current_value and self.current_value in self.available_batches:
                return "green"
            else:
                return "yellow"
