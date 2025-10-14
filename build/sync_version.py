#!/usr/bin/env python3
"""
Version Synchronization Script for Tobbes

Reads APP_VERSION from config/constants.py and synchronizes it to:
- build/assets/version.txt
- build/nuitka_build.py

Usage:
    python build/sync_version.py

Called automatically by pre-commit hook.
"""

import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime


def get_app_version():
    """Extract APP_VERSION from config/constants.py."""
    constants_path = Path(__file__).parent.parent / "config" / "constants.py"

    if not constants_path.exists():
        print(f"ERROR: Could not find {constants_path}")
        sys.exit(1)

    content = constants_path.read_text(encoding='utf-8')

    # Match: APP_VERSION = "1.12"
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)

    if not match:
        print("ERROR: Could not find APP_VERSION in config/constants.py")
        sys.exit(1)

    version = match.group(1)
    print(f"✓ Found APP_VERSION = '{version}'")
    return version


def get_git_info():
    """Get git commit hash and branch."""
    try:
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        commit = "unknown"

    try:
        branch = subprocess.check_output(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except:
        branch = "unknown"

    return commit, branch


def update_version_txt(version):
    """Update build/assets/version.txt."""
    version_file = Path(__file__).parent / "assets" / "version.txt"

    commit, branch = get_git_info()
    build_date = datetime.now().strftime("%Y-%m-%d")

    content = f"""VERSION={version}
BUILD_DATE={build_date}
GIT_COMMIT={commit}
GIT_BRANCH={branch}
PYTHON_VERSION=3.9+
"""

    version_file.write_text(content, encoding='utf-8')
    print(f"✓ Updated {version_file.relative_to(Path.cwd())}")


def main():
    """Main synchronization function."""
    print("=" * 60)
    print("Synchronizing version from config/constants.py")
    print("=" * 60)

    # Get version
    version = get_app_version()

    # Update version.txt (nuitka_build.py now reads directly from config)
    update_version_txt(version)

    print("=" * 60)
    print(f"✓ Version synchronized: {version}")
    print(f"✓ Note: build/nuitka_build.py reads directly from config/constants.py")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
