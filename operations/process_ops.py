"""
Process Operations for Tobbes v2.

Matching logic for articles and inventory charges.
Pure functions - no database access, no side effects.

According to plan (Week 2, Day 6-7):
- match_articles_with_charges() - Core matching logic
- _find_charge_for_article() - Helper for single article
"""

import logging
from typing import List, Dict, Any, Optional

from domain.models import Article, InventoryItem, MatchResult
from domain.rules import (
    find_best_charge_match,
    get_available_charges,
    calculate_match_statistics,
)

logger = logging.getLogger(__name__)


def match_articles_with_charges(
    articles: List[Dict[str, Any]],
    inventory_items: List[Dict[str, Any]],
    auto_match_single: bool = True,
) -> List[MatchResult]:
    """
    Match articles with available inventory charges.

    This is the CORE matching logic of the application.
    Returns MatchResult objects that show which articles have charges available.

    Matching logic:
    1. For each article, find all matching inventory items by article_number
    2. If multiple charges available: user must select manually
    3. If single charge available: auto-select (if auto_match_single=True)
    4. If no charges available: article remains unmatched

    Args:
        articles: List of article dicts (from import_nivalista)
        inventory_items: List of inventory item dicts (from import_lagerlogg)
        auto_match_single: If True, auto-select when only one charge available

    Returns:
        List of MatchResult objects with matching status

    Example:
        >>> articles = import_nivalista("nivalista.xlsx")
        >>> inventory = import_lagerlogg("lagerlogg.xlsx")
        >>> results = match_articles_with_charges(articles, inventory)
        >>> matched = [r for r in results if r.is_matched]
    """
    logger.info(f"Matching {len(articles)} articles with {len(inventory_items)} inventory items")

    # Convert dicts to model objects for domain logic
    article_models = [
        Article(
            project_id=0,  # Temporary, will be set when saving to DB
            article_number=a["article_number"],
            description=a.get("description", ""),
            quantity=a.get("quantity", 0.0),
            level=a.get("level", ""),
        )
        for a in articles
    ]

    inventory_models = [
        InventoryItem(
            project_id=0,  # Temporary
            article_number=i["article_number"],
            charge_number=i["charge_number"],
            quantity=i.get("quantity", 0.0),
            batch_id=i.get("batch_id"),
            location=i.get("location"),
            received_date=i.get("received_date"),
        )
        for i in inventory_items
    ]

    # Match each article
    match_results = []
    for article in article_models:
        result = _match_single_article(
            article=article,
            inventory_items=inventory_models,
            auto_match_single=auto_match_single,
        )
        match_results.append(result)

    # Log statistics
    stats = calculate_match_statistics([r.article for r in match_results if r.selected_charge])
    logger.info(
        f"Matching complete: {stats['matched']}/{stats['total']} matched "
        f"({stats['match_rate']:.1f}%)"
    )

    return match_results


def _match_single_article(
    article: Article,
    inventory_items: List[InventoryItem],
    auto_match_single: bool = True,
) -> MatchResult:
    """
    Match a single article with inventory charges.

    Helper function for match_articles_with_charges.

    Args:
        article: Article to match
        inventory_items: Available inventory items
        auto_match_single: Auto-select if only one charge available

    Returns:
        MatchResult with available charges and selected charge (if auto-matched)
    """
    # Get all available charges for this article
    available_charges = get_available_charges(article, inventory_items)

    # Determine if we should auto-match
    selected_charge = None
    auto_matched = False

    if len(available_charges) == 1 and auto_match_single:
        # Only one charge available - auto-select it
        selected_charge = available_charges[0]
        auto_matched = True
        logger.debug(f"Auto-matched {article.article_number} → {selected_charge}")

    elif len(available_charges) > 1:
        # Multiple charges - try to find best match
        best_charge = find_best_charge_match(article, inventory_items)
        if best_charge and auto_match_single:
            selected_charge = best_charge
            auto_matched = True
            logger.debug(
                f"Auto-matched {article.article_number} → {selected_charge} "
                f"(best of {len(available_charges)} options)"
            )

    # Create match result
    result = MatchResult(
        article=article,
        available_charges=available_charges,
        selected_charge=selected_charge,
        auto_matched=auto_matched,
    )

    return result


def apply_charge_selection(
    match_result: MatchResult,
    selected_charge: str,
) -> MatchResult:
    """
    Apply manual charge selection to a match result.

    Used when user manually selects a charge from available options.

    Args:
        match_result: Original match result
        selected_charge: Charge number selected by user

    Returns:
        Updated MatchResult with selected charge

    Raises:
        ValueError: If selected charge is not in available charges
    """
    if selected_charge not in match_result.available_charges:
        raise ValueError(
            f"Selected charge '{selected_charge}' not in available charges: "
            f"{match_result.available_charges}"
        )

    # Update article with selected charge
    match_result.article.charge_number = selected_charge
    match_result.selected_charge = selected_charge
    match_result.auto_matched = False  # This was manual selection

    logger.info(
        f"Applied manual selection: {match_result.article.article_number} → {selected_charge}"
    )

    return match_result


def get_matching_summary(match_results: List[MatchResult]) -> Dict[str, Any]:
    """
    Get summary statistics for matching results.

    Useful for displaying to user after matching.

    Args:
        match_results: List of MatchResult objects

    Returns:
        Dict with summary statistics

    Example:
        >>> results = match_articles_with_charges(articles, inventory)
        >>> summary = get_matching_summary(results)
        >>> print(f"Matched: {summary['matched_count']}/{summary['total_count']}")
    """
    total = len(match_results)
    matched = sum(1 for r in match_results if r.is_matched)
    auto_matched = sum(1 for r in match_results if r.auto_matched)
    needs_manual = sum(1 for r in match_results if r.needs_manual_selection)
    no_charges = sum(1 for r in match_results if len(r.available_charges) == 0)

    return {
        "total_count": total,
        "matched_count": matched,
        "auto_matched_count": auto_matched,
        "needs_manual_count": needs_manual,
        "no_charges_count": no_charges,
        "match_rate": (matched / total * 100) if total > 0 else 0.0,
    }


def get_unmatched_articles(match_results: List[MatchResult]) -> List[Article]:
    """
    Get list of articles that couldn't be matched.

    Useful for displaying unmatched articles to user.

    Args:
        match_results: List of MatchResult objects

    Returns:
        List of unmatched Article objects
    """
    return [r.article for r in match_results if not r.is_matched]


def get_articles_needing_manual_selection(match_results: List[MatchResult]) -> List[MatchResult]:
    """
    Get match results that need manual charge selection.

    These are articles with multiple charges available.

    Args:
        match_results: List of MatchResult objects

    Returns:
        List of MatchResult objects needing manual selection
    """
    return [r for r in match_results if r.needs_manual_selection]
