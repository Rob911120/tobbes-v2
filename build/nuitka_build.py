#!/usr/bin/env python3
"""
Nuitka Build Script for Tobbes v2

Kompilerar Python-koden till en standalone .exe med Nuitka.

KRAV:
- Nuitka installerad: pip install nuitka ordered-set zstandard
- Windows: Microsoft C++ Build Tools (för Windows builds)
- macOS: Xcode Command Line Tools

Användning:
    python build/nuitka_build.py [--clean] [--debug]

Flags:
    --clean     Rensa tidigare build-filer
    --debug     Bygg med debug-symbols (större .exe)
"""

import sys
import shutil
import subprocess
from pathlib import Path
import argparse

# Import version from constants
sys.path.insert(0, str(Path(__file__).parent.parent))
from config.constants import APP_VERSION, APP_NAME


def main():
    """Main build function."""
    parser = argparse.ArgumentParser(description="Build Tobbes v2 with Nuitka")
    parser.add_argument("--clean", action="store_true", help="Clean previous builds")
    parser.add_argument("--debug", action="store_true", help="Build with debug symbols")
    parser.add_argument("--onefile", action="store_true", help="Build as single .exe file")
    args = parser.parse_args()

    # Project root
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")

    # Entry point
    entry_point = project_root / "main.py"
    if not entry_point.exists():
        print(f"ERROR: Entry point not found: {entry_point}")
        sys.exit(1)

    # Clean previous builds
    if args.clean:
        print("Cleaning previous builds...")
        dist_dir = project_root / "dist"
        build_dir = project_root / "build" / "main.build"

        if dist_dir.exists():
            shutil.rmtree(dist_dir)
            print(f"  Removed: {dist_dir}")

        if build_dir.exists():
            shutil.rmtree(build_dir)
            print(f"  Removed: {build_dir}")

    # Build Nuitka command
    cmd = [
        sys.executable, "-m", "nuitka",

        # Build mode
        "--standalone",

        # Output
        "--output-dir=dist",

        # Plugins
        "--enable-plugin=pyside6",

        # Include packages
        "--include-package=operations",
        "--include-package=domain",
        "--include-package=data",
        "--include-package=services",
        "--include-package=config",
        "--include-package=ui",

        # Include data
        "--include-data-dir=data/migrations=data/migrations",

        # Performance
        "--jobs=4",
        "--lto=yes",

        # Python flags
        "--python-flag=no_site",
        "--python-flag=no_warnings",

        # Follow imports
        "--follow-imports",

        # Assume yes for downloads
        "--assume-yes-for-downloads",
    ]

    # Platform-specific options
    if sys.platform == "win32":
        windows_opts = [
            "--windows-disable-console",
            "--windows-company-name=FA-TEC",
            f"--windows-product-name={APP_NAME}",
            f"--windows-file-version={APP_VERSION}",
            f"--windows-product-version={APP_VERSION}",
            "--windows-file-description=Sparbarhetsguide for materialcertifikat",
        ]

        # Add icon if file exists (optional)
        icon_path = project_root / "build" / "assets" / "app.ico"
        if icon_path.exists():
            windows_opts.append(f"--windows-icon-from-ico={icon_path}")
            print(f"✓ Using custom icon: {icon_path}")
        else:
            print(f"ℹ  No custom icon found, using default Python icon")

        cmd.extend(windows_opts)
        output_name = "TobbesWizard.exe"
    elif sys.platform == "darwin":
        # macOS
        cmd.extend([
            "--macos-create-app-bundle",
            "--macos-app-name=TobbesWizard",
        ])
        output_name = "TobbesWizard.app"
    else:
        # Linux
        output_name = "TobbesWizard"

    # Onefile mode
    if args.onefile:
        cmd.append("--onefile")
        print("Building as single executable (onefile mode)...")
    else:
        print("Building as standalone directory...")

    # Debug mode
    if args.debug:
        cmd.extend([
            "--debug",
            "--debugger",
        ])
        print("Building with debug symbols...")

    # Entry point
    cmd.append(str(entry_point))

    # Print command
    print("\nNuitka command:")
    print(" ".join(cmd))
    print("\n" + "=" * 60)

    # Run build
    print("Starting Nuitka compilation...")
    print("This may take 3-5 minutes...")
    print("=" * 60 + "\n")

    try:
        result = subprocess.run(cmd, cwd=project_root, check=True)

        print("\n" + "=" * 60)
        print("BUILD SUCCESSFUL!")
        print("=" * 60)

        # Find output
        dist_dir = project_root / "dist"
        if args.onefile:
            output_path = dist_dir / output_name
        else:
            output_path = dist_dir / "main.dist" / output_name

        if output_path.exists():
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"\nOutput: {output_path}")
            print(f"Size: {size_mb:.1f} MB")
        else:
            print(f"\nOutput directory: {dist_dir}")

        print("\nNästa steg:")
        print("1. Testa .exe: cd dist && ./TobbesWizard")
        print("2. Verifiera Chrome-check fungerar")
        print("3. Testa komplett workflow")

        return 0

    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 60)
        print("BUILD FAILED!")
        print("=" * 60)
        print(f"\nError code: {e.returncode}")
        print("\nFelsökning:")
        print("1. Kontrollera att Nuitka är installerad: pip install nuitka")
        print("2. På Windows: Installera Microsoft C++ Build Tools")
        print("3. På macOS: Installera Xcode Command Line Tools")
        print("4. Kör med --clean flag: python build/nuitka_build.py --clean")
        return 1

    except KeyboardInterrupt:
        print("\n\nBuild avbruten av användaren")
        return 130


if __name__ == "__main__":
    sys.exit(main())
