"""
Operations layer for Tobbes v2.

Business logic operations - pure functions with dependency injection.
No database access - returns data structures that can be saved separately.
"""

from .import_ops import (
    import_nivalista,
    import_lagerlogg,
    validate_import_file,
    get_import_summary,
)

from .process_ops import (
    match_articles_with_charges,
    apply_charge_selection,
    get_matching_summary,
    get_unmatched_articles,
    get_articles_needing_manual_selection,
)

from .certificate_ops import (
    guess_certificate_type,
    validate_certificate_file,
    create_certificate_dict,
    get_certificates_summary,
    get_certificates_for_article,
    get_certificates_by_type,
    get_articles_with_certificates,
    get_articles_without_certificates,
)

from .article_ops import (
    update_article_notes,
    get_articles_for_project,
    get_notes_history,
    get_articles_with_notes,
)

from .update_ops import (
    compare_articles_for_update,
    apply_updates,
    get_update_summary,
    filter_updates_by_field,
    get_articles_with_updates,
)

from .report_ops import (
    generate_material_specification_html,
    generate_pdf_report,
    merge_certificates_into_report,
    create_table_of_contents,
    get_report_summary,
    filter_articles_by_charge_status,
)

__all__ = [
    # Import Operations
    "import_nivalista",
    "import_lagerlogg",
    "validate_import_file",
    "get_import_summary",
    # Process Operations
    "match_articles_with_charges",
    "apply_charge_selection",
    "get_matching_summary",
    "get_unmatched_articles",
    "get_articles_needing_manual_selection",
    # Certificate Operations
    "guess_certificate_type",
    "validate_certificate_file",
    "create_certificate_dict",
    "get_certificates_summary",
    "get_certificates_for_article",
    "get_certificates_by_type",
    "get_articles_with_certificates",
    "get_articles_without_certificates",
    # Article Operations
    "update_article_notes",
    "get_articles_for_project",
    "get_notes_history",
    "get_articles_with_notes",
    # Update Operations
    "compare_articles_for_update",
    "apply_updates",
    "get_update_summary",
    "filter_updates_by_field",
    "get_articles_with_updates",
    # Report Operations
    "generate_material_specification_html",
    "generate_pdf_report",
    "merge_certificates_into_report",
    "create_table_of_contents",
    "get_report_summary",
    "filter_articles_by_charge_status",
]
