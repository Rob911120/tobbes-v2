"""
Article Card Widget for Tobbes v2.

Displays article information with editable global notes.
"""

import logging

try:
    from PySide6.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QLabel,
        QTextEdit, QGroupBox, QFrame
    )
    from PySide6.QtCore import QTimer, Qt
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False
    QWidget = object

from operations import update_article_notes
from domain.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class ArticleCard(QWidget):
    """
    Article card widget with global notes.

    Features:
    - Display article information (number, description, quantity, level, charge)
    - Editable global notes with auto-save (debounced)
    - Shows notes history on hover (TODO: future)

    Example:
        >>> card = ArticleCard(article_data, database, user_name="Tobbes")
        >>> layout.addWidget(card)
    """

    def __init__(self, article: dict, database, user_name: str = "user", parent=None):
        """
        Initialize article card.

        Args:
            article: Article dict with keys: article_number, description, quantity, etc.
            database: DatabaseInterface instance
            user_name: User name for audit logging
            parent: Parent widget
        """
        super().__init__(parent)

        self.article = article
        self.database = database
        self.user_name = user_name

        # Debounce timer for auto-save notes
        self.save_timer = QTimer(self)
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_notes)

        self._setup_ui()
        self._load_notes()

    def _setup_ui(self):
        """Setup UI components."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Article info section
        info_frame = QFrame()
        info_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        info_layout = QVBoxLayout()

        # Article number + description
        header_layout = QHBoxLayout()

        article_num_label = QLabel(f"<b>{self.article['article_number']}</b>")
        article_num_label.setProperty("class", "header")
        header_layout.addWidget(article_num_label)

        header_layout.addStretch()

        # Quantity
        qty = self.article.get("quantity", 0.0)
        qty_label = QLabel(f"Antal: {qty:.1f}")
        header_layout.addWidget(qty_label)

        info_layout.addLayout(header_layout)

        # Description
        desc = self.article.get("global_description", self.article.get("description", ""))
        if desc:
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)

        # Level + Charge
        details_layout = QHBoxLayout()

        level = self.article.get("level", "")
        if level:
            level_label = QLabel(f"Nivå: {level}")
            details_layout.addWidget(level_label)

        charge = self.article.get("charge_number", "")
        if charge:
            charge_label = QLabel(f"Charge: {charge}")
            details_layout.addWidget(charge_label)
        else:
            no_charge_label = QLabel("(Ingen charge)")
            no_charge_label.setStyleSheet("color: red;")
            details_layout.addWidget(no_charge_label)

        details_layout.addStretch()
        info_layout.addLayout(details_layout)

        info_frame.setLayout(info_layout)
        layout.addWidget(info_frame)

        # Notes section
        notes_group = QGroupBox("Anteckningar (delas globalt)")
        notes_layout = QVBoxLayout()

        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText(
            "Anteckningar för denna artikel (delas mellan alla projekt)..."
        )
        self.notes_edit.setMaximumHeight(100)
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        notes_layout.addWidget(self.notes_edit)

        # Notes hint
        hint_label = QLabel("💡 Anteckningar sparas automatiskt efter 1.5 sekunder")
        hint_label.setStyleSheet("color: #666666; font-size: 9pt;")
        notes_layout.addWidget(hint_label)

        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        self.setLayout(layout)

    def _load_notes(self):
        """Load notes from database."""
        try:
            notes = self.article.get("global_notes", "")
            if notes:
                # Block signals to avoid triggering save
                self.notes_edit.blockSignals(True)
                self.notes_edit.setText(notes)
                self.notes_edit.blockSignals(False)

        except Exception as e:
            logger.exception("Failed to load notes")

    def _on_notes_changed(self):
        """Handle notes text changed - start debounce timer."""
        # Restart timer on each change (debounce)
        self.save_timer.start(1500)  # 1.5 seconds

    def _save_notes(self):
        """Save notes to database (called after debounce)."""
        try:
            notes = self.notes_edit.toPlainText().strip()

            # Update via operation
            success = update_article_notes(
                db=self.database,
                article_number=self.article["article_number"],
                notes=notes,
                changed_by=self.user_name,
            )

            if success:
                logger.info(
                    f"Saved notes for {self.article['article_number']} "
                    f"({len(notes)} chars)"
                )
            else:
                logger.warning(f"Failed to save notes for {self.article['article_number']}")

        except DatabaseError as e:
            logger.error(f"Database error saving notes: {e}")

        except Exception as e:
            logger.exception("Unexpected error saving notes")

    def get_article_number(self) -> str:
        """Get article number."""
        return self.article["article_number"]

    def refresh_notes(self):
        """Refresh notes from database (useful after external update)."""
        try:
            global_article = self.database.get_global_article(
                self.article["article_number"]
            )
            if global_article:
                notes = global_article.get("notes", "")
                self.notes_edit.blockSignals(True)
                self.notes_edit.setText(notes)
                self.notes_edit.blockSignals(False)

        except Exception as e:
            logger.exception("Failed to refresh notes")
