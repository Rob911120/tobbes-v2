"""
Hierarchy Operations for Tobbes v2.

Pure functions for building hierarchical relationships from nivålista level column.
Supports up to 15 levels of hierarchy.

According to plan:
- build_hierarchy() - Build parent/child relationships from level strings
- parse_level() - Parse level string to depth and path
- find_parent_article() - Find parent based on level stack
- validate_hierarchy() - Validate that hierarchy is well-formed
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

from domain.exceptions import ImportValidationError, ValidationError

logger = logging.getLogger(__name__)

# Maximum hierarchy depth
MAX_HIERARCHY_DEPTH = 15


def parse_level(level_str: str) -> Tuple[int, List[int]]:
    """
    Parse level string to depth and path.

    Examples:
        "1" → (1, [1])
        "1.2" → (2, [1, 2])
        "1.2.3.4.5" → (5, [1, 2, 3, 4, 5])

    Args:
        level_str: Level string (e.g., "1", "1.2", "1.2.3")

    Returns:
        Tuple of (depth, path) where:
        - depth: Integer depth (1-15)
        - path: List of integers representing the path

    Raises:
        ValidationError: If level format is invalid or too deep

    Example:
        >>> depth, path = parse_level("1.2.3")
        >>> depth
        3
        >>> path
        [1, 2, 3]
    """
    if not level_str or not level_str.strip():
        raise ValidationError(
            "Nivå-sträng är tom",
            details={"level": level_str}
        )

    # Split by dot and parse integers
    parts = level_str.strip().split(".")

    try:
        path = [int(part) for part in parts]
    except ValueError as e:
        raise ValidationError(
            f"Ogiltig nivå-format: '{level_str}' (måste vara numeriskt, t.ex. '1.2.3')",
            details={"level": level_str, "error": str(e)}
        )

    depth = len(path)

    # Validate depth
    if depth > MAX_HIERARCHY_DEPTH:
        raise ValidationError(
            f"Hierarkin är för djup: {depth} nivåer (max {MAX_HIERARCHY_DEPTH})",
            details={"level": level_str, "depth": depth}
        )

    # Validate all parts are non-negative (allow 0 for special/spare parts)
    if any(part < 0 for part in path):
        raise ValidationError(
            f"Nivå-siffror kan inte vara negativa: '{level_str}'",
            details={"level": level_str, "path": path}
        )

    return depth, path


def find_parent_article(
    level_path: List[int],
    stack: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Find parent article based on level path and article stack.

    Logic:
    - Level 0 or 1 (top-level) → No parent (None)
    - Level N → Parent is nearest article at level N-1

    Args:
        level_path: Current level path (e.g., [1, 2, 3] for "1.2.3" or [0] for "0")
        stack: Stack of articles at each depth (index 0 = depth 1, etc.)

    Returns:
        Article number of parent, or None for top-level articles

    Example:
        >>> stack = [
        ...     {"article_number": "MOTOR-001", "level": "1"},
        ...     {"article_number": "1.1", "level": "1.1"},
        ... ]
        >>> find_parent_article([1, 2, 1], stack)
        "1.1"  # Parent is at depth 2 (second element in stack)
    """
    depth = len(level_path)

    # Top-level articles (depth 1) have no parent
    if depth == 1:
        return None  # Level "1" = top-level, no parent

    # Parent is at depth-1 (e.g., depth 3 → parent at depth 2)
    parent_depth = depth - 1

    # Stack is 0-indexed, so parent_depth-1 is the index
    parent_index = parent_depth - 1

    if parent_index < 0 or parent_index >= len(stack):
        # No parent found in stack (shouldn't happen with valid hierarchy)
        logger.warning(
            f"No parent found for level {level_path} (depth {depth}). "
            f"Stack size: {len(stack)}"
        )
        return None

    parent_article = stack[parent_index]
    return parent_article["article_number"]


