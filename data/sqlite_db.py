"""
SQLite implementation of DatabaseInterface.

This module provides a complete SQLite implementation of the database interface,
including automatic migrations and connection management.
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime

from .interface import DatabaseInterface
from . import queries as Q
from domain.exceptions import DatabaseError, NotFoundError

logger = logging.getLogger(__name__)


class SQLiteDatabase(DatabaseInterface):
    """
    SQLite implementation of DatabaseInterface.

    Features:
    - Automatic migrations on initialization
    - Connection pooling with row_factory
    - ACID transactions
    - Foreign key enforcement
    """

    def __init__(self, db_path: Union[Path, str]):
        """
        Initialize SQLite database.

        Args:
            db_path: Path to SQLite database file (created if not exists)
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize connection
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Use built-in Row factory (safer for JOINs)
        self.conn.execute("PRAGMA foreign_keys = ON")  # Enforce FK constraints

        # Run migrations
        self._run_migrations()
        logger.info(f"SQLite database initialized at {self.db_path}")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert sqlite3.Row to dictionary."""
        return dict(row) if row else None

    def _rows_to_dicts(self, rows: List[sqlite3.Row]) -> List[Dict[str, Any]]:
        """Convert list of sqlite3.Row to list of dicts."""
        return [dict(row) for row in rows]

    def _run_migrations(self):
        """
        Run all SQL migration files in order, tracking which have been applied.

        Uses schema_migrations table to track applied migrations and prevent
        re-running destructive migrations (like 007_rebuild_certificates.sql).
        """
        migrations_dir = Path(__file__).parent / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))

        # Step 1: Ensure migration tracking table exists
        # Run 000_migration_tracking.sql first if it exists
        tracking_migration = migrations_dir / "000_migration_tracking.sql"
        if tracking_migration.exists():
            sql = tracking_migration.read_text()
            self.conn.executescript(sql)
            self.conn.commit()

        # Step 2: Get list of already-applied migrations
        cursor = self.conn.cursor()
        cursor.execute("SELECT migration_name FROM schema_migrations")
        applied_migrations = {row[0] for row in cursor.fetchall()}

        # Step 3: Run each migration that hasn't been applied yet
        migrations_run = 0
        for migration_file in migration_files:
            migration_name = migration_file.name

            # Skip if already applied
            if migration_name in applied_migrations:
                logger.debug(f"Skipping already-applied migration: {migration_name}")
                continue

            logger.debug(f"Running migration: {migration_name}")
            sql = migration_file.read_text()

            try:
                # Execute migration
                self.conn.executescript(sql)

                # Record as applied
                cursor.execute(
                    "INSERT INTO schema_migrations (migration_name) VALUES (?)",
                    (migration_name,)
                )
                self.conn.commit()
                migrations_run += 1
                logger.info(f"✅ Applied migration: {migration_name}")

            except sqlite3.OperationalError as e:
                # Handle idempotent migrations (e.g., duplicate column)
                if "duplicate column" in str(e).lower():
                    logger.warning(f"Migration {migration_name} already applied (columns exist) - marking as applied")
                    # Mark as applied even though it failed (schema already correct)
                    cursor.execute(
                        "INSERT OR IGNORE INTO schema_migrations (migration_name) VALUES (?)",
                        (migration_name,)
                    )
                    self.conn.commit()
                else:
                    # Re-raise other operational errors
                    raise

        logger.info(f"Migration summary: {migrations_run} new, {len(applied_migrations)} already applied")

    # ==================== Project Operations ====================

    def save_project(
        self,
        project_name: str,
        order_number: str,
        customer: str,
        created_by: str,
        purchase_order_number: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> int:
        """Save or update a project."""
        try:
            cursor = self.conn.cursor()

            if project_id:
                # Update existing
                cursor.execute(
                    Q.UPDATE_PROJECT,
                    (project_name, order_number, customer, description,
                     purchase_order_number, project_id),
                )
                self.conn.commit()
                return project_id
            else:
                # Insert new
                cursor.execute(
                    Q.INSERT_PROJECT,
                    (project_name, order_number, customer, created_by, description,
                     purchase_order_number),
                )
                new_project_id = cursor.lastrowid
                self.conn.commit()

                # Initialize certificate types for new project
                self._initialize_project_certificate_types(new_project_id)

                return new_project_id

        except sqlite3.IntegrityError as e:
            raise DatabaseError(
                f"Project with order_number '{order_number}' already exists",
                details={"order_number": order_number, "error": str(e)},
            )
        except Exception as e:
            raise DatabaseError(f"Failed to save project: {e}")

    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_PROJECT_BY_ID, (project_id,))
        return self._row_to_dict(cursor.fetchone())

    def list_projects(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "updated_at DESC",
    ) -> List[Dict[str, Any]]:
        """List all projects with pagination."""
        cursor = self.conn.cursor()
        query = Q.SELECT_ALL_PROJECTS.format(order_by=order_by)
        cursor.execute(query, (limit or 999999, offset))
        return self._rows_to_dicts(cursor.fetchall())

    def delete_project(self, project_id: int) -> bool:
        """Delete a project and all associated data."""
        cursor = self.conn.cursor()
        cursor.execute(Q.DELETE_PROJECT, (project_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_distinct_customers(self) -> List[str]:
        """Get list of unique customer names from all projects."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_DISTINCT_CUSTOMERS)
        rows = cursor.fetchall()
        return [row[0] for row in rows]

    # ==================== Global Article Operations ====================

    def save_global_article(
        self,
        article_number: str,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> bool:
        """Save or update a global article."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                Q.UPSERT_GLOBAL_ARTICLE,
                (article_number, description or "", notes or "", changed_by or "system"),
            )
            self.conn.commit()
            return True
        except Exception as e:
            raise DatabaseError(f"Failed to save global article: {e}")

    def get_global_article(self, article_number: str) -> Optional[Dict[str, Any]]:
        """Get global article data."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_GLOBAL_ARTICLE, (article_number,))
        return self._row_to_dict(cursor.fetchone())

    def update_article_notes(
        self,
        article_number: str,
        notes: str,
        changed_by: str,
    ) -> bool:
        """Update notes for a global article (triggers audit log)."""
        cursor = self.conn.cursor()
        cursor.execute(Q.UPDATE_ARTICLE_NOTES, (notes, changed_by, article_number))
        self.conn.commit()
        return cursor.rowcount > 0

    def get_notes_history(
        self,
        article_number: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get audit log of notes changes."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_NOTES_HISTORY, (article_number, limit))
        return self._rows_to_dicts(cursor.fetchall())

    # ==================== Project Article Operations ====================

    def save_project_articles(
        self,
        project_id: int,
        articles: List[Dict[str, Any]],
    ) -> bool:
        """Save project-specific articles (from nivålista/BOM)."""
        try:
            cursor = self.conn.cursor()

            for article in articles:
                # Ensure global article exists (only create if new, don't overwrite)
                article_num = article["article_number"]
                if not self.get_global_article(article_num):
                    # Create new global article
                    self.save_global_article(
                        article_num,
                        description=article.get("description", ""),
                        notes="",  # Empty initially
                    )

                # Save project article
                cursor.execute(
                    Q.INSERT_PROJECT_ARTICLE,
                    (
                        project_id,
                        article["article_number"],
                        article.get("description", ""),
                        article.get("quantity", 0.0),
                        article.get("level", ""),
                        article.get("parent_article"),
                        article.get("charge_number"),
                        article.get("batch_number"),
                        article.get("sort_order", 0),  # Preserve import order from Excel
                    ),
                )

            self.conn.commit()
            return True

        except Exception as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to save project articles: {e}")

    def get_project_articles(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all articles for a project (project-specific data only)."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_PROJECT_ARTICLES, (project_id,))
        return self._rows_to_dicts(cursor.fetchall())

    def get_project_articles_with_global_data(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all articles for a project WITH global notes joined."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_PROJECT_ARTICLES_WITH_GLOBAL, (project_id,))
        return self._rows_to_dicts(cursor.fetchall())

    def update_article_charge(
        self,
        project_id: int,
        article_number: str,
        charge_number: Optional[str],
    ) -> bool:
        """Update charge number for a project article."""
        cursor = self.conn.cursor()
        cursor.execute(
            Q.UPDATE_ARTICLE_CHARGE, (charge_number, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_article_quantity(
        self,
        project_id: int,
        article_number: str,
        quantity: float,
    ) -> bool:
        """Update quantity for a project article."""
        cursor = self.conn.cursor()
        cursor.execute(
            Q.UPDATE_ARTICLE_QUANTITY, (quantity, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_article_level(
        self,
        project_id: int,
        article_number: str,
        level: str,
    ) -> bool:
        """Update level number for a project article."""
        cursor = self.conn.cursor()
        cursor.execute(
            Q.UPDATE_ARTICLE_LEVEL, (level, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_article_batch(
        self,
        project_id: int,
        article_number: str,
        batch_id: Optional[str],
    ) -> bool:
        """Update batch ID for a project article."""
        cursor = self.conn.cursor()
        batch_value = batch_id if batch_id else None
        cursor.execute(
            Q.UPDATE_ARTICLE_BATCH, (batch_value, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_article_parent(
        self,
        project_id: int,
        article_number: str,
        parent_article: Optional[str],
    ) -> bool:
        """Update parent article for a project article (hierarchy)."""
        cursor = self.conn.cursor()
        cursor.execute(
            Q.UPDATE_ARTICLE_PARENT, (parent_article, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_article_sort_order(
        self,
        project_id: int,
        article_number: str,
        sort_order: int,
    ) -> bool:
        """Update sort order for a project article (display order)."""
        cursor = self.conn.cursor()
        cursor.execute(
            Q.UPDATE_ARTICLE_SORT_ORDER, (sort_order, project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def update_project_article(
        self,
        project_id: int,
        article_number: str,
        article_data: Dict[str, Any],
    ) -> bool:
        """
        Update project article with multiple fields at once.

        Dynamically builds UPDATE query based on provided fields.
        Only updates fields that are present in article_data.
        """
        if not article_data:
            return False

        # Allowed fields that can be updated
        allowed_fields = {
            'quantity', 'charge_number', 'batch_number', 'level',
            'parent_article', 'sort_order', 'verified', 'description'
        }

        # Filter to only allowed fields
        fields_to_update = {k: v for k, v in article_data.items() if k in allowed_fields}

        if not fields_to_update:
            logger.warning(f"No valid fields to update for article {article_number}")
            return False

        # Build dynamic UPDATE query
        set_clauses = [f"{field} = ?" for field in fields_to_update.keys()]
        sql = f"""
            UPDATE project_articles
            SET {', '.join(set_clauses)}
            WHERE project_id = ? AND article_number = ?
        """

        # Build values list
        values = list(fields_to_update.values()) + [project_id, article_number]

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, values)
            self.conn.commit()

            if cursor.rowcount > 0:
                logger.debug(f"Updated article {article_number} with fields: {list(fields_to_update.keys())}")
                return True
            else:
                logger.warning(f"Article {article_number} not found in project {project_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to update article {article_number}: {e}")
            raise DatabaseError(f"Failed to update article: {e}")

    def delete_project_article(
        self,
        project_id: int,
        article_number: str,
    ) -> bool:
        """
        Delete article from project.

        NOTE: This only removes the project_article record.
        Global article data is preserved (other projects might use it).
        Certificates should be deleted separately before calling this.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            Q.DELETE_PROJECT_ARTICLE, (project_id, article_number)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Inventory Operations ====================

    def save_inventory_items(
        self,
        project_id: int,
        inventory_items: List[Dict[str, Any]],
    ) -> bool:
        """Save inventory items (from lagerlogg)."""
        try:
            cursor = self.conn.cursor()

            for item in inventory_items:
                cursor.execute(
                    Q.INSERT_INVENTORY_ITEM,
                    (
                        project_id,
                        item["article_number"],
                        item["charge_number"],
                        item.get("batch_id"),
                        item.get("quantity", 0.0),
                        item.get("location"),
                        item.get("received_date"),
                    ),
                )

            self.conn.commit()

            # Sync charge/batch numbers from inventory to project_articles
            self._sync_charges_from_inventory(project_id)

            return True

        except Exception as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to save inventory items: {e}")

    def _sync_charges_from_inventory(self, project_id: int) -> None:
        """
        Sync charge and batch numbers from inventory_items to project_articles.

        After lagerlogg is imported, this updates project_articles with the latest
        charge/batch info from inventory_items.

        For each article:
        - Finds the most recent inventory item (by received_date)
        - Updates project_articles with that charge_number and batch_id
        """
        try:
            cursor = self.conn.cursor()

            # Get distinct article numbers from inventory for this project
            cursor.execute("""
                SELECT DISTINCT article_number
                FROM inventory_items
                WHERE project_id = ?
            """, (project_id,))

            articles = cursor.fetchall()

            for (article_number,) in articles:
                # Get most recent inventory item for this article
                cursor.execute("""
                    SELECT charge_number, batch_id
                    FROM inventory_items
                    WHERE project_id = ? AND article_number = ?
                    ORDER BY received_date DESC, id DESC
                    LIMIT 1
                """, (project_id, article_number))

                result = cursor.fetchone()
                if result:
                    charge_number, batch_id = result

                    # Update project_articles with charge and batch
                    cursor.execute(
                        Q.UPDATE_ARTICLE_CHARGE_AND_BATCH,
                        (charge_number, batch_id, project_id, article_number)
                    )

            self.conn.commit()
            logger.debug(f"Synced charges/batches for {len(articles)} articles in project {project_id}")

        except Exception as e:
            logger.exception(f"Failed to sync charges from inventory: {e}")
            # Don't raise - this is a best-effort sync
            # Inventory is still saved even if sync fails

    def get_inventory_items(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all inventory items for a project."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_INVENTORY_ITEMS, (project_id,))
        return self._rows_to_dicts(cursor.fetchall())

    def get_available_charges(
        self,
        project_id: int,
        article_number: str,
    ) -> List[str]:
        """Get list of available charge numbers for an article."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_AVAILABLE_CHARGES, (project_id, article_number))
        rows = cursor.fetchall()
        return [row["charge_number"] for row in rows if row["charge_number"]]

    def delete_inventory_items(
        self,
        project_id: int,
    ) -> bool:
        """Delete all inventory items for a project (prevent duplicates on re-import)."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(Q.DELETE_INVENTORY_ITEMS_FOR_PROJECT, (project_id,))
            self.conn.commit()
            deleted_count = cursor.rowcount
            logger.info(f"Deleted {deleted_count} inventory items for project {project_id}")
            return True
        except Exception as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to delete inventory items: {e}")

    # ==================== Certificate Operations ====================

    def save_certificate(
        self,
        project_id: int,
        article_number: str,
        certificate_id: str,
        cert_type: str,
        stored_path: str,
        stored_name: str,
        original_name: str,
        page_count: int = 0,
        project_article_id: Optional[int] = None,
        original_path: Optional[str] = None,
    ) -> int:
        """Save a certificate for an article with full storage metadata."""
        logger.debug(f"💾 SQLiteDatabase.save_certificate() called:")
        logger.debug(f"   project_id={project_id}, article={article_number}, cert_id={certificate_id}")

        try:
            cursor = self.conn.cursor()

            # Execute INSERT
            logger.debug(f"   Executing INSERT_CERTIFICATE...")
            cursor.execute(
                Q.INSERT_CERTIFICATE,
                (
                    project_id,
                    article_number,
                    certificate_id,
                    cert_type,
                    stored_path,
                    stored_name,
                    original_name,
                    page_count,
                    project_article_id,
                    original_path,
                ),
            )

            # Get inserted row ID
            inserted_id = cursor.lastrowid
            logger.debug(f"   INSERT executed, lastrowid={inserted_id}")

            # Commit transaction
            logger.debug(f"   Calling commit()...")
            self.conn.commit()
            logger.debug(f"   ✅ Commit successful!")

            # Verify that row was actually saved
            cursor.execute(
                "SELECT COUNT(*) FROM certificates WHERE id = ?",
                (inserted_id,)
            )
            count = cursor.fetchone()[0]
            logger.debug(f"   🔍 VERIFICATION: SELECT COUNT(*) WHERE id={inserted_id} → {count}")

            if count == 0:
                logger.error(f"   ❌ CRITICAL: Row with id={inserted_id} NOT found after commit!")
                raise DatabaseError(f"Certificate row disappeared after commit (id={inserted_id})")

            logger.info(f"✅ Certificate saved successfully: id={inserted_id}, cert_id={certificate_id}")
            return inserted_id

        except DatabaseError:
            # Re-raise DatabaseError as-is
            raise

        except Exception as e:
            logger.exception(f"❌ Exception in save_certificate: {type(e).__name__}: {e}")
            self.conn.rollback()  # Explicit rollback on error
            raise DatabaseError(f"Failed to save certificate: {e}")

    def get_certificates_for_article(
        self,
        project_id: int,
        article_number: str,
    ) -> List[Dict[str, Any]]:
        """Get all certificates for an article."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_CERTIFICATES_BY_ARTICLE, (project_id, article_number))
        return self._rows_to_dicts(cursor.fetchall())

    def get_certificates_for_project(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """Get all certificates for a project."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_CERTIFICATES_BY_PROJECT, (project_id,))
        return self._rows_to_dicts(cursor.fetchall())

    def delete_certificate(
        self,
        certificate_id: int,
    ) -> bool:
        """Delete a certificate."""
        cursor = self.conn.cursor()
        cursor.execute(Q.DELETE_CERTIFICATE, (certificate_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    # ==================== Certificate Type Operations ====================

    def get_certificate_types(
        self,
        project_id: Optional[int] = None,
    ) -> List[str]:
        """
        Get certificate types.

        If project_id is provided: Returns project-specific types only (sorted by sort_order).
        If project_id is None: Returns global types (for template management).
        """
        cursor = self.conn.cursor()

        if project_id:
            # Project mode: Return only project-specific types
            cursor.execute(Q.SELECT_PROJECT_CERTIFICATE_TYPES, (project_id,))
            return [row["type_name"] for row in cursor.fetchall()]
        else:
            # Global mode: Return global template types
            cursor.execute(Q.SELECT_GLOBAL_CERTIFICATE_TYPES)
            return [row["type_name"] for row in cursor.fetchall()]

    def add_certificate_type(
        self,
        type_name: str,
        project_id: Optional[int] = None,
        search_path: Optional[str] = None,
    ) -> bool:
        """Add a new certificate type with auto-assigned sort_order."""
        try:
            cursor = self.conn.cursor()

            if project_id:
                # Project-specific type: Get max sort_order + 10
                cursor.execute(Q.SELECT_MAX_PROJECT_SORT_ORDER, (project_id,))
                max_sort_order = cursor.fetchone()["max_sort_order"]
                new_sort_order = max_sort_order + 10

                cursor.execute(Q.INSERT_PROJECT_CERTIFICATE_TYPE, (project_id, type_name, new_sort_order))
            else:
                # Global type: Get max sort_order + 10
                cursor.execute(Q.SELECT_MAX_GLOBAL_SORT_ORDER)
                max_sort_order = cursor.fetchone()["max_sort_order"]
                new_sort_order = max_sort_order + 10

                cursor.execute(Q.INSERT_GLOBAL_CERTIFICATE_TYPE, (type_name, search_path, new_sort_order))

            self.conn.commit()
            logger.info(f"Added certificate type '{type_name}' with sort_order={new_sort_order}")
            return cursor.rowcount > 0

        except Exception as e:
            logger.warning(f"Failed to add certificate type (may already exist): {e}")
            return False

    def _initialize_project_certificate_types(self, project_id: int) -> None:
        """
        Initialize project certificate types by copying all global types.

        Called automatically when a new project is created.
        Each project gets its own copy of standard types which can be reordered independently.

        Args:
            project_id: ID of newly created project
        """
        try:
            cursor = self.conn.cursor()

            # Get all global certificate types
            cursor.execute(Q.SELECT_GLOBAL_CERTIFICATE_TYPES_WITH_SORT_ORDER)
            global_types = cursor.fetchall()

            # Copy each global type to project_certificate_types
            for row in global_types:
                type_name = row["type_name"]
                sort_order = row["sort_order"]

                cursor.execute(
                    Q.INSERT_PROJECT_CERTIFICATE_TYPE,
                    (project_id, type_name, sort_order)
                )

            self.conn.commit()
            logger.info(f"Initialized {len(global_types)} certificate types for project {project_id}")

        except Exception as e:
            logger.exception(f"Failed to initialize project certificate types: {e}")
            self.conn.rollback()
            # Don't raise - project creation should succeed even if this fails

    def delete_certificate_type(
        self,
        type_name: str,
        project_id: Optional[int] = None,
    ) -> bool:
        """Delete a certificate type."""
        cursor = self.conn.cursor()

        if project_id:
            cursor.execute(Q.DELETE_PROJECT_CERTIFICATE_TYPE, (project_id, type_name))
        else:
            cursor.execute(Q.DELETE_GLOBAL_CERTIFICATE_TYPE, (type_name,))

        self.conn.commit()
        return cursor.rowcount > 0

    def get_certificate_types_with_paths(
        self,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get all certificate types with their search paths."""
        cursor = self.conn.cursor()

        # Get global types with paths
        cursor.execute(Q.SELECT_GLOBAL_CERTIFICATE_TYPES_WITH_PATHS)
        global_types = [
            {
                "type_name": row["type_name"],
                "search_path": row["search_path"],
                "is_global": True,
            }
            for row in cursor.fetchall()
        ]

        # Get project-specific types if project_id provided
        project_types = []
        if project_id:
            cursor.execute(Q.SELECT_PROJECT_CERTIFICATE_TYPES_WITH_PATHS, (project_id,))
            project_types = [
                {
                    "type_name": row["type_name"],
                    "search_path": None,  # Project types don't have search paths
                    "is_global": False,
                }
                for row in cursor.fetchall()
            ]

        # Combine (project-specific first)
        return project_types + global_types

    def update_certificate_type_search_path(
        self,
        type_name: str,
        search_path: Optional[str],
        project_id: Optional[int] = None,
    ) -> bool:
        """Update the search path for a certificate type."""
        # Only global types have search paths
        if project_id is not None:
            logger.warning("Project-specific certificate types cannot have search paths")
            return False

        try:
            cursor = self.conn.cursor()
            cursor.execute(Q.UPDATE_CERTIFICATE_TYPE_SEARCH_PATH, (search_path, type_name))
            self.conn.commit()

            if cursor.rowcount > 0:
                logger.info(f"Updated search_path for '{type_name}': {search_path}")
                return True
            else:
                logger.warning(f"Certificate type '{type_name}' not found")
                return False

        except Exception as e:
            logger.exception(f"Failed to update search_path: {e}")
            self.conn.rollback()
            return False

    def swap_certificate_type_order(
        self,
        type_name_1: str,
        type_name_2: str,
        project_id: Optional[int] = None,
    ) -> bool:
        """Swap the sort_order of two certificate types."""
        try:
            cursor = self.conn.cursor()

            if project_id:
                # Project-specific types
                # Get sort_orders
                cursor.execute(
                    "SELECT sort_order FROM project_certificate_types WHERE project_id = ? AND type_name = ?",
                    (project_id, type_name_1)
                )
                row1 = cursor.fetchone()

                cursor.execute(
                    "SELECT sort_order FROM project_certificate_types WHERE project_id = ? AND type_name = ?",
                    (project_id, type_name_2)
                )
                row2 = cursor.fetchone()

                if not row1 or not row2:
                    logger.warning(
                        f"Could not find both certificate types for swap: "
                        f"project_id={project_id}, type1='{type_name_1}' (found={row1 is not None}), "
                        f"type2='{type_name_2}' (found={row2 is not None})"
                    )
                    return False

                sort_order_1 = row1["sort_order"]
                sort_order_2 = row2["sort_order"]

                # Swap
                cursor.execute(Q.UPDATE_PROJECT_CERTIFICATE_TYPE_SORT_ORDER, (sort_order_2, project_id, type_name_1))
                cursor.execute(Q.UPDATE_PROJECT_CERTIFICATE_TYPE_SORT_ORDER, (sort_order_1, project_id, type_name_2))
            else:
                # Global types
                # Get sort_orders
                cursor.execute(
                    "SELECT sort_order FROM certificate_types WHERE type_name = ?",
                    (type_name_1,)
                )
                row1 = cursor.fetchone()

                cursor.execute(
                    "SELECT sort_order FROM certificate_types WHERE type_name = ?",
                    (type_name_2,)
                )
                row2 = cursor.fetchone()

                if not row1 or not row2:
                    logger.warning(f"Could not find both certificate types for swap")
                    return False

                sort_order_1 = row1["sort_order"]
                sort_order_2 = row2["sort_order"]

                # Swap
                cursor.execute(Q.UPDATE_GLOBAL_CERTIFICATE_TYPE_SORT_ORDER, (sort_order_2, type_name_1))
                cursor.execute(Q.UPDATE_GLOBAL_CERTIFICATE_TYPE_SORT_ORDER, (sort_order_1, type_name_2))

            self.conn.commit()
            logger.info(f"Swapped sort_order for '{type_name_1}' and '{type_name_2}'")
            return True

        except Exception as e:
            logger.exception(f"Failed to swap certificate type order: {e}")
            self.conn.rollback()
            return False

    def get_certificate_types_with_sort_order(
        self,
        project_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get certificate types with their sort_order for ordering.

        If project_id is provided: Returns project-specific types only.
        If project_id is None: Returns global template types.
        """
        cursor = self.conn.cursor()

        if project_id:
            # Project mode: Return only project-specific types
            cursor.execute(Q.SELECT_PROJECT_CERTIFICATE_TYPES_WITH_SORT_ORDER, (project_id,))
            return [
                {
                    "type_name": row["type_name"],
                    "sort_order": row["sort_order"],
                    "is_global": False,
                }
                for row in cursor.fetchall()
            ]
        else:
            # Global mode: Return global template types
            cursor.execute(Q.SELECT_GLOBAL_CERTIFICATE_TYPES_WITH_SORT_ORDER)
            return [
                {
                    "type_name": row["type_name"],
                    "sort_order": row["sort_order"],
                    "is_global": True,
                }
                for row in cursor.fetchall()
            ]

    # ==================== Statistics Operations ====================

    def get_project_statistics(self, project_id: int) -> Dict[str, int]:
        """Get statistics for a project."""
        cursor = self.conn.cursor()
        cursor.execute(Q.SELECT_PROJECT_STATISTICS, (project_id,))
        row = cursor.fetchone()

        if row:
            return {
                "total_articles": row["total_articles"] or 0,
                "verified_articles": row["verified_articles"] or 0,
            }
        return {"total_articles": 0, "verified_articles": 0}

    def get_project_content_count(self, project_id: int) -> Dict[str, int]:
        """Get count of articles and certificates for a project."""
        cursor = self.conn.cursor()
        cursor.execute(Q.COUNT_PROJECT_CONTENT, (project_id, project_id))
        row = cursor.fetchone()
        return {
            "articles": row[0] or 0,
            "certificates": row[1] or 0,
        }

    # ==================== Utility Operations ====================

    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
    ) -> List[Dict[str, Any]]:
        """Execute a raw SQL query (for advanced use cases)."""
        cursor = self.conn.cursor()
        cursor.execute(query, params or ())
        return self._rows_to_dicts(cursor.fetchall())

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
