"""
Certificate Operations for Tobbes v2.

Certificate management operations.
Pure functions - no database access, no side effects.

According to plan (Week 2, Day 8-9):
- guess_certificate_type() - Re-exported from domain.rules
- validate_certificate() - Validation logic
- get_certificates_summary() - Statistics
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from domain.models import Certificate
from domain.rules import guess_certificate_type as _guess_certificate_type
from domain.validators import validate_file_path
from domain.exceptions import ValidationError

logger = logging.getLogger(__name__)


# Re-export from domain.rules for convenience
def guess_certificate_type(filename: str) -> str:
    """
    Guess certificate type from filename.

    Uses keyword matching against common certificate types.
    This is a convenience re-export from domain.rules.

    Args:
        filename: Certificate filename (e.g., "materialintyg_2024.pdf")

    Returns:
        Certificate type name (e.g., "Material Certificate")
        Defaults to "Other Documents" if no match found

    Example:
        >>> guess_certificate_type("materialintyg_2024.pdf")
        'Material Certificate'
        >>> guess_certificate_type("svets_protokoll.pdf")
        'Welding Log'
        >>> guess_certificate_type("unknown.pdf")
        'Other Documents'
    """
    return _guess_certificate_type(filename)


def validate_certificate_file(file_path: Path) -> Path:
    """
    Validate certificate file exists and is a PDF.

    Args:
        file_path: Path to certificate file

    Returns:
        Validated Path object

    Raises:
        ValidationError: If file is invalid
    """
    # Validate file exists
    validated_path = validate_file_path(
        file_path,
        must_exist=True,
        allowed_extensions=[".pdf"]
    )

    logger.debug(f"Validated certificate file: {validated_path}")
    return validated_path


def create_certificate_dict(
    project_id: int,
    article_number: str,
    file_path: Path,
    certificate_type: Optional[str] = None,
    original_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create certificate dictionary from file.

    PURE FUNCTION - no database access.
    Returns dict that can be saved separately.

    Args:
        project_id: Project ID
        article_number: Article number
        file_path: Path to certificate file
        certificate_type: Certificate type (auto-detected if None)
        original_name: Original filename (uses file_path.name if None)

    Returns:
        Dict with certificate data

    Raises:
        ValidationError: If file is invalid
    """
    # Validate file
    validated_path = validate_certificate_file(file_path)

    # Auto-detect type if not provided
    if certificate_type is None:
        certificate_type = guess_certificate_type(validated_path.name)

    # Use original name or current filename
    if original_name is None:
        original_name = validated_path.name

    logger.info(
        f"Created certificate: {article_number} → {certificate_type} "
        f"({original_name})"
    )

    return {
        "project_id": project_id,
        "article_number": article_number,
        "file_path": str(validated_path),
        "certificate_type": certificate_type,
        "original_filename": original_name,
    }


def get_certificates_summary(certificates: List[Certificate]) -> Dict[str, Any]:
    """
    Get summary statistics for certificates.

    Args:
        certificates: List of Certificate objects

    Returns:
        Dict with summary statistics

    Example:
        >>> certs = [Certificate(...), Certificate(...)]
        >>> summary = get_certificates_summary(certs)
        >>> print(f"Total: {summary['total_count']}")
    """
    total = len(certificates)

    # Group by type
    by_type = {}
    for cert in certificates:
        cert_type = cert.certificate_type
        by_type[cert_type] = by_type.get(cert_type, 0) + 1

    # Group by article
    by_article = {}
    for cert in certificates:
        article = cert.article_number
        by_article[article] = by_article.get(article, 0) + 1

    return {
        "total_count": total,
        "by_type": by_type,
        "by_article": by_article,
        "unique_types": len(by_type),
        "unique_articles": len(by_article),
    }


def get_certificates_for_article(
    certificates: List[Certificate],
    article_number: str,
) -> List[Certificate]:
    """
    Get all certificates for a specific article.

    Args:
        certificates: List of Certificate objects
        article_number: Article number to filter by

    Returns:
        List of Certificate objects for the article
    """
    return [
        cert for cert in certificates
        if cert.article_number == article_number
    ]


def get_certificates_by_type(
    certificates: List[Certificate],
    certificate_type: str,
) -> List[Certificate]:
    """
    Get all certificates of a specific type.

    Args:
        certificates: List of Certificate objects
        certificate_type: Certificate type to filter by

    Returns:
        List of Certificate objects of the type
    """
    return [
        cert for cert in certificates
        if cert.certificate_type == certificate_type
    ]


def get_articles_with_certificates(
    certificates: List[Certificate],
) -> List[str]:
    """
    Get list of unique article numbers that have certificates.

    Args:
        certificates: List of Certificate objects

    Returns:
        Sorted list of unique article numbers
    """
    article_numbers = {cert.article_number for cert in certificates}
    return sorted(article_numbers)


def get_articles_without_certificates(
    all_articles: List[str],
    certificates: List[Certificate],
) -> List[str]:
    """
    Get list of articles that don't have certificates.

    Args:
        all_articles: List of all article numbers
        certificates: List of Certificate objects

    Returns:
        Sorted list of article numbers without certificates
    """
    articles_with_certs = set(get_articles_with_certificates(certificates))
    articles_without = [
        article for article in all_articles
        if article not in articles_with_certs
    ]
    return sorted(articles_without)
