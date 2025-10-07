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
        """Run all SQL migration files in order."""
        migrations_dir = Path(__file__).parent / "migrations"
        migration_files = sorted(migrations_dir.glob("*.sql"))

        for migration_file in migration_files:
            logger.debug(f"Running migration: {migration_file.name}")
            sql = migration_file.read_text()
            self.conn.executescript(sql)

        self.conn.commit()
        logger.info(f"Executed {len(migration_files)} migrations")

    # ==================== Project Operations ====================

    def save_project(
        self,
        project_name: str,
        order_number: str,
        customer: str,
        created_by: str,
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
                    (project_name, order_number, customer, description, project_id),
                )
                self.conn.commit()
                return project_id
            else:
                # Insert new
                cursor.execute(
                    Q.INSERT_PROJECT,
                    (project_name, order_number, customer, created_by, description),
                )
                self.conn.commit()
                return cursor.lastrowid

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
            return True

        except Exception as e:
            self.conn.rollback()
            raise DatabaseError(f"Failed to save inventory items: {e}")

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

    # ==================== Certificate Operations ====================

    def save_certificate(
        self,
        project_id: int,
        article_number: str,
        certificate_type: str,
        file_path: str,
        original_filename: str,
        page_count: int = 1,
        project_article_id: Optional[int] = None,
    ) -> int:
        """Save a certificate for an article."""
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                Q.INSERT_CERTIFICATE,
                (
                    project_id,
                    article_number,
                    certificate_type,
                    file_path,
                    original_filename,
                    page_count,
                    project_article_id,
                ),
            )
            self.conn.commit()
            return cursor.lastrowid

        except Exception as e:
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
        """Get all certificate types (global + project-specific)."""
        cursor = self.conn.cursor()

        # Get global types
        cursor.execute(Q.SELECT_GLOBAL_CERTIFICATE_TYPES)
        global_types = [row["type_name"] for row in cursor.fetchall()]

        # Get project-specific types if project_id provided
        project_types = []
        if project_id:
            cursor.execute(Q.SELECT_PROJECT_CERTIFICATE_TYPES, (project_id,))
            project_types = [row["type_name"] for row in cursor.fetchall()]

        # Combine and sort (project-specific first)
        return sorted(set(project_types + global_types))

    def add_certificate_type(
        self,
        type_name: str,
        project_id: Optional[int] = None,
    ) -> bool:
        """Add a new certificate type."""
        try:
            cursor = self.conn.cursor()

            if project_id:
                cursor.execute(Q.INSERT_PROJECT_CERTIFICATE_TYPE, (project_id, type_name))
            else:
                cursor.execute(Q.INSERT_GLOBAL_CERTIFICATE_TYPE, (type_name,))

            self.conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            logger.warning(f"Failed to add certificate type (may already exist): {e}")
            return False

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
