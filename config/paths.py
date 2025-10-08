"""
Path Configuration for Tobbes v2.

Centralized path management for projects and certificates.
"""

from pathlib import Path
import logging
import re
import sys
from typing import Optional

logger = logging.getLogger(__name__)


def get_app_root() -> Path:
    """
    Get application root directory.

    Returns:
        - Production (.exe): Directory where .exe is located
        - Development (script): Project root (tobbes_v2/)

    Example:
        Production: C:/Users/User/Desktop/TobbesWizard.exe → C:/Users/User/Desktop/
        Development: /Users/robs/DEV_projects/Traces/tobbes_v2/
    """
    if getattr(sys, 'frozen', False):
        # Running as compiled .exe (Nuitka/PyInstaller)
        app_root = Path(sys.executable).parent
        logger.debug(f"Running as .exe, app root: {app_root}")
    else:
        # Running as Python script (development)
        # __file__ = /Users/robs/.../tobbes_v2/config/paths.py
        # parent = config/, parent.parent = tobbes_v2/
        app_root = Path(__file__).parent.parent
        logger.debug(f"Running as script, app root: {app_root}")

    return app_root


def sanitize_order_number(order_number: str) -> str:
    """
    Sanitize order number for use as directory name.

    Removes/replaces characters that are invalid in directory names.

    Args:
        order_number: Order number (e.g., "TO-12345")

    Returns:
        Safe directory name (e.g., "TO-12345")

    Example:
        >>> sanitize_order_number("TO-12345")
        'TO-12345'
        >>> sanitize_order_number("TO/12345")
        'TO_12345'
    """
    # Replace invalid characters with underscore
    # Invalid: / \ : * ? " < > |
    safe_name = re.sub(r'[/\\:*?"<>|]', '_', order_number)
    return safe_name


def get_project_base_path() -> Path:
    """
    Get base path for all project directories.

    Structure (relative to .exe or project root):
        {app_root}/
        └── projects/
            ├── {order_number_1}/
            │   └── certificates/
            ├── {order_number_2}/
            │   └── certificates/
            └── ...

    Returns:
        Path to 'projects' directory (creates if doesn't exist)

    Example:
        Production: C:/Users/User/Desktop/projects/
        Development: /Users/robs/.../tobbes_v2/projects/
    """
    projects_path = get_app_root() / "projects"
    projects_path.mkdir(parents=True, exist_ok=True)
    return projects_path


def get_project_path(order_number: str) -> Path:
    """
    Get path for specific project directory.

    Args:
        order_number: Project order number (e.g., "TO-12345")

    Returns:
        Path to project directory (creates if doesn't exist)
    """
    safe_order_number = sanitize_order_number(order_number)
    project_path = get_project_base_path() / safe_order_number
    project_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Project path: {project_path} (order_number={order_number})")
    return project_path


def get_project_certificates_path(order_number: str) -> Path:
    """
    Get certificates directory path for project.

    Args:
        order_number: Project order number (e.g., "TO-12345")

    Returns:
        Path to certificates directory (creates if doesn't exist)
    """
    cert_path = get_project_path(order_number) / "certificates"
    cert_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Certificates path: {cert_path}")
    return cert_path


def get_certificate_path(order_number: str, certificate_filename: str) -> Path:
    """
    Get full path to a specific certificate file.

    Args:
        order_number: Project order number
        certificate_filename: Certificate filename (e.g., 'ART_123_Materialintyg_20250107.pdf')

    Returns:
        Full path to certificate file
    """
    return get_project_certificates_path(order_number) / certificate_filename


def get_project_reports_path(order_number: str) -> Path:
    """
    Get reports directory path for project.

    Args:
        order_number: Project order number (e.g., "TO-12345")

    Returns:
        Path to reports directory (creates if doesn't exist)
    """
    reports_path = get_project_path(order_number) / "reports"
    reports_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Reports path: {reports_path}")
    return reports_path


def get_database_path() -> Path:
    """
    Get database file path.

    Database is stored in projects directory for portability:
    - Development: {project_root}/projects/sparbarhet.db
    - Production (.exe): {exe_dir}/projects/sparbarhet.db

    Benefits:
    - Easy backup: copy entire projects/ folder
    - Easy cleanup: delete projects/ → all data gone
    - Portable: move projects/ between computers
    - Self-contained: .exe + projects/ is all you need

    Returns:
        Path to database file

    Example:
        Production: C:/Users/User/Desktop/projects/sparbarhet.db
        Development: /Users/robs/.../tobbes_v2/projects/sparbarhet.db
    """
    db_path = get_project_base_path() / "sparbarhet.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure projects/ exists
    logger.debug(f"Database path: {db_path}")
    return db_path
