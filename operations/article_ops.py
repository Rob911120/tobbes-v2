"""
Article Operations for Tobbes v2.

Global article notes management operations.
Pure functions with dependency injection - no global state.

According to plan (Week 2, Day 8-9):
- update_article_notes() - Update global notes (shared across ALL projects)
- get_articles_for_project() - Get articles WITH global data
- get_notes_history() - Get audit log for notes changes

NEW FEATURE: Global notes that are shared across all projects where
the article appears.
"""

import logging
from typing import List, Dict, Any
from data.interface import DatabaseInterface
from domain.validators import validate_article_number
from domain.exceptions import DatabaseError, ValidationError

logger = logging.getLogger(__name__)


def update_article_notes(
    db: DatabaseInterface,
    article_number: str,
    notes: str,
    changed_by: str = "user"
) -> bool:
    """
    Update article notes GLOBALLY.

    This updates the notes field in global_articles table, which means
    the notes will be visible in ALL projects where this article appears.

    An audit log entry is automatically created via database trigger.

    Args:
        db: Database instance (injected)
        article_number: Article number to update notes for
        notes: New notes text (can be empty string to clear notes)
        changed_by: Who made the change (for audit log)

    Returns:
        True if update succeeded

    Raises:
        ValidationError: If article_number is invalid
        DatabaseError: If update fails

    Example:
        >>> db = create_database("sqlite", ":memory:")
        >>> update_article_notes(db, "ART-001", "Kräver extra kontroll", "user1")
        True
    """
    # Validate input
    try:
        validated_article = validate_article_number(article_number)
    except ValidationError as e:
        logger.error(f"Invalid article number: {article_number}")
        raise

    # Delegate to database
    try:
        success = db.update_article_notes(
            article_number=validated_article,
            notes=notes,
            changed_by=changed_by
        )

        if success:
            logger.info(
                f"Updated notes for {validated_article} (by {changed_by})"
            )
        else:
            logger.warning(f"Failed to update notes for {validated_article}")

        return success

    except Exception as e:
        logger.exception(f"Error updating notes for {validated_article}")
        raise DatabaseError(
            f"Failed to update article notes: {e}",
            details={
                "article_number": validated_article,
                "changed_by": changed_by
            }
        )


def get_articles_for_project(
    db: DatabaseInterface,
    project_id: int
) -> List[Dict[str, Any]]:
    """
    Get all articles for a project WITH global data.

    This fetches project articles and populates them with data from
    global_articles (description, notes, etc.).

    Args:
        db: Database instance (injected)
        project_id: Project ID

    Returns:
        List of article dicts with global data populated

    Raises:
        DatabaseError: If query fails

    Example:
        >>> db = create_database("sqlite", ":memory:")
        >>> articles = get_articles_for_project(db, project_id=1)
        >>> for article in articles:
        ...     print(f"{article['article_number']}: {article['notes']}")
    """
    try:
        articles = db.get_project_articles_with_global_data(project_id)
        logger.debug(
            f"Loaded {len(articles)} articles for project {project_id}"
        )
        return articles

    except Exception as e:
        logger.exception(f"Error loading articles for project {project_id}")
        raise DatabaseError(
            f"Failed to load articles: {e}",
            details={"project_id": project_id}
        )


