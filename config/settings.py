"""
Application settings for Tobbes v2.

Loads settings from environment variables or uses defaults.
Provides centralized configuration management.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field

from .constants import (
    APP_VERSION,
    DEFAULT_DATABASE_NAME,
    DEFAULT_USER_NAME,
    DATA_DIR,
    TEMP_DIR,
)
from .paths import get_database_path


@dataclass
class Settings:
    """
    Application settings.

    Can be loaded from environment variables or initialized with defaults.
    """

    # Application info
    app_version: str = APP_VERSION
    user_name: str = DEFAULT_USER_NAME

    # Database settings
    database_type: str = "sqlite"  # Future: "postgresql"
    database_path: Path = field(default_factory=get_database_path)

    # Directory paths (created automatically if missing)
    # NOTE: Reports and certificates are now stored per-project in projects/{project_id}/
    # See config.paths module for project-specific paths
    data_dir: Path = field(default_factory=lambda: Path.cwd() / DATA_DIR)
    temp_dir: Path = field(default_factory=lambda: Path.cwd() / TEMP_DIR)

    # Chrome/Chromium path (auto-detected if not set)
    chrome_path: Optional[str] = None

    # PDF settings
    pdf_page_size: str = "A4"
    enable_watermark: bool = True

    # UI settings
    window_width: int = 1024
    window_height: int = 768

    # Debug settings
    debug_mode: bool = False
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR

    def __post_init__(self):
        """Ensure directories exist after initialization."""
        self._ensure_directories()

    def _ensure_directories(self):
        """Create required directories if they don't exist."""
        for dir_path in [
            self.data_dir,
            self.temp_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Load settings from environment variables.

        Environment variables:
        - TOBBES_USER_NAME: User name for audit logging
        - TOBBES_DATABASE_PATH: Path to SQLite database
        - TOBBES_DATA_DIR: Data directory
        - TOBBES_CHROME_PATH: Path to Chrome/Chromium executable
        - TOBBES_DEBUG: Enable debug mode (true/false)
        - TOBBES_LOG_LEVEL: Logging level (DEBUG/INFO/WARNING/ERROR)

        Note: Reports and certificates are now stored per-project in projects/{project_id}/
        See config.paths module for project-specific paths.

        Returns:
            Settings instance with values from environment or defaults
        """
        return cls(
            user_name=os.getenv("TOBBES_USER_NAME", DEFAULT_USER_NAME),
            database_path=Path(os.getenv("TOBBES_DATABASE_PATH", str(get_database_path()))),
            data_dir=Path(os.getenv("TOBBES_DATA_DIR", DATA_DIR)),
            temp_dir=Path(os.getenv("TOBBES_TEMP_DIR", TEMP_DIR)),
            chrome_path=os.getenv("TOBBES_CHROME_PATH"),
            debug_mode=os.getenv("TOBBES_DEBUG", "false").lower() == "true",
            log_level=os.getenv("TOBBES_LOG_LEVEL", "INFO"),
        )

    def to_dict(self) -> dict:
        """Convert settings to dictionary for serialization."""
        return {
            "app_version": self.app_version,
            "user_name": self.user_name,
            "database_type": self.database_type,
            "database_path": str(self.database_path),
            "data_dir": str(self.data_dir),
            "temp_dir": str(self.temp_dir),
            "chrome_path": self.chrome_path,
            "pdf_page_size": self.pdf_page_size,
            "enable_watermark": self.enable_watermark,
            "window_width": self.window_width,
            "window_height": self.window_height,
            "debug_mode": self.debug_mode,
            "log_level": self.log_level,
        }


# Global settings instance (lazy-loaded)
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get global settings instance.

    Lazy-loaded on first call. Loads from environment variables.

    Returns:
        Settings instance

    Example:
        >>> from config.settings import get_settings
        >>> settings = get_settings()
        >>> print(settings.database_path)
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


def reset_settings():
    """
    Reset global settings instance.

    Useful for testing - forces reload from environment on next get_settings() call.
    """
    global _settings
    _settings = None
