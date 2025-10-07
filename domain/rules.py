"""
Business rules for Tobbes v2.

These functions encode business logic and decision-making rules.
They are pure functions with no side effects.
"""

from typing import List, Optional
from .models import Article, InventoryItem, Certificate


# Certificate type keywords for auto-detection
CERTIFICATE_TYPE_KEYWORDS = {
    "materialintyg": "Materialintyg",
    "material": "Materialintyg",
    "3.1": "Materialintyg",
    "3.2": "Materialintyg",
    "certifikat": "Certifikat",
    "certificate": "Certifikat",
    "svets": "Svetslogg",
    "weld": "Svetslogg",
    "kontroll": "Kontrollrapport",
    "inspection": "Kontrollrapport",
    "provning": "Provningsprotokoll",
    "test": "Provningsprotokoll",
    "leverantör": "Leverantörsintyg",
    "supplier": "Leverantörsintyg",
    "kvalitet": "Kvalitetsintyg",
    "quality": "Kvalitetsintyg",
}


def guess_certificate_type(filename: str) -> str:
    """
    Guess certificate type from filename.

    Uses keyword matching against common certificate types.

    Args:
        filename: Certificate filename (e.g., "materialintyg_2024.pdf")

    Returns:
        Certificate type name (e.g., "Materialintyg")
        Defaults to "Andra handlingar" if no match found
    """
    filename_lower = filename.lower()

    for keyword, cert_type in CERTIFICATE_TYPE_KEYWORDS.items():
        if keyword in filename_lower:
            return cert_type

    return "Andra handlingar"


def find_best_charge_match(
    article: Article,
    inventory_items: List[InventoryItem],
) -> Optional[str]:
    """
    Find best charge match for an article from inventory.

    Matching rules:
    1. Exact article_number match
    2. Take most recent (last in list)
    3. If no matches, return None

    Args:
        article: Article to match
        inventory_items: Available inventory items (sorted by received_date)

    Returns:
        Charge number or None if no match found
    """
    matching_items = [
        item
        for item in inventory_items
        if item.article_number == article.article_number
    ]

    if matching_items:
        # Return most recent (last item, assuming sorted by received_date)
        return matching_items[-1].charge_number

    return None


def get_available_charges(
    article: Article,
    inventory_items: List[InventoryItem],
) -> List[str]:
    """
    Get all available charges for an article.

    Args:
        article: Article to find charges for
        inventory_items: Available inventory items

    Returns:
        List of unique charge numbers (most recent first)
    """
    matching_items = [
        item
        for item in inventory_items
        if item.article_number == article.article_number
    ]

    # Get unique charges, preserve order (most recent first)
    seen = set()
    charges = []
    for item in reversed(matching_items):
        if item.charge_number not in seen:
            charges.append(item.charge_number)
            seen.add(item.charge_number)

    return charges


def should_remove_certificates_on_charge_change(
    old_charge: Optional[str],
    new_charge: Optional[str],
) -> bool:
    """
    Determine if certificates should be removed when charge changes.

    Rule: Remove certificates if charge actually changes
    (e.g., from "CHARGE-A" to "CHARGE-B" or from None to "CHARGE-A")

    Args:
        old_charge: Previous charge number (can be None)
        new_charge: New charge number (can be None)

    Returns:
        True if certificates should be removed
    """
    # No change = keep certificates
    if old_charge == new_charge:
        return False

    # Change from/to None = remove certificates
    # Change between charges = remove certificates
    return True


def calculate_match_statistics(articles: List[Article]) -> dict:
    """
    Calculate matching statistics for a list of articles.

    Args:
        articles: Articles with charge_number populated

    Returns:
        Dict with statistics:
        - total: Total articles
        - matched: Articles with charge assigned
        - unmatched: Articles without charge
        - match_rate: Percentage of matched articles
    """
    total = len(articles)
    matched = sum(1 for a in articles if a.charge_number)
    unmatched = total - matched
    match_rate = (matched / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "matched": matched,
        "unmatched": unmatched,
        "match_rate": round(match_rate, 1),
    }


def group_certificates_by_article(
    certificates: List[Certificate],
) -> dict[str, List[Certificate]]:
    """
    Group certificates by article number.

    Args:
        certificates: List of certificates

    Returns:
        Dict mapping article_number to list of certificates
    """
    grouped = {}
    for cert in certificates:
        if cert.article_number not in grouped:
            grouped[cert.article_number] = []
        grouped[cert.article_number].append(cert)

    return grouped


def is_child_article(article: Article) -> bool:
    """
    Check if article is a child in BOM hierarchy.

    Args:
        article: Article to check

    Returns:
        True if article has a parent
    """
    return article.parent_article is not None and article.parent_article != ""


def get_level_depth(level: str) -> int:
    """
    Get depth of BOM level.

    Examples:
        "1" -> 1
        "1.1" -> 2
        "1.1.1" -> 3

    Args:
        level: Level string

    Returns:
        Depth (number of levels)
    """
    if not level:
        return 0
    return len(level.split("."))


def should_inherit_certificates(parent: Article, child: Article) -> bool:
    """
    Determine if child should inherit certificates from parent.

    Rule: Inherit if:
    - Child has same article_number as parent
    - Child has same charge_number as parent
    - Child has no certificates of its own

    Args:
        parent: Parent article
        child: Child article

    Returns:
        True if child should inherit
    """
    return (
        child.article_number == parent.article_number
        and child.charge_number == parent.charge_number
        and child.charge_number is not None
    )