def get_notes_history(
    db: DatabaseInterface,
    article_number: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get change history for article notes.

    Returns audit log entries showing who changed notes and when.

    Args:
        db: Database instance (injected)
        article_number: Article number
        limit: Max number of history entries to return (default 10)

    Returns:
        List of history dicts with keys:
        - changed_at: Timestamp
        - changed_by: Who made the change
        - old_notes: Previous notes value
        - new_notes: New notes value

    Raises:
        ValidationError: If article_number is invalid
        DatabaseError: If query fails

    Example:
        >>> history = get_notes_history(db, "ART-001", limit=5)
        >>> for entry in history:
        ...     print(f"{entry['changed_at']}: {entry['changed_by']}")
    """
    # Validate input
    try:
        validated_article = validate_article_number(article_number)
    except ValidationError as e:
        logger.error(f"Invalid article number: {article_number}")
        raise

    # Delegate to database
    try:
        history = db.get_notes_history(
            article_number=validated_article,
            limit=limit
        )

        logger.debug(
            f"Retrieved {len(history)} history entries for {validated_article}"
        )

        return history

    except Exception as e:
        logger.exception(f"Error loading notes history for {validated_article}")
        raise DatabaseError(
            f"Failed to load notes history: {e}",
            details={
                "article_number": validated_article,
                "limit": limit
            }
        )


def populate_articles_with_certificates(
    db: DatabaseInterface,
    articles: List[Dict[str, Any]],
    project_id: int
) -> List[Dict[str, Any]]:
    """
    Populate articles with certificates from database.

    This enriches article dicts with a 'certificates' field containing
    the list of certificates for each article.

    OPTIMIZED: Fetches all certificates in ONE query instead of N queries (N+1 problem fix).

    Args:
        db: Database instance (injected)
        articles: List of article dicts (from get_articles_for_project)
        project_id: Project ID

    Returns:
        Same articles list but with 'certificates' field populated

    Example:
        >>> articles = get_articles_for_project(db, project_id=1)
        >>> articles = populate_articles_with_certificates(db, articles, project_id)
        >>> for article in articles:
        ...     print(f"{article['article_number']}: {len(article['certificates'])} certs")
    """
    logger.info(f"🔍 populate_articles_with_certificates: project_id={project_id}, {len(articles)} articles")

    # OPTIMIZATION: Fetch ALL certificates for project in ONE query (instead of N queries)
    all_certificates = db.get_certificates_for_project(project_id)
    logger.debug(f"  Fetched {len(all_certificates)} total certificates in 1 query")

    # Group certificates by article_number for fast lookup
    cert_by_article = {}
    for cert in all_certificates:
        article_num = cert.get('article_number')
        if article_num:
            if article_num not in cert_by_article:
                cert_by_article[article_num] = []
            cert_by_article[article_num].append(cert)

    # Assign certificates to each article
    for article in articles:
        article_number = article.get('article_number')
        if article_number:
            certificates = cert_by_article.get(article_number, [])
            article['certificates'] = certificates

            # DEBUG: Log certificate details
            if certificates:
                logger.info(f"  ✅ {article_number}: {len(certificates)} certifikat")
                for cert in certificates:
                    logger.debug(f"    - {cert.get('certificate_type', 'Unknown')}: {cert.get('stored_path', 'No path')}")
            else:
                logger.debug(f"  ⚠️ {article_number}: Inga certifikat")
        else:
            article['certificates'] = []
            logger.warning(f"  ❌ Article utan article_number: {article}")

    total_certs = sum(len(a.get('certificates', [])) for a in articles)
    logger.info(
        f"✅ Populated {len(articles)} articles with {total_certs} TOTAL certificates "
        f"for project {project_id}"
    )

    return articles


def get_articles_with_notes(
    db: DatabaseInterface,
    project_id: int
) -> List[Dict[str, Any]]:
    """
    Get articles that have notes set.

    Convenience function to filter articles that have non-empty notes.

    Args:
        db: Database instance (injected)
        project_id: Project ID

    Returns:
        List of article dicts that have notes

    Example:
        >>> articles = get_articles_with_notes(db, project_id=1)
        >>> for article in articles:
        ...     print(f"{article['article_number']}: {article['global_notes']}")
    """
    all_articles = get_articles_for_project(db, project_id)
    articles_with_notes = [
        article for article in all_articles
        if article.get("global_notes") and article["global_notes"].strip()
    ]

    logger.debug(
        f"Found {len(articles_with_notes)}/{len(all_articles)} articles "
        f"with notes in project {project_id}"
    )

    return articles_with_notes