def validate_hierarchy(articles: List[Dict[str, Any]]) -> None:
    """
    Validate that hierarchy is well-formed.

    Checks:
    - All articles have 'level' field
    - Level format is valid (numeric dot-notation)
    - No skipped levels (e.g., 1 → 3 without 2)
    - Max 15 levels

    Args:
        articles: List of article dictionaries

    Raises:
        ImportValidationError: If hierarchy is invalid

    Example:
        >>> articles = [
        ...     {"article_number": "A", "level": "1"},
        ...     {"article_number": "B", "level": "1.1"},
        ... ]
        >>> validate_hierarchy(articles)  # OK
    """
    if not articles:
        return

    # Check all articles have level
    for idx, article in enumerate(articles):
        if "level" not in article or not article["level"]:
            raise ImportValidationError(
                f"Artikel på rad {idx + 1} saknar 'level'-fält",
                details={"article": article.get("article_number", "(okänd)"), "row": idx + 1}
            )

    # Validate each level format
    prev_depth = 0
    for idx, article in enumerate(articles):
        level_str = article["level"]

        try:
            depth, path = parse_level(level_str)
        except ValidationError as e:
            raise ImportValidationError(
                f"Ogiltig nivå på rad {idx + 1}: {e.message}",
                details={
                    "article": article.get("article_number", "(okänd)"),
                    "level": level_str,
                    "row": idx + 1
                }
            )

        # Check for skipped levels (e.g., depth 1 → 3 without 2)
        # Allow same depth or one level deeper, but not jumps
        if depth > prev_depth + 1:
            raise ImportValidationError(
                f"Hoppad nivå på rad {idx + 1}: från nivå {prev_depth} till {depth} "
                f"(måste gå via nivå {prev_depth + 1})",
                details={
                    "article": article.get("article_number", "(okänd)"),
                    "level": level_str,
                    "previous_depth": prev_depth,
                    "current_depth": depth,
                    "row": idx + 1
                }
            )

        prev_depth = depth

    logger.info(f"Hierarchy validation passed for {len(articles)} articles")


def build_hierarchy(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build hierarchical relationships from level column.

    This function:
    1. Validates hierarchy structure
    2. Parses level strings to depths
    3. Calculates parent_article for each article
    4. Preserves sort_order from Excel import order

    Args:
        articles: List of article dictionaries with 'level' field

    Returns:
        Articles with added fields:
        - parent_article: Article number of parent (or None for top-level)
        - level_depth: Integer depth (1-15)
        - sort_order: Original row order (preserved)

    Raises:
        ImportValidationError: If hierarchy is invalid

    Example:
        >>> articles = [
        ...     {"article_number": "MOTOR-001", "level": "1"},
        ...     {"article_number": "1.1", "level": "2"},
        ...     {"article_number": "1.2", "level": "2"},
        ...     {"article_number": "1.2.1", "level": "3"},
        ... ]
        >>> result = build_hierarchy(articles)
        >>> result[0]["parent_article"]
        None
        >>> result[1]["parent_article"]
        'MOTOR-001'
        >>> result[3]["parent_article"]
        '1.2'
    """
    logger.info(f"Building hierarchy for {len(articles)} articles")

    # Validate hierarchy first
    validate_hierarchy(articles)

    result = []
    stack = []  # Stack of articles at each depth (index 0 = depth 1, index 1 = depth 2, etc.)

    for idx, article in enumerate(articles):
        level_str = article["level"]
        depth, level_path = parse_level(level_str)

        # Find parent based on current stack
        parent = find_parent_article(level_path, stack)

        # Add hierarchy fields to article
        article["parent_article"] = parent
        article["level_depth"] = depth

        # Preserve sort_order from Excel import (or use index if not set)
        if "sort_order" not in article:
            article["sort_order"] = idx

        # Update stack: keep only parents at lower depths
        # For depth 3, keep stack[0] (depth 1) and stack[1] (depth 2), discard rest
        stack = stack[:depth - 1] + [article]

        result.append(article)

        logger.debug(
            f"Article {article['article_number']}: "
            f"level={level_str}, depth={depth}, parent={parent}"
        )

    logger.info(
        f"Hierarchy built successfully: "
        f"{len(result)} articles, max depth: {max(a['level_depth'] for a in result)}"
    )

    return result


def get_hierarchy_summary(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Get summary statistics for article hierarchy.

    Args:
        articles: List of articles with hierarchy fields

    Returns:
        Dict with summary:
        - total_articles: Total number of articles
        - max_depth: Maximum hierarchy depth
        - by_depth: Count of articles at each depth
        - top_level_count: Number of top-level articles

    Example:
        >>> articles = build_hierarchy(...)
        >>> summary = get_hierarchy_summary(articles)
        >>> print(f"Max depth: {summary['max_depth']}")
    """
    if not articles:
        return {
            "total_articles": 0,
            "max_depth": 0,
            "by_depth": {},
            "top_level_count": 0,
        }

    # Count articles by depth
    by_depth = {}
    for article in articles:
        depth = article.get("level_depth", 1)
        by_depth[depth] = by_depth.get(depth, 0) + 1

    max_depth = max(a.get("level_depth", 1) for a in articles)
    top_level = sum(1 for a in articles if a.get("level_depth", 1) == 1)

    return {
        "total_articles": len(articles),
        "max_depth": max_depth,
        "by_depth": by_depth,
        "top_level_count": top_level,
    }
