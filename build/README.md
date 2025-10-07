# Build-guide för Tobbes v2

## Översikt

Tobbes v2 kompileras till standalone executables med **Nuitka** för distribution.

⚠️ **Viktigt:** Windows .exe måste byggas på Windows (eller via CI). Cross-kompilering från macOS → Windows stöds inte av Nuitka.

---

## Build-strategi

### Windows .exe (Produktionsbuild)

**Metod 1: GitHub Actions (Rekommenderat)**

1. Pusha kod till GitHub
2. Workflow `.github/workflows/build-windows.yml` körs automatiskt
3. Ladda ner artifact `TobbesWizard-Windows` från Actions-fliken
4. Zipped executable finns i `TobbesWizard-v2.0.0-windows.zip`

**Manuell trigger:**
- Gå till Actions → Build Windows EXE → Run workflow

**Metod 2: Lokal Windows-build**

Om du har tillgång till en Windows-maskin:

```bash
# Installera dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Kör build-script
python build/nuitka_build.py

# Output: dist/main.dist/TobbesWizard.exe
```

**Kompileringstid:** ~3-5 minuter
**Storlek:** ~35-50 MB (standalone directory)

---

### macOS .app (Utveckling/Test)

Lokal macOS build för testning (kräver Homebrew Python):

```bash
# Skapa virtual environment
/opt/homebrew/bin/python3 -m venv build/.venv
source build/.venv/bin/activate

# Installera dependencies
pip install -r requirements.txt
pip install -r requirements-build.txt

# Kör build
python build/nuitka_build.py

# Output: dist/main.dist/TobbesWizard.app
```

**OBS:** Apple Python (`/usr/bin/python3`) stöds INTE av Nuitka på macOS.

---

## Build-konfiguration

### nuitka_build.py

Python-script för automatiserad kompilering med Nuitka.

**Alternativ:**
```bash
python build/nuitka_build.py              # Standard standalone build
python build/nuitka_build.py --clean      # Rensa tidigare builds först
python build/nuitka_build.py --debug      # Build med debug-symbols
python build/nuitka_build.py --onefile    # Single-file executable (långsammare startup)
```

**Plattformsdetektering:**
- Windows: Lägger till `.exe`, ikon, version info, metadata
- macOS: Skapar `.app` bundle
- Linux: Skapar binary

### nuitka.config

Statisk konfigurationsfil med kompileringsalternativ.

**Viktiga settings:**
- `standalone = True` - Inkludera alla dependencies
- `enable-plugin = pyside6` - PySide6 support
- `include-data-dir = data/migrations` - Inkludera migrations
- `jobs = 4` - Parallell kompilering
- `lto = yes` - Link-time optimization

---

## Dependencies

### Runtime dependencies
```
PySide6 >=6.5.0
pandas >=2.0.0
openpyxl >=3.1.0
playwright >=1.40.0
```

**Systemkrav (Runtime):**
- Chrome/Chromium MÅSTE vara installerad (för PDF-generering)
- Windows 10/11, macOS 10.9+, eller Linux

### Build dependencies
```
nuitka >=1.9.0
ordered-set >=4.1.0
zstandard >=0.22.0
```

**Systemkrav (Build):**
- **Windows:** Microsoft C++ Build Tools
- **macOS:** Xcode Command Line Tools + Homebrew Python
- **Linux:** GCC

---

## Felsökning

### Windows: "Microsoft C++ Build Tools saknas"

**Lösning:**
1. Ladda ner från: https://visualstudio.microsoft.com/downloads/
2. Installera "Desktop development with C++"
3. Kör build igen

### macOS: "Apple Python is not supported"

**Lösning:**
```bash
# Installera Homebrew Python
brew install python@3.11

# Använd Homebrew Python
/opt/homebrew/bin/python3 build/nuitka_build.py
```

### "Chrome not found" vid körning

Standalone .exe kräver att Chrome/Chromium är installerad på målmaskinen.

**Kontrollera:**
```python
import shutil
print(shutil.which('chrome'))  # Ska returnera path
```

**Lösning för användare:**
- Installera Chrome från https://google.com/chrome

### Build tar för lång tid

Normal kompileringstid är 3-5 minuter.

**Optimeringar:**
- Använd `--jobs=8` för fler CPU-kärnor
- Skippa `--lto=yes` för snabbare (men större) builds
- Använd `--onefile` INTE (långsammare startup)

---

## Output-struktur

### Standalone mode (default)

```
dist/
└── main.dist/
    ├── TobbesWizard.exe        # Main executable
    ├── python311.dll           # Python runtime
    ├── PySide6/                # Qt libraries
    ├── _internal/              # Bundled dependencies
    └── data/
        └── migrations/         # Inkluderad data
```

**Storlek:** ~35-50 MB
**Distribution:** Zippa hela `main.dist/`-mappen

### Onefile mode

```
dist/
└── TobbesWizard.exe            # Single file (~50 MB)
```

**Storlek:** ~50-60 MB
**Startup:** Längre (extraherar till temp vid varje körning)
**Distribution:** Enklare (en fil)

**Rekommendation:** Använd standalone mode för bättre prestanda.

---

## CI/CD Pipeline

### GitHub Actions Workflow

**Triggers:**
- Push till `main` eller `develop`
- Manuell trigger (`workflow_dispatch`)
- Git tags `v*` (skapar release)

**Steg:**
1. Checkout kod
2. Setup Python 3.11
3. Installera dependencies
4. Kompilera med Nuitka
5. Zippa executable
6. Upload artifact (30 dagars retention)
7. Skapa GitHub Release (vid tags)

**Artifacts:**
- `TobbesWizard-Windows` - Komplett build
- `TobbesWizard-v2.0.0-windows.zip` - Distribuerbar zip

---

## Releases

### Skapa ny release

```bash
# Tag version
git tag -a v2.0.0 -m "Release v2.0.0"
git push origin v2.0.0

# GitHub Actions bygger och skapar release automatiskt
```

### Manual release

```bash
# Bygg lokalt
python build/nuitka_build.py --clean

# Zippa
cd dist
zip -r TobbesWizard-v2.0.0-windows.zip main.dist/

# Ladda upp till GitHub Releases manuellt
```

---

## Versionshantering

### version.txt

```
VERSION=2.0.0
BUILD_DATE=2025-10-07
BUILD_NUMBER=1
GIT_COMMIT=initial
PYTHON_VERSION=3.9+
```

**Uppdatera före release:**
1. Ändra `VERSION` i `version.txt`
2. Ändra `--windows-file-version` i `nuitka_build.py`
3. Commit och tagga

---

## Resurser

- **Nuitka Docs:** https://nuitka.net/doc/user-manual.html
- **PySide6 Deployment:** https://doc.qt.io/qtforpython/deployment.html
- **GitHub Actions:** https://docs.github.com/en/actions

---

*Senast uppdaterad: 2025-10-07*
