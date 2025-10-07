"""
Update Operations for Tobbes v2.

Project update operations - compare and apply changes.
Pure functions with dependency injection - no global state.

According to plan (Week 2, Day 10):
- compare_articles_for_update() - Compare current vs new data
- apply_updates() - Apply selected updates
- get_update_summary() - Statistics

NEW FEATURE: Update existing projects with new data from
nivålista or lagerlogg files.
"""

import logging
from typing import List, Dict, Any, Optional
from data.interface import DatabaseInterface
from domain.models import ArticleUpdate
from domain.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


def compare_articles_for_update(
    current_articles: List[Dict[str, Any]],
    new_data: List[Dict[str, Any]],
    update_type: str,
) -> List[ArticleUpdate]:
    """
    Compare current articles with new data to find updates.

    This function analyzes differences between existing project articles
    and newly imported data (from nivålista or lagerlogg).

    Args:
        current_articles: Current project articles (from get_articles_for_project)
        new_data: New data (from import_nivalista or import_lagerlogg)
        update_type: Either 'nivalista' or 'lagerlogg'

    Returns:
        List of ArticleUpdate objects representing potential changes

    Example:
        >>> current = get_articles_for_project(db, project_id=1)
        >>> new_data = import_lagerlogg("new_lagerlogg.xlsx")
        >>> updates = compare_articles_for_update(current, new_data, 'lagerlogg')
        >>> for update in updates:
        ...     print(f"{update.article_number}: {update.field_name} changed")
    """
    if update_type not in ['nivalista', 'lagerlogg']:
        raise ValidationError(
            f"Invalid update_type: {update_type}",
            details={"allowed": ['nivalista', 'lagerlogg']}
        )

    updates = []

    # Create lookup dict for current articles
    current_lookup = {
        article["article_number"]: article
        for article in current_articles
    }

    # Compare each new item with current
    for new_item in new_data:
        article_num = new_item.get("article_number")
        if not article_num:
            continue

        current = current_lookup.get(article_num)
        if not current:
            # Article doesn't exist in project - skip (not an update)
            continue

        # Check different fields based on update type
        if update_type == 'lagerlogg':
            # Compare charge_number (primary field in lagerlogg)
            new_charge = new_item.get("charge_number", "")
            current_charge = current.get("charge_number") or ""

            if new_charge and new_charge != current_charge:
                updates.append(ArticleUpdate(
                    article_number=article_num,
                    field_name="charge_number",
                    old_value=current_charge,
                    new_value=new_charge,
                    update_type=update_type,
                    affects_certificates=True,  # Charge change requires cert removal
                ))

        elif update_type == 'nivalista':
            # Compare quantity
            new_qty = new_item.get("quantity", 0.0)
            current_qty = current.get("quantity", 0.0)

            if new_qty != current_qty:
                updates.append(ArticleUpdate(
                    article_number=article_num,
                    field_name="quantity",
                    old_value=current_qty,
                    new_value=new_qty,
                    update_type=update_type,
                    affects_certificates=False,
                ))

            # Compare level
            new_level = new_item.get("level", "")
            current_level = current.get("level", "")

            if new_level != current_level:
                updates.append(ArticleUpdate(
                    article_number=article_num,
                    field_name="level",
                    old_value=current_level,
                    new_value=new_level,
                    update_type=update_type,
                    affects_certificates=False,
                ))

            # Compare description (update global)
            new_desc = new_item.get("description", "")
            current_desc = current.get("global_description", "")

            if new_desc and new_desc != current_desc:
                updates.append(ArticleUpdate(
                    article_number=article_num,
                    field_name="description",
                    old_value=current_desc,
                    new_value=new_desc,
                    update_type=update_type,
                    affects_certificates=False,
                ))

    logger.info(
        f"Found {len(updates)} potential updates from {update_type} "
        f"(comparing {len(new_data)} new items with {len(current_articles)} current)"
    )

    return updates


