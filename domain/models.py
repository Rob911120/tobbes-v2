"""
Domain models for Tobbes v2.

These dataclasses represent the core business entities.
They are framework-agnostic and have no dependencies on database or UI.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List


@dataclass
class Project:
    """
    Represents a traceability project.

    A project contains articles, inventory, and certificates.
    """

    project_name: str  # Artikelbenämning (e.g., "Gasturbinmotor")
    order_number: str  # Ordernummer (e.g., "TO-12345")
    customer: str  # Kund (e.g., "Volvo")
    created_by: str
    purchase_order_number: Optional[str] = None  # Beställningsnummer (e.g., "BI-2024-001")
    project_type: str = "Doc"  # Typ: "Doc" eller "Ej Doc"
    description: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate project data after initialization."""
        if not self.project_name:
            raise ValueError("project_name cannot be empty")
        if not self.order_number:
            raise ValueError("order_number cannot be empty")
        if not self.customer:
            raise ValueError("customer cannot be empty")
        if self.project_type not in ["Doc", "Ej Doc"]:
            raise ValueError("project_type must be 'Doc' or 'Ej Doc'")


@dataclass
class GlobalArticle:
    """
    Global article - shared across all projects.

    Notes and description are maintained globally and visible
    in any project that uses this article.
    """

    article_number: str
    description: str = ""
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    changed_by: Optional[str] = None

    def __post_init__(self):
        """Validate article data."""
        if not self.article_number:
            raise ValueError("article_number cannot be empty")


@dataclass
class Article:
    """
    Project-specific article (from BOM/nivålista).

    Contains project-specific data like quantity, level, and charge.
    Global notes are joined from GlobalArticle.
    """

    project_id: int
    article_number: str
    description: str = ""
    quantity: float = 0.0
    level: str = ""
    parent_article: Optional[str] = None
    charge_number: Optional[str] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Joined from global_articles
    global_notes: str = ""
    global_description: str = ""

    def __post_init__(self):
        """Validate article data."""
        if not self.article_number:
            raise ValueError("article_number cannot be empty")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")


@dataclass
class InventoryItem:
    """
    Inventory item (from lagerlogg).

    Represents a batch of material with a specific charge number.
    """

    project_id: int
    article_number: str
    charge_number: str
    quantity: float = 0.0
    batch_id: Optional[str] = None
    location: Optional[str] = None
    received_date: Optional[datetime] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate inventory item."""
        if not self.article_number:
            raise ValueError("article_number cannot be empty")
        if not self.charge_number:
            raise ValueError("charge_number cannot be empty")
        if self.quantity < 0:
            raise ValueError("quantity cannot be negative")


@dataclass
class Certificate:
    """
    Certificate/PDF document for an article.

    Can be linked to a specific project article or shared across levels.
    """

    project_id: int
    article_number: str
    certificate_type: str
    file_path: str  # Relative path to certificate file
    original_filename: str
    page_count: int = 1
    project_article_id: Optional[int] = None
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate certificate."""
        if not self.article_number:
            raise ValueError("article_number cannot be empty")
        if not self.certificate_type:
            raise ValueError("certificate_type cannot be empty")
        if not self.file_path:
            raise ValueError("file_path cannot be empty")
        if self.page_count <= 0:
            raise ValueError("page_count must be positive")

    def get_full_path(self, base_dir: Path) -> Path:
        """Get full path to certificate file."""
        return base_dir / self.file_path


@dataclass
class CertificateType:
    """
    Certificate type (global or project-specific).

    Examples: "Materialintyg", "Svetslogg", "Kontrollrapport"
    """

    type_name: str
    project_id: Optional[int] = None  # None = global type
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate certificate type."""
        if not self.type_name:
            raise ValueError("type_name cannot be empty")

    @property
    def is_global(self) -> bool:
        """Check if this is a global certificate type."""
        return self.project_id is None


@dataclass
class ArticleUpdate:
    """
    Represents a potential update to a project article.

    Used when importing new versions of nivålista/lagerlogg to
    show the user what would change.
    """

    article_number: str
    field_name: str  # e.g., "charge_number", "quantity"
    old_value: any
    new_value: any
    update_type: str  # "nivalista" or "lagerlogg"
    affects_certificates: bool = False

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"{self.article_number}: {self.field_name} '{self.old_value}' → '{self.new_value}'"


@dataclass
class NotesAuditEntry:
    """
    Audit log entry for article notes changes.

    Automatically created by database triggers.
    """

    article_number: str
    old_notes: Optional[str]
    new_notes: str
    changed_by: str
    changed_at: datetime
    id: Optional[int] = None

    def __str__(self) -> str:
        """User-friendly string representation."""
        timestamp = self.changed_at.strftime("%Y-%m-%d %H:%M")
        return f"[{timestamp}] {self.changed_by}: {self.old_notes} → {self.new_notes}"


@dataclass
class MatchResult:
    """
    Result of matching articles with inventory charges.

    Used in the matching/process step to track which articles
    got matched and which need manual charge selection.
    """

    article: Article
    available_charges: List[str] = field(default_factory=list)
    selected_charge: Optional[str] = None
    auto_matched: bool = False

    @property
    def needs_manual_selection(self) -> bool:
        """Check if user needs to manually select a charge."""
        return len(self.available_charges) > 1 and not self.selected_charge

    @property
    def is_matched(self) -> bool:
        """Check if article has a selected charge."""
        return self.selected_charge is not None

    @property
    def match_status(self) -> str:
        """
        Get user-friendly match status.

        Returns:
            "matched" - Has a selected charge
            "needs_selection" - Multiple charges available
            "no_charges" - No charges available
        """
        if self.is_matched:
            return "matched"
        elif len(self.available_charges) > 1:
            return "needs_selection"
        else:
            return "no_charges"
