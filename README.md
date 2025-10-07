# Tobbes v2 - Spårbarhetsguiden

**Version 2.0** - Komplett ombyggnad med modulär arkitektur och database-first design.

## Vad är nytt i v2?

- ✅ **Database-first arkitektur** med SQLite (enkelt byta till PostgreSQL)
- ✅ **Modulär design** - Operations, services och processors i separata moduler
- ✅ **Global article notes** - Noteringar delas över alla projekt
- ✅ **Audit log** - Komplett historik över ändringar
- ✅ **Project updates** - Uppdatera projekt från ny data
- ✅ **Custom certificate types** - Globala + projektspecifika
- ✅ **Standalone .exe** med Nuitka (ingen Python-installation krävs)
- ✅ **47% mindre kod** (16,000 → 8,500 rader)

## Snabbstart

### Installation

```bash
# Klona projektet
cd /Users/robs/DEV_projects/Traces/tobbes_v2

# Installera dependencies
pip3 install -r requirements.txt

# Installera dev-dependencies (för utveckling)
pip3 install -r requirements-dev.txt

# Installera Playwright browsers för PDF-generering
python3 -m playwright install chromium
```

### Kör applikationen

```bash
python3 main.py
```

## Projektstruktur

```
tobbes_v2/
├── domain/              # Domain models och affärsregler
│   ├── models.py       # Dataclasser (Project, Article, Certificate, etc.)
│   ├── exceptions.py   # Custom exceptions
│   ├── validators.py   # Input-validering
│   └── rules.py        # Affärsregler
│
├── data/               # Database layer
│   ├── interface.py    # DatabaseInterface ABC
│   ├── sqlite_db.py    # SQLite implementation
│   ├── queries.py      # SQL queries
│   └── migrations/     # Database migrations
│       ├── 001_initial.sql
│       ├── 002_global_articles.sql
│       ├── 003_certificate_types.sql
│       └── 004_article_notes_audit.sql
│
├── operations/         # Business logic operations
│   ├── import_ops.py   # Import nivålista/lagerlogg
│   ├── process_ops.py  # Matchning av artiklar
│   ├── certificate_ops.py  # Certifikathantering
│   ├── article_ops.py  # Artikel-operations (notes, etc.)
│   ├── update_ops.py   # Projektuppdateringar
│   └── report_ops.py   # Rapport-generering
│
├── services/           # Infrastructure services
│   ├── excel_reader.py
│   ├── pdf_service.py
│   ├── chrome_checker.py  # Chrome browser-detektion
│   └── file_service.py
│
├── ui/                 # User interface (PySide6)
│   ├── wizard.py       # Main wizard
│   ├── pages/          # Wizard pages
│   │   ├── start_page.py
│   │   ├── import_page.py
│   │   ├── process_page.py
│   │   ├── export_page.py
│   │   └── update_page.py
│   ├── widgets/        # Reusable widgets
│   │   ├── article_card.py
│   │   ├── charge_selector.py
│   │   └── cert_widget.py
│   ├── dialogs/        # Dialogs
│   │   └── cert_types_dialog.py
│   └── styles.py       # CSS styles
│
├── config/             # Configuration
│   ├── app_context.py  # Application context
│   ├── settings.py     # Settings från .env
│   └── constants.py    # Konstanter
│
├── utils/              # Utilities
│
├── tests/              # Tests
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── build/              # Build configuration
│   ├── nuitka.config
│   ├── nuitka_build.py
│   └── assets/
│
├── requirements.txt    # Core dependencies
├── requirements-dev.txt  # Dev dependencies
├── .env.example        # Environment variables template
└── main.py            # Application entry point
```

## Utveckling

### Köra tester

```bash
# Kör alla tester
pytest

# Med coverage
pytest --cov=. --cov-report=html

# Specifik testfil
pytest tests/unit/test_import_ops.py
```

### Kodkvalitet

```bash
# Format kod med black
black .

# Lint med ruff
ruff check .

# Type checking med mypy
mypy .
```

### Bygga .exe med Nuitka

```bash
# Install build dependencies
pip3 install -r requirements-dev.txt

# Build
python3 build/nuitka_build.py
```

## Databas

Projektet använder SQLite för datalagring. Databasen skapas automatiskt vid första körningen.

### Migrations

Migrations körs automatiskt när applikationen startar. För att köra manuellt:

```python
from data.sqlite_db import SQLiteDatabase

db = SQLiteDatabase("path/to/database.db")
# Migrations körs automatiskt i __init__
```

### Database Schema

Se `data/migrations/` för fullständigt schema.

**Huvudtabeller:**
- `projects` - Projektmetadata
- `project_articles` - Projektspecifika artiklar
- `global_articles` - Globala artikeldata (notes delas över projekt)
- `inventory_items` - Lagerlogg-data med charges
- `certificates` - PDF-certifikat
- `certificate_types` - Globala certifikattyper
- `project_certificate_types` - Projektspecifika certifikattyper
- `article_notes_audit` - Audit log för article notes

## Systemkrav

- **OS:** Windows 10/11, macOS, Linux
- **Python:** 3.9+
- **RAM:** 4 GB minimum, 8 GB rekommenderat
- **Disk:** 500 MB för applikation + projektutrymme
- **Browser:** Chrome/Chromium (för PDF-generering)

## Licens

Proprietär - För internt bruk

## Support

För frågor eller problem, kontakta utvecklingsteamet.

---

**Version:** 2.0.0
**Senast uppdaterad:** 2025-10-06
