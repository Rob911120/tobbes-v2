"""
Certificate Scanner Service for Tobbes v2.

Provides fuzzy matching and auto-suggestion of certificate files
based on article number, charge number, and other criteria.
"""

import logging
from pathlib import Path
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

# Try to import rapidfuzz (will be added to dependencies)
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    logger.warning("rapidfuzz not available - fuzzy matching will use basic scoring")
    RAPIDFUZZ_AVAILABLE = False


def scan_directory(directory: Path, recursive: bool = True) -> List[Path]:
    """
    Scan directory for PDF files.

    Args:
        directory: Directory to scan
        recursive: If True, scan subdirectories recursively

    Returns:
        List of Path objects for found PDF files
    """
    if not directory.exists() or not directory.is_dir():
        logger.warning(f"Directory not found or not accessible: {directory}")
        return []

    pdf_files = []

    try:
        if recursive:
            pdf_files = list(directory.rglob("*.pdf"))
        else:
            pdf_files = list(directory.glob("*.pdf"))

        logger.info(f"Found {len(pdf_files)} PDF files in {directory}")
        return pdf_files

    except Exception as e:
        logger.exception(f"Error scanning directory {directory}: {e}")
        return []


def calculate_match_score(
    filename: str,
    article_number: str,
    charge_number: Optional[str] = None,
) -> float:
    """
    Calculate fuzzy match score for a certificate filename.

    Scoring system:
    - Exact substring match on article_number: +50 points
    - Exact substring match on charge_number: +40 points
    - Fuzzy match on article_number (rapidfuzz): 0-30 points
    - Fuzzy match on charge_number (rapidfuzz): 0-20 points

    Total: 0-100 points

    Args:
        filename: Certificate filename (without path)
        article_number: Article number to match
        charge_number: Optional charge number to match

    Returns:
        Match score (0-100)
    """
    score = 0.0
    filename_lower = filename.lower()
    article_lower = article_number.lower()

    # Exact substring match on article number → +50
    if article_lower in filename_lower:
        score += 50.0
        logger.debug(f"Exact article match: {filename} contains {article_number}")
    elif RAPIDFUZZ_AVAILABLE:
        # Fuzzy match on article number → 0-30
        fuzzy_score = fuzz.partial_ratio(article_lower, filename_lower)
        fuzzy_points = (fuzzy_score / 100) * 30
        score += fuzzy_points
        logger.debug(f"Fuzzy article match: {filename} ~ {article_number} = {fuzzy_score}%")

    # Charge number matching (if provided)
    if charge_number:
        charge_lower = charge_number.lower()

        # Exact substring match on charge → +40
        if charge_lower in filename_lower:
            score += 40.0
            logger.debug(f"Exact charge match: {filename} contains {charge_number}")
        elif RAPIDFUZZ_AVAILABLE:
            # Fuzzy match on charge → 0-20
            fuzzy_score = fuzz.partial_ratio(charge_lower, filename_lower)
            fuzzy_points = (fuzzy_score / 100) * 20
            score += fuzzy_points
            logger.debug(f"Fuzzy charge match: {filename} ~ {charge_number} = {fuzzy_score}%")

    return round(score, 1)


def suggest_certificates(
    search_path: Path,
    article_number: str,
    charge_number: Optional[str] = None,
    min_score: float = 70.0,
    recursive: bool = True,
) -> List[Tuple[Path, float]]:
    """
    Suggest certificate files for an article based on fuzzy matching.

    Args:
        search_path: Directory to search in
        article_number: Article number
        charge_number: Optional charge number
        min_score: Minimum match score (default 70.0)
        recursive: Search subdirectories recursively (default True)

    Returns:
        List of (file_path, score) tuples, sorted by score (highest first)

    Example:
        >>> suggestions = suggest_certificates(
        ...     Path("/certs/material"),
        ...     "ART-123",
        ...     "C-456"
        ... )
        >>> for path, score in suggestions:
        ...     print(f"{path.name}: {score}%")
    """
    if not search_path.exists():
        logger.warning(f"Search path does not exist: {search_path}")
        return []

    # Scan directory for PDFs
    pdf_files = scan_directory(search_path, recursive=recursive)

    if not pdf_files:
        logger.info(f"No PDF files found in {search_path}")
        return []

    # Score each file
    scored_files = []
    for pdf_file in pdf_files:
        score = calculate_match_score(
            filename=pdf_file.name,
            article_number=article_number,
            charge_number=charge_number,
        )

        if score >= min_score:
            scored_files.append((pdf_file, score))
            logger.debug(f"Match: {pdf_file.name} → {score}%")

    # Sort by score (highest first)
    scored_files.sort(key=lambda x: x[1], reverse=True)

    logger.info(
        f"Found {len(scored_files)} matching certificates for {article_number} "
        f"(charge: {charge_number or 'N/A'})"
    )

    return scored_files


def get_best_match(
    search_path: Path,
    article_number: str,
    charge_number: Optional[str] = None,
    auto_select_threshold: float = 85.0,
) -> Optional[Path]:
    """
    Get best matching certificate file (auto-select if score is high enough).

    Args:
        search_path: Directory to search in
        article_number: Article number
        charge_number: Optional charge number
        auto_select_threshold: Minimum score for auto-selection (default 85.0)

    Returns:
        Path to best match if score >= threshold, otherwise None

    Example:
        >>> best = get_best_match(Path("/certs"), "ART-123", "C-456")
        >>> if best:
        ...     print(f"Auto-selected: {best.name}")
    """
    suggestions = suggest_certificates(
        search_path=search_path,
        article_number=article_number,
        charge_number=charge_number,
        min_score=70.0,  # Use lower threshold for search
    )

    if not suggestions:
        return None

    # Get highest scoring match
    best_file, best_score = suggestions[0]

    if best_score >= auto_select_threshold:
        logger.info(f"Auto-selected '{best_file.name}' (score: {best_score}%)")
        return best_file
    else:
        logger.info(
            f"Best match '{best_file.name}' has score {best_score}% "
            f"(threshold: {auto_select_threshold}%)"
        )
        return None
