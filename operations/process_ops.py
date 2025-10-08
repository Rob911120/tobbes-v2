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
    get_available_charges,
    get_available_batches,
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
    Match a single article with inventory charges and batches.

    Helper function for match_articles_with_charges.

    NO auto-match when multiple values! User must always choose.
    Auto-match ONLY when exactly 1 charge or 1 batch available.

    Args:
        article: Article to match
        inventory_items: Available inventory items
        auto_match_single: Auto-select if only one charge/batch available

    Returns:
        MatchResult with available charges/batches and selected values (if auto-matched)
    """
    # Get all available charges and batches for this article
    available_charges = get_available_charges(article, inventory_items)
    available_batches = get_available_batches(article, inventory_items)

    # Auto-match logic: ONLY if exactly 1 option
    selected_charge = None
    selected_batch = None
    auto_matched = False

    if len(available_charges) == 1 and auto_match_single:
        # Only one charge available - auto-select it
        selected_charge = available_charges[0]
        auto_matched = True
        logger.debug(f"Auto-matched charge {article.article_number} → {selected_charge}")

    if len(available_batches) == 1 and auto_match_single:
        # Only one batch available - auto-select it
        selected_batch = available_batches[0]
        auto_matched = True
        logger.debug(f"Auto-matched batch {article.article_number} → {selected_batch}")

    # Multiple charges/batches → Yellow field, user MUST choose
    if len(available_charges) > 1:
        logger.debug(
            f"{article.article_number} has {len(available_charges)} charges - "
            f"user must select (yellow field)"
        )

    if len(available_batches) > 1:
        logger.debug(
            f"{article.article_number} has {len(available_batches)} batches - "
            f"user must select (yellow field)"
        )

    # Create match result
    result = MatchResult(
        article=article,
        available_charges=available_charges,
        available_batches=available_batches,
        selected_charge=selected_charge,
        selected_batch=selected_batch,
        auto_matched=auto_matched,
    )

    return result


def apply_charge_selection(
    match_result: MatchResult,
    selected_charge: str = None,
    selected_batch: str = None,
) -> MatchResult:
    """
    Apply manual charge and/or batch selection to a match result.

    Used when user manually selects a charge/batch from available options.

    Args:
        match_result: Original match result
        selected_charge: Charge number selected by user (optional)
        selected_batch: Batch number selected by user (optional)

    Returns:
        Updated MatchResult with selected charge/batch

    Raises:
        ValueError: If selected value is not in available options
    """
    if selected_charge is not None:
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
            f"Applied manual charge selection: {match_result.article.article_number} → {selected_charge}"
        )

    if selected_batch is not None:
        if selected_batch not in match_result.available_batches:
            raise ValueError(
                f"Selected batch '{selected_batch}' not in available batches: "
                f"{match_result.available_batches}"
            )

        # Update article with selected batch
        match_result.article.batch_number = selected_batch
        match_result.selected_batch = selected_batch
        match_result.auto_matched = False  # This was manual selection

        logger.info(
            f"Applied manual batch selection: {match_result.article.article_number} → {selected_batch}"
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


def compare_import_with_existing(
    existing_articles: List[Dict[str, Any]],
    new_articles: List[Dict[str, Any]],
    new_inventory: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compare existing project articles with new import data.

    Returns a unified diff showing what will change if import is applied.
    Used for both first-time import (all "new") and re-import (diff).

    **Smart Re-import Logic:**
    - Lagerlogg: Update charge/batch ONLY on non-verified articles
    - Nivålista: Detect structure changes (levels, removed articles)

    Args:
        existing_articles: Current articles in project (from DB)
        new_articles: Articles from new nivålista file
        new_inventory: Inventory items from new lagerlogg file

    Returns:
        Dict with diff structure:
        {
            'new': [...],           # New articles (green)
            'updated': [{           # Updated articles (yellow if not verified, gray if verified)
                'article': {...},
                'changes': {
                    'charge': {'old': 'C1', 'new': 'C2'},
                    'batch': {'old': 'B1', 'new': 'B2'},
                    'level': {'old': '1', 'new': '2'},
                    'quantity': {'old': 10, 'new': 20}
                },
                'is_verified': True/False,
                'can_update': True/False  # False if verified
            }],
            'removed': [...],       # Articles removed from nivålista (red)
            'unchanged': [...]      # No changes
        }

    Example:
        >>> existing = db.get_articles_for_project(1)
        >>> new_articles = import_nivalista("updated_nivalista.xlsx")
        >>> new_inventory = import_lagerlogg("updated_lagerlogg.xlsx")
        >>> diff = compare_import_with_existing(existing, new_articles, new_inventory)
        >>> print(f"New: {len(diff['new'])}, Updated: {len(diff['updated'])}")
    """
    # If no existing articles, everything is "new"
    if not existing_articles:
        logger.info("First import - all articles are new")
        return {
            'new': new_articles,
            'updated': [],
            'removed': [],
            'unchanged': []
        }

    # Create lookups
    existing_lookup = {
        a['article_number']: a for a in existing_articles
    }
    new_lookup = {
        a['article_number']: a for a in new_articles
    }

    # Match new inventory to get updated charges/batches
    inventory_models = [
        InventoryItem(
            project_id=0,
            article_number=i["article_number"],
            charge_number=i["charge_number"],
            quantity=i.get("quantity", 0.0),
            batch_id=i.get("batch_id"),
            location=i.get("location"),
            received_date=i.get("received_date"),
        )
        for i in new_inventory
    ]

    new_articles_list = []
    updated_articles = []
    unchanged_articles = []
    removed_articles = []

    # Check each article from new nivålista
    for article_num, new_article in new_lookup.items():
        existing = existing_lookup.get(article_num)

        if not existing:
            # NEW article - not in existing project
            # Match with inventory to get charge/batch
            article_model = Article(
                project_id=0,
                article_number=article_num,
                description=new_article.get('description', ''),
                quantity=new_article.get('quantity', 0.0),
                level=new_article.get('level', ''),
            )

            available_charges = get_available_charges(article_model, inventory_models)
            available_batches = get_available_batches(article_model, inventory_models)

            # Auto-select if only 1 option
            if len(available_charges) == 1:
                new_article['charge_number'] = available_charges[0]
            if len(available_batches) == 1:
                new_article['batch_number'] = available_batches[0]

            new_articles_list.append(new_article)
            continue

        # Article exists - check for changes
        changes = {}

        # Compare nivålista fields (level, quantity, description)
        if new_article.get('level') != existing.get('level'):
            changes['level'] = {
                'old': existing.get('level', ''),
                'new': new_article.get('level', '')
            }

        if new_article.get('quantity') != existing.get('quantity'):
            changes['quantity'] = {
                'old': existing.get('quantity', 0.0),
                'new': new_article.get('quantity', 0.0)
            }

        # Compare charge/batch from new inventory
        # Get new charge/batch for this article
        article_model = Article(
            project_id=0,
            article_number=article_num,
            description=new_article.get('description', ''),
            quantity=new_article.get('quantity', 0.0),
            level=new_article.get('level', ''),
        )

        available_charges = get_available_charges(article_model, inventory_models)
        available_batches = get_available_batches(article_model, inventory_models)

        # Auto-select if only 1 option
        new_charge = available_charges[0] if len(available_charges) == 1 else None
        new_batch = available_batches[0] if len(available_batches) == 1 else None

        # FIX: Add charge/batch to article dict so they're saved correctly
        if new_charge:
            new_article['charge_number'] = new_charge
        if new_batch:
            new_article['batch_number'] = new_batch

        if new_charge and new_charge != existing.get('charge_number'):
            changes['charge'] = {
                'old': existing.get('charge_number', ''),
                'new': new_charge
            }

        if new_batch and new_batch != existing.get('batch_number'):
            changes['batch'] = {
                'old': existing.get('batch_number', ''),
                'new': new_batch
            }

        # Determine if article can be updated
        is_verified = existing.get('verified', False)
        can_update = not is_verified  # Can only update non-verified articles

        if changes:
            # Article has changes
            updated_articles.append({
                'article': new_article,
                'article_number': article_num,
                'changes': changes,
                'is_verified': is_verified,
                'can_update': can_update,
                'available_charges': available_charges,
                'available_batches': available_batches,
            })
        else:
            # No changes
            unchanged_articles.append(new_article)

    # Find removed articles (in existing but not in new nivålista)
    for article_num, existing_article in existing_lookup.items():
        if article_num not in new_lookup:
            removed_articles.append(existing_article)

    logger.info(
        f"Diff: {len(new_articles_list)} new, {len(updated_articles)} updated, "
        f"{len(removed_articles)} removed, {len(unchanged_articles)} unchanged"
    )

    return {
        'new': new_articles_list,
        'updated': updated_articles,
        'removed': removed_articles,
        'unchanged': unchanged_articles,
    }
