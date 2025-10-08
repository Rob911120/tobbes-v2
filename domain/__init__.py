"""
Domain layer for Tobbes v2.

This module contains core business entities, rules, and validators.
No dependencies on database, UI, or external frameworks.
"""

from .models import (
    Project,
    GlobalArticle,
    Article,
    InventoryItem,
    Certificate,
    CertificateType,
    ArticleUpdate,
    NotesAuditEntry,
    MatchResult,
)

from .exceptions import (
    TobbesBaseException,
    DatabaseError,
    ImportValidationError,
    CertificateError,
    ReportGenerationError,
    ValidationError,
    NotFoundError,
)

from .validators import (
    validate_order_number,
    validate_article_number,
    validate_charge_number,
    validate_quantity,
    validate_file_path,
    validate_level_number,
    validate_certificate_type,
    validate_project_name,
    validate_customer_name,
    sanitize_filename,
)

from .rules import (
    guess_certificate_type,
    get_available_charges,
    get_available_batches,
    should_remove_certificates_on_charge_change,
    calculate_match_statistics,
    group_certificates_by_article,
    is_child_article,
    get_level_depth,
    should_inherit_certificates,
    CERTIFICATE_TYPE_KEYWORDS,
)

__all__ = [
    # Models
    "Project",
    "GlobalArticle",
    "Article",
    "InventoryItem",
    "Certificate",
    "CertificateType",
    "ArticleUpdate",
    "NotesAuditEntry",
    "MatchResult",
    # Exceptions
    "TobbesBaseException",
    "DatabaseError",
    "ImportValidationError",
    "CertificateError",
    "ReportGenerationError",
    "ValidationError",
    "NotFoundError",
    # Validators
    "validate_order_number",
    "validate_article_number",
    "validate_charge_number",
    "validate_quantity",
    "validate_file_path",
    "validate_level_number",
    "validate_certificate_type",
    "validate_project_name",
    "validate_customer_name",
    "sanitize_filename",
    # Rules
    "guess_certificate_type",
    "get_available_charges",
    "get_available_batches",
    "should_remove_certificates_on_charge_change",
    "calculate_match_statistics",
    "group_certificates_by_article",
    "is_child_article",
    "get_level_depth",
    "should_inherit_certificates",
    "CERTIFICATE_TYPE_KEYWORDS",
]
