"""
Chrome/Chromium checker service.

This module ensures that Chrome or Chromium is installed on the system,
which is REQUIRED for PDF generation via Playwright.

According to CLAUDE.md:
- System Chrome is required (no bundled Chromium to keep .exe size down)
- Trade-off: User must have Chrome installed
- Bundle size: ~35-50 MB without Chromium vs ~150 MB with
"""

import shutil
import logging
import platform
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def has_system_chrome() -> bool:
    """
    Check if Chrome or Chromium is installed on the system.

    Returns:
        True if Chrome/Chromium is found, False otherwise
    """
    # Common Chrome executable names
    chrome_names = [
        "chrome",
        "chromium",
        "google-chrome",
        "google-chrome-stable",
        "chrome.exe",
        "chromium.exe",
    ]

    for name in chrome_names:
        if shutil.which(name):
            logger.debug(f"Found Chrome: {name}")
            return True

    # Windows-specific paths
    if platform.system() == "Windows":
        windows_paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
        ]
        for path in windows_paths:
            if path.exists():
                logger.debug(f"Found Chrome at: {path}")
                return True

    # macOS-specific paths
    elif platform.system() == "Darwin":
        macos_paths = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for path in macos_paths:
            if path.exists():
                logger.debug(f"Found Chrome at: {path}")
                return True

    logger.warning("Chrome/Chromium not found on system")
    return False


def get_chrome_path() -> Optional[Path]:
    """
    Get the path to Chrome/Chromium executable.

    Returns:
        Path to Chrome executable, or None if not found
    """
    # Try shutil.which first (works on all platforms)
    chrome_names = ["chrome", "chromium", "google-chrome", "google-chrome-stable"]
    for name in chrome_names:
        path = shutil.which(name)
        if path:
            return Path(path)

    # Windows-specific paths
    if platform.system() == "Windows":
        windows_paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
        ]
        for path in windows_paths:
            if path.exists():
                return path

    # macOS-specific paths
    elif platform.system() == "Darwin":
        macos_paths = [
            Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
        for path in macos_paths:
            if path.exists():
                return path

    return None


def ensure_chrome_installed() -> None:
    """
    Ensure Chrome/Chromium is installed on the system.

    This is a hard requirement for PDF generation.

    Raises:
        EnvironmentError: If Chrome/Chromium is not found

    Example:
        >>> ensure_chrome_installed()  # Raises if Chrome not found
        >>> # Continue with PDF generation...
    """
    if not has_system_chrome():
        raise EnvironmentError(
            "Chrome eller Chromium krävs för PDF-generering men kunde inte hittas.\n\n"
            "Installera Chrome från: https://google.com/chrome\n"
            "Eller Chromium från: https://www.chromium.org/getting-involved/download-chromium/\n\n"
            "Efter installation, starta om applikationen."
        )

    chrome_path = get_chrome_path()
    if chrome_path:
        logger.info(f"Chrome found at: {chrome_path}")
    else:
        logger.warning("Chrome detected but path could not be determined")


def get_chrome_info() -> dict:
    """
    Get information about installed Chrome/Chromium.

    Returns:
        Dict with Chrome information:
        - installed: bool
        - path: str or None
        - platform: str
    """
    installed = has_system_chrome()
    path = get_chrome_path()

    return {
        "installed": installed,
        "path": str(path) if path else None,
        "platform": platform.system(),
    }


def get_installation_instructions() -> str:
    """
    Get platform-specific Chrome installation instructions.

    Returns:
        User-friendly installation instructions as string
    """
    system = platform.system()

    if system == "Windows":
        return (
            "För Windows:\n"
            "1. Besök https://google.com/chrome\n"
            "2. Ladda ner Chrome för Windows\n"
            "3. Kör installationsprogrammet\n"
            "4. Starta om Tobbes efter installation"
        )
    elif system == "Darwin":
        return (
            "För macOS:\n"
            "1. Besök https://google.com/chrome\n"
            "2. Ladda ner Chrome för Mac\n"
            "3. Dra Chrome till Applications-mappen\n"
            "4. Starta om Tobbes efter installation"
        )
    elif system == "Linux":
        return (
            "För Linux:\n"
            "Ubuntu/Debian:\n"
            "  sudo apt-get install google-chrome-stable\n\n"
            "Fedora/RHEL:\n"
            "  sudo dnf install google-chrome-stable\n\n"
            "Eller installera Chromium:\n"
            "  sudo apt-get install chromium-browser\n\n"
            "Starta om Tobbes efter installation"
        )
    else:
        return (
            "Installera Chrome eller Chromium:\n"
            "Chrome: https://google.com/chrome\n"
            "Chromium: https://www.chromium.org/getting-involved/download-chromium/"
        )