def apply_updates(
    db: DatabaseInterface,
    project_id: int,
    selected_updates: List[ArticleUpdate],
) -> Dict[str, Any]:
    """
    Apply selected updates to project articles.

    IMPORTANT: If charge_number is updated, associated certificates
    will be DELETED (new charge = new certificates needed).

    Args:
        db: Database instance (injected)
        project_id: Project ID
        selected_updates: List of ArticleUpdate objects to apply

    Returns:
        Dict with summary:
        - applied_count: Number of updates applied
        - certificates_removed: Number of certificates deleted
        - errors: List of error messages (if any)

    Raises:
        DatabaseError: If update fails

    Example:
        >>> updates = compare_articles_for_update(current, new_data, 'lagerlogg')
        >>> result = apply_updates(db, project_id=1, selected_updates=updates[:5])
        >>> print(f"Applied {result['applied_count']} updates")
    """
    applied_count = 0
    certificates_removed = 0
    errors = []

    try:
        for update in selected_updates:
            try:
                if update.field_name == "charge_number":
                    # Update charge in project_articles table
                    success = db.update_article_charge(
                        project_id=project_id,
                        article_number=update.article_number,
                        charge_number=update.new_value,
                    )

                    if success:
                        applied_count += 1

                        # Delete certificates if charge changed
                        if update.affects_certificates:
                            certs = db.get_certificates_for_article(
                                project_id=project_id,
                                article_number=update.article_number
                            )
                            for cert in certs:
                                db.delete_certificate(cert["id"])
                                certificates_removed += 1

                            logger.info(
                                f"Removed {len(certs)} certificates for "
                                f"{update.article_number} (charge changed)"
                            )

                elif update.field_name == "quantity":
                    # Update quantity in project_articles
                    success = db.update_article_quantity(
                        project_id=project_id,
                        article_number=update.article_number,
                        quantity=update.new_value,
                    )
                    if success:
                        applied_count += 1

                elif update.field_name == "level":
                    # Update level in project_articles
                    success = db.update_article_level(
                        project_id=project_id,
                        article_number=update.article_number,
                        level=update.new_value,
                    )
                    if success:
                        applied_count += 1

                elif update.field_name == "description":
                    # Update global description (affects all projects)
                    existing = db.get_global_article(update.article_number)
                    if existing:
                        # Preserve existing notes
                        db.save_global_article(
                            article_number=update.article_number,
                            description=update.new_value,
                            notes=existing.get("notes", ""),
                        )
                        applied_count += 1

            except Exception as e:
                error_msg = f"Failed to apply update for {update.article_number}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)

        logger.info(
            f"Applied {applied_count}/{len(selected_updates)} updates "
            f"(removed {certificates_removed} certificates)"
        )

        return {
            "applied_count": applied_count,
            "certificates_removed": certificates_removed,
            "errors": errors,
        }

    except Exception as e:
        logger.exception("Error during apply_updates")
        raise DatabaseError(
            f"Failed to apply updates: {e}",
            details={
                "project_id": project_id,
                "update_count": len(selected_updates)
            }
        )


def get_update_summary(updates: List[ArticleUpdate]) -> Dict[str, Any]:
    """
    Get summary statistics for updates.

    Args:
        updates: List of ArticleUpdate objects

    Returns:
        Dict with summary statistics

    Example:
        >>> updates = compare_articles_for_update(current, new_data, 'lagerlogg')
        >>> summary = get_update_summary(updates)
        >>> print(f"Total: {summary['total_count']}")
        >>> print(f"Affects certificates: {summary['affects_certificates_count']}")
    """
    total = len(updates)
    affects_certs = sum(1 for u in updates if u.affects_certificates)

    # Group by field
    by_field = {}
    for update in updates:
        field = update.field_name
        by_field[field] = by_field.get(field, 0) + 1

    # Group by article
    by_article = {}
    for update in updates:
        article = update.article_number
        by_article[article] = by_article.get(article, 0) + 1

    return {
        "total_count": total,
        "affects_certificates_count": affects_certs,
        "by_field": by_field,
        "by_article": by_article,
        "unique_articles": len(by_article),
    }


def filter_updates_by_field(
    updates: List[ArticleUpdate],
    field_name: str,
) -> List[ArticleUpdate]:
    """
    Filter updates to only include specific field.

    Args:
        updates: List of ArticleUpdate objects
        field_name: Field to filter by (e.g., "charge_number")

    Returns:
        Filtered list of updates

    Example:
        >>> charge_updates = filter_updates_by_field(updates, "charge_number")
    """
    return [u for u in updates if u.field_name == field_name]


def get_articles_with_updates(
    updates: List[ArticleUpdate],
) -> List[str]:
    """
    Get list of unique article numbers that have updates.

    Args:
        updates: List of ArticleUpdate objects

    Returns:
        Sorted list of unique article numbers

    Example:
        >>> articles = get_articles_with_updates(updates)
        >>> print(f"Updates affect {len(articles)} articles")
    """
    article_numbers = {update.article_number for update in updates}
    return sorted(article_numbers)
