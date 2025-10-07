"""
Database Interface - Abstract Base Class for database operations.

This module defines the contract for all database implementations in tobbes_v2.
Any database backend (SQLite, PostgreSQL, etc.) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
from pathlib import Path


class DatabaseInterface(ABC):
    """
    Abstract base class for database operations.

    This interface defines all methods required for managing:
    - Projects and their metadata
    - Articles (project-specific and global)
    - Inventory items and batches
    - Certificates
    - Certificate types (global and project-specific)
    """

    # ==================== Project Operations ====================

    @abstractmethod
    def save_project(
        self,
        project_name: str,
        order_number: str,
        customer: str,
        created_by: str,
        purchase_order_number: Optional[str] = None,
        project_type: str = "Doc",
        description: Optional[str] = None,
        project_id: Optional[int] = None,
    ) -> int:
        """
        Save or update a project.

        Args:
            project_name: Name of the project (Artikelbenämning)
            order_number: Order number (e.g., "TO-12345")
            customer: Customer name
            created_by: Username of creator
            purchase_order_number: Purchase order number (Beställningsnummer)
            project_type: Project type ("Doc" or "Ej Doc")
            description: Optional project description
            project_id: If provided, update existing project; otherwise create new

        Returns:
            int: Project ID (newly created or existing)
        """
        pass

    @abstractmethod
    def get_project(self, project_id: int) -> Optional[Dict[str, Any]]:
        """
        Get project by ID.

        Args:
            project_id: The project ID

        Returns:
            Dict containing project data, or None if not found.
            Expected keys: id, project_name, order_number, customer,
                          created_at, updated_at, created_by, description
        """
        pass

    @abstractmethod
    def list_projects(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        order_by: str = "updated_at DESC",
    ) -> List[Dict[str, Any]]:
        """
        List all projects with pagination.

        Args:
            limit: Maximum number of projects to return (None for all)
            offset: Number of projects to skip
            order_by: SQL ORDER BY clause (e.g., "updated_at DESC")

        Returns:
            List of project dictionaries
        """
        pass

    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        """
        Delete a project and all associated data.

        Args:
            project_id: The project ID

        Returns:
            bool: True if deleted, False if project not found
        """
        pass

    # ==================== Global Article Operations ====================

    @abstractmethod
    def save_global_article(
        self,
        article_number: str,
        description: Optional[str] = None,
        notes: Optional[str] = None,
        changed_by: Optional[str] = None,
    ) -> bool:
        """
        Save or update a global article (shared across all projects).

        Args:
            article_number: Article number (unique identifier)
            description: Article description
            notes: Global notes for this article (visible in all projects)
            changed_by: Username of person making changes

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_global_article(self, article_number: str) -> Optional[Dict[str, Any]]:
        """
        Get global article data.

        Args:
            article_number: Article number

        Returns:
            Dict containing global article data, or None if not found.
            Expected keys: article_number, description, notes, updated_at, changed_by
        """
        pass

    @abstractmethod
    def update_article_notes(
        self,
        article_number: str,
        notes: str,
        changed_by: str,
    ) -> bool:
        """
        Update notes for a global article.

        This will trigger the audit log (via database trigger).

        Args:
            article_number: Article number
            notes: New notes content
            changed_by: Username of person making changes

        Returns:
            bool: True if successful, False if article not found
        """
        pass

    @abstractmethod
    def get_notes_history(
        self,
        article_number: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get audit log of notes changes for an article.

        Args:
            article_number: Article number
            limit: Maximum number of history entries to return

        Returns:
            List of audit log entries, each containing:
            - changed_at: datetime
            - changed_by: str
            - old_notes: str
            - new_notes: str
        """
        pass

    # ==================== Project Article Operations ====================

    @abstractmethod
    def save_project_articles(
        self,
        project_id: int,
        articles: List[Dict[str, Any]],
    ) -> bool:
        """
        Save project-specific articles (from nivålista/BOM).

        Args:
            project_id: The project ID
            articles: List of article dictionaries with keys:
                - article_number (str)
                - description (str)
                - quantity (float)
                - level (int, e.g., 1, 1.1, 1.1.1)
                - parent_article (Optional[str])
                - charge_number (Optional[str])

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_project_articles(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all articles for a project (project-specific data only).

        Args:
            project_id: The project ID

        Returns:
            List of article dictionaries (project_articles table)
        """
        pass

    @abstractmethod
    def get_project_articles_with_global_data(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all articles for a project WITH global notes joined.

        This is the primary method for displaying articles in the UI.

        Args:
            project_id: The project ID

        Returns:
            List of article dictionaries containing:
            - All project_articles fields (id, article_number, description, etc.)
            - global_notes: From global_articles table
            - global_description: From global_articles table
        """
        pass

    @abstractmethod
    def update_article_charge(
        self,
        project_id: int,
        article_number: str,
        charge_number: Optional[str],
    ) -> bool:
        """
        Update charge number for a project article.

        Args:
            project_id: The project ID
            article_number: Article number
            charge_number: New charge number (None to clear)

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def update_article_quantity(
        self,
        project_id: int,
        article_number: str,
        quantity: float,
    ) -> bool:
        """
        Update quantity for a project article.

        Args:
            project_id: The project ID
            article_number: Article number
            quantity: New quantity

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def update_article_level(
        self,
        project_id: int,
        article_number: str,
        level: str,
    ) -> bool:
        """
        Update level number for a project article.

        Args:
            project_id: The project ID
            article_number: Article number
            level: New level number

        Returns:
            bool: True if successful
        """
        pass

    # ==================== Inventory Operations ====================

    @abstractmethod
    def save_inventory_items(
        self,
        project_id: int,
        inventory_items: List[Dict[str, Any]],
    ) -> bool:
        """
        Save inventory items (from lagerlogg).

        Args:
            project_id: The project ID
            inventory_items: List of inventory item dictionaries with keys:
                - article_number (str)
                - charge_number (str)
                - batch_id (Optional[str])
                - quantity (float)
                - location (Optional[str])
                - received_date (Optional[datetime])

        Returns:
            bool: True if successful
        """
        pass

    @abstractmethod
    def get_inventory_items(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all inventory items for a project.

        Args:
            project_id: The project ID

        Returns:
            List of inventory item dictionaries
        """
        pass

    @abstractmethod
    def get_available_charges(
        self,
        project_id: int,
        article_number: str,
    ) -> List[str]:
        """
        Get list of available charge numbers for an article.

        Args:
            project_id: The project ID
            article_number: Article number

        Returns:
            List of charge numbers (strings)
        """
        pass

    # ==================== Certificate Operations ====================

    @abstractmethod
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
        """
        Save a certificate for an article.

        Args:
            project_id: The project ID
            article_number: Article number
            certificate_type: Type of certificate (e.g., "Materialintyg", "Svetslogg")
            file_path: Path to certificate file (relative to project dir)
            original_filename: Original filename
            page_count: Number of pages in PDF
            project_article_id: Optional reference to specific project_articles.id

        Returns:
            int: Certificate ID
        """
        pass

    @abstractmethod
    def get_certificates_for_article(
        self,
        project_id: int,
        article_number: str,
    ) -> List[Dict[str, Any]]:
        """
        Get all certificates for an article.

        Args:
            project_id: The project ID
            article_number: Article number

        Returns:
            List of certificate dictionaries
        """
        pass

    @abstractmethod
    def get_certificates_for_project(
        self,
        project_id: int,
    ) -> List[Dict[str, Any]]:
        """
        Get all certificates for a project.

        Args:
            project_id: The project ID

        Returns:
            List of certificate dictionaries
        """
        pass

    @abstractmethod
    def delete_certificate(
        self,
        certificate_id: int,
    ) -> bool:
        """
        Delete a certificate.

        Args:
            certificate_id: The certificate ID

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    # ==================== Certificate Type Operations ====================

    @abstractmethod
    def get_certificate_types(
        self,
        project_id: Optional[int] = None,
    ) -> List[str]:
        """
        Get all certificate types (global + project-specific).

        Args:
            project_id: If provided, include project-specific types;
                       otherwise only return global types

        Returns:
            List of certificate type names (strings), sorted
        """
        pass

    @abstractmethod
    def add_certificate_type(
        self,
        type_name: str,
        project_id: Optional[int] = None,
    ) -> bool:
        """
        Add a new certificate type.

        Args:
            type_name: Name of certificate type
            project_id: If provided, add as project-specific;
                       otherwise add as global

        Returns:
            bool: True if added, False if already exists
        """
        pass

    @abstractmethod
    def delete_certificate_type(
        self,
        type_name: str,
        project_id: Optional[int] = None,
    ) -> bool:
        """
        Delete a certificate type.

        Args:
            type_name: Name of certificate type
            project_id: If provided, delete from project-specific;
                       otherwise delete from global

        Returns:
            bool: True if deleted, False if not found
        """
        pass

    # ==================== Statistics Operations ====================

    @abstractmethod
    def get_project_statistics(self, project_id: int) -> Dict[str, int]:
        """
        Get statistics for a project.

        Args:
            project_id: The project ID

        Returns:
            Dict containing:
            - total_articles: Total number of articles in project
            - verified_articles: Number of articles with at least one certificate
        """
        pass

    # ==================== Utility Operations ====================

    @abstractmethod
    def execute_query(
        self,
        query: str,
        params: Optional[Tuple] = None,
    ) -> List[Dict[str, Any]]:
        """
        Execute a raw SQL query (for advanced use cases).

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of result dictionaries
        """
        pass

    @abstractmethod
    def close(self):
        """Close database connection."""
        pass
