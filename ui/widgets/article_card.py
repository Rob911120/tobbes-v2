"""
Article Card Widget for Tobbes v2.

Displays article information with all editable fields, based on v1 design.
SQLite-optimized: Direct saves instead of debounced JSON writes.
"""

import logging
from typing import Dict, Any

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QLineEdit, QSpinBox, QCheckBox, QFrame
    )
    from PySide6.QtCore import Signal, Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object
    Signal = None

from .charge_selector import ChargeSelector
from .batch_selector import BatchSelector
from .certificate_manager import CertificateManager
from .notes_text_edit import NotesTextEdit

logger = logging.getLogger(__name__)


class ArticleCard(QFrame):
    """
    Article card widget with full editing capabilities.

    Features:
    - Article header (number + description)
    - Batch number input
    - Charge selector (color-coded)
    - Quantity spinbox
    - Certificate manager
    - Comment field
    - Verified checkbox
    - Direct SQLite saves (no debouncing needed)

    Signals:
        verified_changed(bool): Emitted when verification checkbox changes
        save_required(): Emitted when any field changes (parent should save to DB)
        notes_changed(str, str): Emitted when notes change (article_number, notes_text)
    """

    # Signals
    verified_changed = Signal(bool)
    save_required = Signal()
    notes_changed = Signal(str, str)

    def __init__(
        self,
        article_data: Dict[str, Any],
        config: Dict[str, Any] = None,
        db=None,
        project_id: int = None,
        parent=None
    ):
        """
        Initialize article card.

        Args:
            article_data: Article data dict with keys:
                - article_number: str
                - description: str
                - quantity: float
                - batch_number: str (optional)
                - charge_number: str (optional)
                - available_charges: List[str] (optional)
                - charge_count: int (optional)
                - comment: str (optional)
                - verified: bool (optional)
                - certificates: List[dict] (optional)
            config: Config dict (for certificate types, etc.)
            db: Database interface (for certificate processing)
            project_id: Project ID (for certificate processing)
            parent: Parent widget
        """
        if not PYSIDE6_AVAILABLE:
            raise EnvironmentError("PySide6 is not installed")

        super().__init__(parent)

        self.article_data = article_data
        self.config = config or {}
        self.db = db
        self.project_id = project_id
        self.is_verified = article_data.get('verified', False)

        self._setup_card()
        self._create_widgets()
        self._setup_layout()
        self._connect_signals()

    def _setup_card(self):
        """Configure card styling."""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(1)
        self.setStyleSheet("""
            ArticleCard {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 8px;
                margin: 4px;
                padding: 8px;
            }

            ArticleCard:hover {
                border: 2px solid #0078d4;
                background-color: #f8f9fa;
            }

            ArticleCard[verified="true"] {
                border: 2px solid #28a745;
                background-color: #f8fff8;
            }
        """)

        # Set property for CSS selector
        self.setProperty("verified", str(self.is_verified).lower())

    def _create_widgets(self):
        """Create widgets for the card."""
        # Article info
        article_num = self.article_data.get('article_number', 'Okänt')
        description = self.article_data.get('description', 'Ingen beskrivning')

        self.article_header = QLabel(f"<b>{article_num}</b>")
        self.article_header.setStyleSheet("font-size: 14px; color: #0078d4;")
        self.article_header.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        self.description_label = QLabel(description)
        self.description_label.setWordWrap(True)
        self.description_label.setStyleSheet("color: #333; margin-bottom: 8px;")
        self.description_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )

        # Charge status (if multiple charges available)
        charge_count = self.article_data.get('charge_count', 0)
        if charge_count > 1:
            self.charge_status = QLabel(f"⚠ {charge_count} chargenummer tillgängliga")
            self.charge_status.setStyleSheet("""
                color: #ff9800;
                font-size: 11px;
                font-weight: bold;
                padding: 2px 4px;
                background-color: #fff3cd;
                border-radius: 3px;
            """)
        else:
            self.charge_status = None

        # Batch number section (same logic as charge - dropdown with multiple options)
        self.batch_label = QLabel("Batchnummer:")
        available_batches = self.article_data.get('available_batches', [])
        current_batch = self.article_data.get('batch_number') or ""  # Convert None → ""
        self.batch_selector = BatchSelector(
            available_batches=available_batches,
            current_value=current_batch
        )

        # Charge selector
        self.charge_label = QLabel("Chargenummer:")
        available_charges = self.article_data.get('available_charges', [])
        current_charge = self.article_data.get('charge_number') or ""  # Convert None → ""
        self.charge_selector = ChargeSelector(
            available_charges=available_charges,
            current_value=current_charge
        )

        # Quantity section
        self.quantity_label = QLabel("Kvantitet:")
        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 99999)
        self.quantity_input.setValue(int(self.article_data.get('quantity', 0)))

        # Certificate manager
        self.certificate_manager = CertificateManager(
            article_data=self.article_data,
            config=self.config,
            db=self.db,
            project_id=self.project_id
        )

        # Comment section (global notes - shared across all projects)
        self.comment_label = QLabel("Kommentar (global):")
        self.comment_input = NotesTextEdit()
        self.comment_input.setMaximumHeight(60)
        self.comment_input.setPlaceholderText("Global anteckning (delas över alla projekt)...")
        # Read from 'global_notes' field (returned by DB query)
        if self.article_data.get('global_notes'):
            self.comment_input.setText(self.article_data.get('global_notes', ''))

        # Verification checkbox
        self.verify_checkbox = QCheckBox("Verifierad")
        self.verify_checkbox.setChecked(self.is_verified)

    def _setup_layout(self):
        """Setup layout for the card."""
        main_layout = QVBoxLayout()

        # Header
        main_layout.addWidget(self.article_header)
        main_layout.addWidget(self.description_label)

        # Charge status if multiple charges
        if self.charge_status:
            main_layout.addWidget(self.charge_status)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # Data fields
        data_layout = QVBoxLayout()

        # Batch number with selector
        batch_layout = QHBoxLayout()
        batch_layout.addWidget(self.batch_label)
        batch_layout.addWidget(self.batch_selector)
        data_layout.addLayout(batch_layout)

        # Charge number with selector
        charge_layout = QHBoxLayout()
        charge_layout.addWidget(self.charge_label)
        charge_layout.addWidget(self.charge_selector)
        data_layout.addLayout(charge_layout)

        # Quantity
        quantity_layout = QHBoxLayout()
        quantity_layout.addWidget(self.quantity_label)
        quantity_layout.addWidget(self.quantity_input)
        quantity_layout.addStretch()
        data_layout.addLayout(quantity_layout)

        # Certificate manager
        data_layout.addWidget(self.certificate_manager)

        main_layout.addLayout(data_layout)

        # Comment
        main_layout.addWidget(self.comment_label)
        main_layout.addWidget(self.comment_input)

        # Verification
        main_layout.addWidget(self.verify_checkbox)

        self.setLayout(main_layout)

    def _connect_signals(self):
        """Connect signals for auto-save."""
        # Verified checkbox - save immediately
        self.verify_checkbox.toggled.connect(self._on_verify_toggled)

        # Other fields - save when editing finished
        self.batch_selector.batch_changed.connect(self._on_batch_changed)
        self.charge_selector.charge_changed.connect(self._on_charge_changed)
        self.quantity_input.editingFinished.connect(self._on_field_changed)

        # Global notes - save on focus loss (blur)
        self.comment_input.focus_lost.connect(self._on_notes_blur)

        # Certificate changes
        self.certificate_manager.certificate_added.connect(self._on_field_changed)

    def _on_verify_toggled(self, checked: bool):
        """Handle verification checkbox toggle."""
        self.is_verified = checked
        self.setProperty("verified", str(checked).lower())
        self.style().unpolish(self)
        self.style().polish(self)

        # Emit signals
        self.verified_changed.emit(checked)
        self.save_required.emit()

    def _on_batch_changed(self, batch: str):
        """Handle batch selector change."""
        self.article_data['batch_number'] = batch
        self.save_required.emit()

    def _on_charge_changed(self, charge: str):
        """Handle charge selector change."""
        self.article_data['charge_number'] = charge
        self.save_required.emit()

    def _on_field_changed(self):
        """Handle any field change - emit save signal."""
        self.save_required.emit()

    def _on_notes_blur(self, notes_text: str):
        """
        Handle notes field focus loss.

        Emits notes_changed signal for parent to save globally.

        Args:
            notes_text: Current notes text
        """
        article_number = self.article_data.get('article_number', '')
        if article_number:
            logger.debug(f"Notes changed for {article_number} (length: {len(notes_text)})")
            self.notes_changed.emit(article_number, notes_text)
        else:
            logger.warning("Cannot save notes - article_number missing")

    def get_article_data(self) -> Dict[str, Any]:
        """
        Get updated article data.

        Returns:
            Dict with all current field values
        """
        self.article_data.update({
            'batch_number': self.batch_selector.get_value(),
            'charge_number': self.charge_selector.get_value(),
            'quantity': self.quantity_input.value(),
            'global_notes': self.comment_input.toPlainText(),  # Global notes field
            'certificates': self.certificate_manager.selected_files,
            'verified': self.is_verified
        })
        return self.article_data

    def get_article_id(self) -> str:
        """Get unique ID for this article."""
        return self.article_data.get('article_number', '') or self.article_data.get('id', '')

    def set_verified(self, verified: bool):
        """
        Set verification status programmatically.

        Args:
            verified: True to mark as verified
        """
        self.is_verified = verified
        self.verify_checkbox.setChecked(verified)
        self.setProperty("verified", str(verified).lower())
        self.style().unpolish(self)
        self.style().polish(self)
