"""
Unit tests for Chrome Checker service.

Tests cover Chrome detection and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from services.chrome_checker import (
    has_system_chrome,
    get_chrome_path,
    ensure_chrome_installed,
    get_chrome_info,
    get_installation_instructions,
)


def test_has_system_chrome_when_chrome_exists():
    """Test Chrome detection when Chrome is found."""
    with patch("shutil.which", return_value="/usr/bin/google-chrome"):
        assert has_system_chrome() is True


def test_has_system_chrome_when_chrome_missing():
    """Test Chrome detection when Chrome is not found."""
    with patch("shutil.which", return_value=None):
        with patch("platform.system", return_value="Linux"):
            assert has_system_chrome() is False


def test_get_chrome_path_when_exists():
    """Test getting Chrome path when Chrome exists."""
    with patch("shutil.which", return_value="/usr/bin/google-chrome"):
        path = get_chrome_path()
        assert path == Path("/usr/bin/google-chrome")


def test_get_chrome_path_when_missing():
    """Test getting Chrome path when Chrome is missing."""
    with patch("shutil.which", return_value=None):
        with patch("platform.system", return_value="Linux"):
            path = get_chrome_path()
            assert path is None


def test_ensure_chrome_installed_success():
    """Test ensure_chrome_installed when Chrome is present."""
    with patch("services.chrome_checker.has_system_chrome", return_value=True):
        with patch("services.chrome_checker.get_chrome_path", return_value=Path("/usr/bin/chrome")):
            # Should not raise
            ensure_chrome_installed()


def test_ensure_chrome_installed_raises_when_missing():
    """Test ensure_chrome_installed raises error when Chrome is missing."""
    with patch("services.chrome_checker.has_system_chrome", return_value=False):
        with pytest.raises(EnvironmentError) as exc_info:
            ensure_chrome_installed()

        assert "Chrome eller Chromium krävs" in str(exc_info.value)
        assert "https://google.com/chrome" in str(exc_info.value)


def test_get_chrome_info_when_installed():
    """Test get_chrome_info when Chrome is installed."""
    with patch("services.chrome_checker.has_system_chrome", return_value=True):
        with patch("services.chrome_checker.get_chrome_path", return_value=Path("/usr/bin/chrome")):
            with patch("platform.system", return_value="Linux"):
                info = get_chrome_info()

                assert info["installed"] is True
                assert info["path"] == "/usr/bin/chrome"
                assert info["platform"] == "Linux"


def test_get_chrome_info_when_not_installed():
    """Test get_chrome_info when Chrome is not installed."""
    with patch("services.chrome_checker.has_system_chrome", return_value=False):
        with patch("services.chrome_checker.get_chrome_path", return_value=None):
            with patch("platform.system", return_value="Linux"):
                info = get_chrome_info()

                assert info["installed"] is False
                assert info["path"] is None
                assert info["platform"] == "Linux"


def test_get_installation_instructions_windows():
    """Test installation instructions for Windows."""
    with patch("platform.system", return_value="Windows"):
        instructions = get_installation_instructions()
        assert "Windows" in instructions
        assert "https://google.com/chrome" in instructions


def test_get_installation_instructions_macos():
    """Test installation instructions for macOS."""
    with patch("platform.system", return_value="Darwin"):
        instructions = get_installation_instructions()
        assert "macOS" in instructions
        assert "Applications-mappen" in instructions


def test_get_installation_instructions_linux():
    """Test installation instructions for Linux."""
    with patch("platform.system", return_value="Linux"):
        instructions = get_installation_instructions()
        assert "Linux" in instructions
        assert "apt-get" in instructions or "dnf" in instructions


def test_windows_specific_paths():
    """Test Windows-specific Chrome path detection."""
    with patch("shutil.which", return_value=None):
        with patch("platform.system", return_value="Windows"):
            # Mock Path.exists for Windows paths
            with patch.object(Path, "exists", return_value=True):
                assert has_system_chrome() is True


def test_macos_specific_paths():
    """Test macOS-specific Chrome path detection."""
    with patch("shutil.which", return_value=None):
        with patch("platform.system", return_value="Darwin"):
            # Mock Path.exists for macOS paths
            with patch.object(Path, "exists", return_value=True):
                assert has_system_chrome() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
