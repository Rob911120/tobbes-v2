"""
Application Context for Tobbes v2.

Centralized application state and dependency injection.
"""

from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

from data.interface import DatabaseInterface
from .settings import Settings, get_settings


@dataclass
class AppContext:
    """
    Centralized application context.

    Contains all application-wide state and dependencies.
    Injected into UI layer and passed to operations.

    Key principles:
    - Immutable where possible (use with_* methods for changes)
    - All dependencies explicit (database, settings, etc.)
    - No global state - everything through context

    Example:
        >>> from config.app_context import AppContext
        >>> from data import create_database
        >>> from config.settings import get_settings
        >>>
        >>> db = create_database("sqlite", path="./test.db")
        >>> settings = get_settings()
        >>> ctx = AppContext(database=db, settings=settings)
        >>>
        >>> # Set current project
        >>> ctx = ctx.with_project(project_id=1)
        >>>
        >>> # Pass to operations
        >>> from operations import get_articles_for_project
        >>> articles = get_articles_for_project(ctx.database, ctx.current_project_id)
    """

    # Core dependencies (required)
    database: DatabaseInterface
    settings: Settings = field(default_factory=get_settings)

    # Application state (optional)
    current_project_id: Optional[int] = None
    current_project_name: Optional[str] = None

    # User info
    user_name: str = field(default_factory=lambda: get_settings().user_name)

    # Application version
    app_version: str = field(default_factory=lambda: get_settings().app_version)

    # Working directories (from settings)
    # NOTE: Reports and certificates are now stored per-project in projects/{project_id}/
    # Use config.paths.get_project_reports_path(project_id) and get_project_certificates_path(project_id)
    @property
    def data_dir(self) -> Path:
        """Get data directory from settings."""
        return self.settings.data_dir

    @property
    def temp_dir(self) -> Path:
        """Get temp directory from settings."""
        return self.settings.temp_dir

    @property
    def project_name(self) -> Optional[str]:
        """Get current project name (alias for current_project_name)."""
        return self.current_project_name

    def with_project(self, project_id: int, project_name: Optional[str] = None) -> "AppContext":
        """
        Create new context with project set.

        Immutable pattern - returns new instance instead of modifying self.

        Args:
            project_id: Project ID to set
            project_name: Optional project name (for display)

        Returns:
            New AppContext instance with project set

        Example:
            >>> ctx = app_context.with_project(project_id=1, project_name="Test Project")
            >>> print(ctx.current_project_id)  # 1
        """
        return AppContext(
            database=self.database,
            settings=self.settings,
            current_project_id=project_id,
            current_project_name=project_name,
            user_name=self.user_name,
            app_version=self.app_version,
        )

    def clear_project(self) -> "AppContext":
        """
        Create new context with project cleared.

        Returns:
            New AppContext instance with no project set
        """
        return AppContext(
            database=self.database,
            settings=self.settings,
            current_project_id=None,
            current_project_name=None,
            user_name=self.user_name,
            app_version=self.app_version,
        )

    def has_project(self) -> bool:
        """Check if a project is currently selected."""
        return self.current_project_id is not None

    def require_project(self) -> int:
        """
        Get current project ID or raise error.

        Useful in operations that require a project.

        Returns:
            Current project ID

        Raises:
            ValueError: If no project is selected

        Example:
            >>> project_id = ctx.require_project()  # Raises if no project
            >>> articles = get_articles_for_project(ctx.database, project_id)
        """
        if not self.has_project():
            raise ValueError(
                "No project selected. Please select a project first."
            )
        return self.current_project_id


def create_app_context(
    database: DatabaseInterface,
    settings: Optional[Settings] = None,
    user_name: Optional[str] = None,
) -> AppContext:
    """
    Factory function to create AppContext.

    Args:
        database: Database instance (required)
        settings: Settings instance (defaults to global settings)
        user_name: User name (defaults to settings.user_name)

    Returns:
        AppContext instance

    Example:
        >>> from data import create_database
        >>> db = create_database("sqlite", path="./test.db")
        >>> ctx = create_app_context(database=db, user_name="Tobbes")
    """
    if settings is None:
        settings = get_settings()

    if user_name is None:
        user_name = settings.user_name

    return AppContext(
        database=database,
        settings=settings,
        user_name=user_name,
    )
