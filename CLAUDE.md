# CLAUDE.md - Tobbes 2.0 Spårbarhetsapplikation

## 🎯 Projektmål

### Primärt mål
Radikal ombyggnad av spårbarhetsapplikationen med fokus på **enkelhet, tydlighet och underhållbarhet**. Målet är att reducera kodbasen med 47% (16,000 → 8,500 rader) samtidigt som vi bibehåller 100% funktionalitet och lägger till 6 nya features.

### Affärsvärde
- **Kodreduktion:** 16,000 → 8,500 rader (-47%)
- **Underhållbarhet:** Små, läsbara funktioner (max 20-60 rader)
- **Testbarhet:** 80%+ code coverage (upp från 20%)
- **Distribution:** Standalone .exe med Nuitka (~35-50 MB)
- **Prestanda:** 20-30% snabbare genom native kompilering

### Kärnprinciper

1. **KISS (Keep It Simple, Stupid)**
   - En funktion = EN operation
   - Max 20 rader för helpers
   - Max 40-60 rader för orchestrators
   - Max 200 rader per fil

2. **Separation of Concerns**
   - UI gör BARA rendering
   - Operations gör BARA bearbetning
   - Database gör BARA persistence

3. **Database First**
   - All data börjar i databasen
   - Abstrakt databaslager
   - Lätt byta backend (SQLite → PostgreSQL)

4. **Dependency Injection**
   - Inga globala variabler
   - AppContext för state management
   - Testbara, rena funktioner

---

## 🛠️ Teknisk Stack

### Kärnteknologier
```python
# Backend & Logik
Python 3.9+           # Huvudspråk
pandas 2.0+           # Dataprocessning
openpyxl 3.1+         # Excel-hantering
sqlite3               # SQLite databas (inbyggd)

# GUI Framework
PySide6 6.5+          # Qt för Python (LGPL-licens)

# PDF-hantering
playwright 1.40+      # Browser automation för PDF-generering
                      # ⚠️ KRAV: System Chrome/Chromium måste vara installerad!

# Build & Distribution
nuitka 1.9+           # Python → Native .exe kompilering
ordered-set 4.1+      # Nuitka dependency
zstandard 0.22+       # Nuitka kompression

# Utvecklingsverktyg
pytest                # Testramverk
black                 # Kodformattering
mypy                  # Statisk typkontroll
ruff                  # Snabb linter
poetry                # Dependency management
```

### Systemkrav
- **OS:** Windows 10/11 (primärt), Linux, macOS
- **Chrome:** Google Chrome eller Chromium (OBLIGATORISKT!)
- **RAM:** Minimum 4 GB, rekommenderat 8 GB
- **Disk:** 500 MB för applikation
- **Python:** 3.9 eller senare (bara för utveckling, ej för .exe)

### Installation (Utveckling)
```bash
# Installera Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Installera dependencies
poetry install

# Kontrollera Chrome
python -c "import shutil; print('Chrome OK!' if shutil.which('chrome') else 'Chrome SAKNAS!')"

# Kör applikationen
poetry run tobbes
```

### Build till .exe
```bash
# Installera build-dependencies
poetry install --with build

# Kompilera
python build/nuitka_build.py

# Output: dist/TobbesWizard.exe (~35-50 MB)
```

---

## 📁 Projektstruktur

### Lagerad Arkitektur

```
┌─────────────────────────────────────────┐
│           UI Layer (PySide6)            │  ← BARA rendering
│  - Wizard pages                         │
│  - Widgets (charge_selector, etc.)      │
│  - Dialogs (certificate_types, etc.)    │
└─────────────────────────────────────────┘
                    ↓ uses
┌─────────────────────────────────────────┐
│         Application Context             │  ← State management
│  - current_project_id                   │
│  - database instance                    │
│  - user_info, app_config                │
└─────────────────────────────────────────┘
                    ↓ injected into
┌─────────────────────────────────────────┐
│         Operations Layer                │  ← Business logic (rena funktioner)
│  - import_ops.py                        │
│  - process_ops.py                       │
│  - report_ops.py                        │
│  - certificate_ops.py                   │
│  - update_ops.py                        │
│  - article_ops.py                       │
└─────────────────────────────────────────┘
                    ↓ uses
┌─────────────────────────────────────────┐
│          Domain Layer                   │  ← Core models
│  - models.py (dataclasses)              │
│  - rules.py (business rules)            │
│  - validators.py                        │
│  - exceptions.py                        │
└─────────────────────────────────────────┘
                    ↓ persisted by
┌─────────────────────────────────────────┐
│       Data Access Layer                 │  ← Database
│  - interface.py (ABC)                   │
│  - sqlite_db.py (implementation)        │
│  - postgresql_db.py (future)            │
└─────────────────────────────────────────┘
```

### Folder-struktur

```
tobbes_v2/
├── build/                     # Build-relaterade filer (Nuitka)
│   ├── nuitka.config          # Kompileringsalternativ
│   ├── nuitka_build.py        # Build-script
│   ├── requirements.txt       # Freeze:ade dependencies
│   └── assets/
│       ├── app.ico            # Windows-ikon
│       └── version.txt
│
├── domain/                    # Kärnlogik - NOLL dependencies
│   ├── models.py              # Dataklasser (Project, Article, etc.)
│   ├── rules.py               # Affärsregler
│   ├── validators.py          # Input-validering
│   └── exceptions.py          # Custom exceptions
│
├── data/                      # Data Access Layer
│   ├── interface.py           # Abstract Database Interface
│   ├── sqlite_db.py           # SQLite implementation
│   ├── migrations/            # Database migrations
│   │   ├── 001_initial.sql
│   │   ├── 002_global_articles.sql
│   │   ├── 003_certificate_types.sql
│   │   └── 004_article_notes_audit.sql
│   └── queries.py             # SQL queries som konstanter
│
├── operations/                # Business operations (rena funktioner)
│   ├── import_ops.py          # Filimport
│   ├── process_ops.py         # Matchning
│   ├── certificate_ops.py     # Certifikathantering
│   ├── report_ops.py          # Rapportgenerering
│   ├── update_ops.py          # Projekt-uppdatering (NY)
│   └── article_ops.py         # Global notes (NY)
│
├── ui/                        # UI Layer - BARA rendering
│   ├── wizard.py              # Main wizard
│   ├── pages/
│   │   ├── start_page.py      # ~100 rader max
│   │   ├── import_page.py     # ~100 rader max
│   │   ├── process_page.py    # ~80 rader max
│   │   ├── export_page.py     # ~120 rader max
│   │   └── update_page.py     # ~100 rader (NY)
│   ├── widgets/
│   │   ├── article_card.py    # ~60 rader (med global notes)
│   │   ├── cert_widget.py     # ~50 rader
│   │   ├── charge_selector.py # ~40 rader (NY - färgkodning)
│   │   └── progress_view.py   # ~40 rader
│   ├── dialogs/
│   │   ├── cert_types_dialog.py # ~80 rader (NY)
│   │   └── update_dialog.py     # ~60 rader (NY)
│   └── styles.py              # Qt styles + CSS
│
├── services/                  # Tjänster (stateful)
│   ├── excel_reader.py        # Excel-läsning
│   ├── pdf_service.py         # PDF operations
│   ├── chrome_checker.py      # Chrome-detektion (NY)
│   └── file_service.py        # Filhantering
│
├── config/
│   ├── settings.py            # App settings (.env)
│   ├── constants.py           # Konstanter
│   └── app_context.py         # AppContext class
│
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── fixtures/              # Test data
│
└── app.py                     # Entry point

TOTALT MÅL: ~8,500 rader (varav 3,000 är tester)
```

---

## 🏗️ Modulär arkitektur

### 1. Database First (Data Layer)

**Problem i v1:** Blandat ansvar mellan projekthantering och databasaccess.

**Lösning v2:** Abstract Database Interface med konkreta implementationer.

```python
# data/interface.py
from abc import ABC, abstractmethod

class DatabaseInterface(ABC):
    """Abstract database interface - gör det lätt att byta backend"""

    @abstractmethod
    def save_project(self, project: Project) -> int:
        pass

    @abstractmethod
    def get_project(self, project_id: int) -> Optional[Project]:
        pass

    @abstractmethod
    def save_global_article(self, article_number: str, description: str, notes: str) -> bool:
        """Spara/uppdatera global artikel med notes"""
        pass

    @abstractmethod
    def update_article_notes(self, article_number: str, notes: str, changed_by: str) -> bool:
        """Uppdatera BARA notes - audit-log skapas automatiskt via trigger"""
        pass
```

**SQLite Implementation:**
```python
# data/sqlite_db.py
class SQLiteDatabase(DatabaseInterface):
    """SQLite implementation av database interface"""

    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self._run_migrations()

    def save_project(self, project: Project) -> int:
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO projects (name, order_number) VALUES (?, ?)",
            (project.name, project.order_number)
        )
        self.conn.commit()
        return cursor.lastrowid
```

**Database Schema - Nyckelfunktioner:**

```sql
-- Global artikel-master (EN rad per artikelnummer)
CREATE TABLE global_articles (
    article_number TEXT PRIMARY KEY,
    description TEXT,
    notes TEXT,  -- ← GLOBAL anteckning (delas över alla projekt)
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Projekt-artiklar (projekt-specifik data)
CREATE TABLE project_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    article_number TEXT NOT NULL,
    quantity REAL,
    level_number TEXT,
    charge_number TEXT,
    verified BOOLEAN DEFAULT 0,

    FOREIGN KEY (article_number) REFERENCES global_articles(article_number),
    UNIQUE(project_id, article_number, level_number)  -- Tillåt flera nivåer
);

-- Audit-log för anteckningar (med trigger)
CREATE TABLE article_notes_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_number TEXT NOT NULL,
    old_notes TEXT,
    new_notes TEXT,
    changed_by TEXT,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger för automatisk audit-loggning
CREATE TRIGGER audit_article_notes_update
AFTER UPDATE OF notes ON global_articles
FOR EACH ROW
BEGIN
    INSERT INTO article_notes_audit (article_number, old_notes, new_notes, changed_by)
    VALUES (NEW.article_number, OLD.notes, NEW.notes, 'system');
END;
```

---

### 2. Operations Layer (Business Logic)

**Problem i v1:** Affärslogik inbäddad i UI-komponenter och monolitiska klasser.

**Lösning v2:** Rena funktioner med dependency injection.

```python
# operations/import_ops.py
def import_nivalista(file_path: Path) -> List[Article]:
    """
    Importera nivålista från Excel.

    ⚠️ REN FUNKTION - ingen databas-access här!
    Returnerar bara parsed data.

    Raises:
        ImportValidationError: Om filen är ogiltig
    """
    if not file_path.exists():
        raise ImportValidationError(
            f"Fil saknas: {file_path}",
            details={'file_path': str(file_path)}
        )

    df = read_excel(file_path)
    df = clean_dataframe(df)
    articles = _parse_articles_from_dataframe(df)
    return articles
```

**Användning i UI med dependency injection:**
```python
# ui/pages/import_page.py
from operations import import_ops
from domain.exceptions import ImportValidationError

class ImportPage(QWizardPage):
    def import_file(self):
        ctx = self.wizard().context  # Hämta AppContext

        try:
            # Anropa operation (ren funktion)
            articles = import_ops.import_nivalista(self.selected_file)

            # Spara till databas (via context)
            ctx.database.save_project_articles(ctx.current_project_id, articles)

            QMessageBox.information(self, "Klart", f"Importerade {len(articles)} artiklar")

        except ImportValidationError as e:
            QMessageBox.warning(self, "Import misslyckades", f"{e.message}\n\n{e.details}")
```

---

### 3. AppContext (State Management)

**Problem i v1:** Globala variabler, svårt att testa.

**Lösning v2:** Centraliserad AppContext som injiceras.

```python
# config/app_context.py
from dataclasses import dataclass

@dataclass
class AppContext:
    """
    Centraliserad applikationskontroll.
    Injiceras i UI-lager och skickas till operations.
    """
    database: DatabaseInterface
    current_project_id: Optional[int] = None
    user_name: str = "user"
    app_version: str = "2.0.0"

    def with_project(self, project_id: int) -> 'AppContext':
        """Skapa ny context med project_id"""
        return AppContext(
            database=self.database,
            current_project_id=project_id,
            user_name=self.user_name,
            app_version=self.app_version
        )
```

**Användning i Wizard:**
```python
# ui/wizard.py
from config.app_context import AppContext
from data import create_database

class TobbesWizard(QWizard):
    def __init__(self):
        super().__init__()

        # Skapa context
        db = create_database("sqlite", path="./sparbarhet.db")
        self.context = AppContext(database=db, user_name="Tobbes")

    def set_current_project(self, project_id: int):
        """Uppdatera context när projekt väljs"""
        self.context = self.context.with_project(project_id)
```

---

### 4. Custom Exceptions & Felhantering

**Problem i v1:** Generiska exceptions, svårt att hantera fel användarvänligt.

**Lösning v2:** Domain-specifika exceptions med detaljer.

```python
# domain/exceptions.py
class TobbesBaseException(Exception):
    """Bas för alla Tobbes-exceptions"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

class ImportValidationError(TobbesBaseException):
    """Fel vid import-validering"""
    pass

class DatabaseError(TobbesBaseException):
    """Databasfel"""
    pass

class CertificateError(TobbesBaseException):
    """Certifikatfel"""
    pass

class ReportGenerationError(TobbesBaseException):
    """Rapportgenereringsfel"""
    pass
```

**Felhantering i UI:**
```python
try:
    articles = import_ops.import_nivalista(file_path)
except ImportValidationError as e:
    # Användarvänligt meddelande
    QMessageBox.warning(self, "Import misslyckades", f"{e.message}\n\n{e.details}")
except DatabaseError as e:
    # Tekniskt fel
    QMessageBox.critical(self, "Databasfel", f"Kunde inte spara: {e.message}")
except Exception as e:
    # Oväntat fel - logga och visa generiskt
    logger.exception("Oväntat fel vid import")
    QMessageBox.critical(self, "Oväntat fel", "Något gick fel. Kontakta support.")
```

---

## 💡 Viktiga designbeslut

### 1. System Chrome - KRAV (ingen bundled browser)

**Varför:**
- System Chrome = redan installerad på de flesta Windows-datorer
- Trade-off: Användaren måste ha Chrome

**Implementation:**
```python
# services/chrome_checker.py
import shutil

def ensure_chrome_installed() -> None:
    """
    Kontrollera att Chrome/Chromium är installerad.

    Raises:
        EnvironmentError: Om Chrome inte hittas
    """
    if not has_system_chrome():
        raise EnvironmentError(
            "Chrome/Chromium krävs för PDF-generering men kunde inte hittas.\n\n"
            "Installera Chrome från: https://google.com/chrome"
        )

def has_system_chrome() -> bool:
    """Kontrollera om Chrome/Chromium finns installerad"""
    return (
        shutil.which('chrome') is not None or
        shutil.which('chromium') is not None or
        shutil.which('google-chrome') is not None
    )
```

**Användning:**
```python
# services/pdf_service.py
from playwright.sync_api import sync_playwright
from services.chrome_checker import ensure_chrome_installed

def html_to_pdf(html_content: str, output_path: Path) -> Path:
    """
    Konvertera HTML till PDF med system Chrome.

    KRAV: Chrome/Chromium måste vara installerad!
    """
    ensure_chrome_installed()  # Kastar exception om saknas

    with sync_playwright() as p:
        browser = p.chromium.launch(channel='chrome')  # Använd system Chrome
        page = browser.new_page()
        page.set_content(html_content)
        page.pdf(path=str(output_path), format='A4', print_background=True)
        browser.close()

    return output_path
```

---

### 2. Nuitka för .exe-kompilering

**Varför:**
- Native kod = 20-30% snabbare än Python
- Standalone .exe = ingen Python-installation behövs
- ~35-50 MB = acceptabel storlek (utan Chromium)

**Trade-off:** Längre kompileringstid (~3-5 min)

**Build-konfiguration:**
```python
# build/nuitka_build.py
def build_exe():
    """Kompilera med Nuitka"""
    cmd = [
        "python", "-m", "nuitka",
        "--standalone",
        "--windows-disable-console",
        "--enable-plugin=pyside6",
        "--include-package=playwright",
        "--output-dir=dist",
        "--output-filename=TobbesWizard.exe",
        "--windows-icon-from-ico=build/assets/app.ico",
        "tobbes_v2/app.py"
    ]
    subprocess.run(cmd)
```

---

### 3. Database First med SQLite

**Varför:**
- Strukturerad data med ACID-garantier
- Snabbare queries än JSON
- Portabel single-file databas
- Lätt byta till PostgreSQL senare

**Trade-off:** Lite mer komplexitet än JSON

**Migrations-hantering:**
```sql
-- data/migrations/001_initial.sql
CREATE TABLE IF NOT EXISTS projects (...);
CREATE TABLE IF NOT EXISTS global_articles (...);
CREATE TABLE IF NOT EXISTS project_articles (...);

-- data/migrations/002_global_articles.sql
ALTER TABLE global_articles ADD COLUMN notes TEXT;

-- data/migrations/003_certificate_types.sql
CREATE TABLE IF NOT EXISTS certificate_types (...);
```

---

### 4. Dependency Injection över globala variabler

**Varför:**
- Testbart - kan mocka dependencies
- Tydligt - ser exakt vilka dependencies en funktion har
- Flexibelt - lätt byta implementation

**Exempel:**
```python
# ❌ DÅLIGT - global state
db = get_database()

def update_article_notes(article_number: str, notes: str) -> bool:
    global db  # Svår att testa!
    return db.update_article_notes(article_number, notes)

# ✅ BRA - dependency injection
def update_article_notes(
    db: DatabaseInterface,  # Explicit dependency
    article_number: str,
    notes: str
) -> bool:
    return db.update_article_notes(article_number, notes)

# Test med mock
def test_update_notes():
    mock_db = MockDatabase()
    result = update_article_notes(mock_db, "ART-001", "Test notes")
    assert result == True
```

---

### 5. Rena funktioner för Operations

**Varför:**
- Input → Output (inga side effects där det går)
- Lätt att testa
- Lätt att förstå
- Kan köras parallellt

**Exempel:**
```python
# operations/certificate_ops.py
def guess_certificate_type(filename: str) -> str:
    """
    Gissa certifikattyp från filnamn.

    REN FUNKTION - inga side effects, ingen databas-access.
    """
    filename_lower = filename.lower()

    for keyword, cert_type in CERTIFICATE_TYPE_KEYWORDS.items():
        if keyword in filename_lower:
            return cert_type

    return "Övriga dokument"

# Test
def test_guess_certificate_type():
    assert guess_certificate_type("materialintyg_2024.pdf") == "Materialintyg"
    assert guess_certificate_type("svets_protokoll.pdf") == "Svetslogg"
```

---

## 🚀 Implementation Guidelines

### Kodstil

**Funktionslängder:**
```python
# ✅ BRA - Helper (max 20 rader)
def _find_charge_for_article(article: Article, inventory: List[InventoryItem]) -> InventoryItem | None:
    """
    Hitta matchande charge för artikel.
    Matchningsregler: Exakt match, ta senaste, filtrera tomma charges.
    """
    matching_items = [
        item for item in inventory
        if item.article_number == article.article_number
        and item.charge_number  # Filtrera bort tomma charges (admin posts)
    ]

    if matching_items:
        return matching_items[-1]  # Senaste
    return None

# ✅ BRA - Orchestrator (max 40-60 rader)
def generate_complete_report(
    project_id: int,
    articles: List[Article],
    certificates: List[Certificate],
    output_path: Path,
    progress_callback: Optional[Callable[[int], None]] = None
) -> Path:
    """
    Generera komplett PDF-rapport.

    Pipeline:
    1. Skapa HTML materialspecifikation
    2. Konvertera till PDF
    3. Slå samman med certifikat (streaming)
    4. Lägg till innehållsförteckning
    5. Spara slutgiltig rapport (idempotent)
    """
    try:
        # Steg 1: HTML
        if progress_callback:
            progress_callback(10)
        html = generate_html_report(articles)

        # Steg 2: PDF
        if progress_callback:
            progress_callback(20)
        main_pdf = html_to_pdf(html)

        # Steg 3: Merge (streaming för stora filer)
        if progress_callback:
            progress_callback(30)
        merged_pdf = _retry_operation(
            lambda: merge_pdfs_streaming(main_pdf, certificates)
        )

        # ... etc (totalt ~55 rader är OK för orchestrator)

    except Exception as e:
        raise ReportGenerationError(f"Misslyckades: {e}")
```

**Type hints:**
```python
def process_file(file_path: Path) -> pd.DataFrame:
    """Process Excel file and return DataFrame."""
    pass

@dataclass
class Article:
    number: str
    description: str
    quantity: float
    level: int = 0
```

**Felhantering:**
```python
try:
    df = pd.read_excel(file_path)
except FileNotFoundError:
    logger.error(f"File not found: {file_path}")
    raise ImportValidationError(f"Fil saknas: {file_path}")
except Exception as e:
    logger.exception("Unexpected error")
    raise
```

---

### UI/UX Principer

1. **Tydlig feedback** - Visa alltid vad som händer (progress callbacks)
2. **Förhindar fel** - Validera input direkt
3. **Undo möjlighet** - Tillåt användaren backa
4. **Keyboard shortcuts** - För power users
5. **Responsiv** - Använd threading för tunga operationer

---

### Säkerhet

- Validera all användarinput
- Använd Path för filoperationer (inte string concatenation)
- Logga aldrig känslig data
- Sanitize filnamn före sparning
- Begränsa filstorlekar

---

## 📊 Datamodeller

### Kärnentiteter

```python
# domain/models.py
@dataclass
class GlobalArticle:
    """Global artikel - delas över alla projekt"""
    article_number: str
    description: str = ""
    notes: str = ""  # ← Global anteckning (ny feature)
    first_seen_at: datetime = None
    last_updated_at: datetime = None

@dataclass
class Article:
    """Artikel i specifikt projekt"""
    project_id: int
    article_number: str
    quantity: float = 0.0
    level_number: str = ""
    charge_number: str = ""
    verified: bool = False

    # Populated från global_articles
    description: str = ""
    notes: str = ""  # ← Visas från global
    id: int = None

@dataclass
class InventoryItem:
    """
    Lagerlogg-post (från lagerlogg).

    Representerar en charge/batch av material i lager.

    VIKTIGT: charge_number KAN vara tom för:
    - Admin posts (administrativa rader)
    - Artiklar under mottagning
    - Andra rader utan specifik charge

    Tomma charges filtreras bort vid matchning.
    quantity KAN vara negativ (uttag/withdrawals).
    """
    project_id: int
    article_number: str
    charge_number: str = ""  # Tillåt tom för admin posts, artiklar under mottagning
    quantity: float = 0.0  # Kan vara negativ för uttag
    batch_id: str = None
    location: str = None
    received_date: datetime = None
    id: int = None

@dataclass
class Certificate:
    project_id: int
    article_number: str
    file_path: Path
    certificate_type: str
    original_name: str
    page_count: int = 0

@dataclass
class ArticleUpdate:
    """Representerar en uppdatering (ny feature)"""
    article_number: str
    update_type: str  # 'lagerlogg' eller 'nivalista'
    old_value: Any
    new_value: Any
    field_name: str
    affects_certificates: bool = False
```

---

## 🧪 Testsstrategi

### Testnivåer
1. **Unit tests** - Varje operation för sig
2. **Integration tests** - Operations + Database
3. **System tests** - Komplett flöde
4. **UI tests** - Manual testing

### Exempel

```python
# tests/unit/test_import_ops.py
def test_import_nivalista_validates_file_exists():
    """Test att import validerar att fil finns"""
    with pytest.raises(ImportValidationError) as exc_info:
        import_ops.import_nivalista(Path("nonexistent.xlsx"))

    assert "Fil saknas" in str(exc_info.value.message)

# tests/unit/test_article_ops.py
def test_global_notes_shared_across_projects():
    """Test att notes delas mellan projekt"""
    db = create_database("sqlite", path=":memory:")

    # Projekt 1
    article_ops.update_article_notes(db, "ART-001", "Kräver kontroll")

    # Projekt 2 ser samma notes
    article = db.get_global_article("ART-001")
    assert article.notes == "Kräver kontroll"

# tests/integration/test_report_generation.py
def test_generate_complete_report_end_to_end():
    """Test komplett rapportgenerering"""
    # Setup
    db = create_database("sqlite", path=":memory:")
    project_id = db.save_project(Project(name="Test", order_number="TO-001"))

    # Import articles
    articles = import_ops.import_nivalista(Path("fixtures/nivalista.xlsx"))
    db.save_project_articles(project_id, articles)

    # Generate report
    output = report_ops.generate_complete_report(
        project_id,
        articles,
        [],
        Path("/tmp/report.pdf")
    )

    assert output.exists()
    assert output.stat().st_size > 0
```

---

## 🆕 Nya funktioner i 2.0

### 1. Global anteckningar för artiklar

**Koncept:** Ett notes-fält på global artikel som delas över ALLA projekt.

**Användning:**
```python
# operations/article_ops.py
def update_article_notes(
    db: DatabaseInterface,
    article_number: str,
    notes: str,
    changed_by: str = "user"
) -> bool:
    """
    Uppdatera anteckningar GLOBALT.
    Påverkar ALLA projekt där artikeln finns.
    Audit-log skapas automatiskt via trigger.
    """
    return db.update_article_notes(article_number, notes, changed_by)
```

**UI Widget:**
```python
# ui/widgets/article_card.py
class ArticleCard(QWidget):
    def _setup_ui(self):
        # Anteckningar (redigerbar)
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Anteckningar (delas globalt)...")

        # Debounce timer - 1.5s
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self._save_notes)

        self.notes_edit.textChanged.connect(lambda: self.save_timer.start(1500))
```

---

### 2. Uppdatera projekt

**Koncept:** Importera nya versioner av nivålista/lagerlogg, jämför, låt användare välja uppdateringar.

```python
# operations/update_ops.py
def compare_articles_for_update(
    current_articles: List[Article],
    new_data: List[Dict],
    update_type: str
) -> List[ArticleUpdate]:
    """Jämför befintliga artiklar med ny data"""
    updates = []

    for new_item in new_data:
        current = _find_article(current_articles, new_item['article_number'])

        if current and current.charge_number != new_item.get('charge_number', ''):
            updates.append(ArticleUpdate(
                article_number=new_item['article_number'],
                old_value=current.charge_number,
                new_value=new_item['charge_number'],
                field_name='charge_number',
                affects_certificates=True  # Ta bort certs vid charge-uppdatering
            ))

    return updates
```

---

### 3. Hantera certifikattyper

**Koncept:** Global + projektspecifika certifikattyper.

```python
# operations/certificate_ops.py
def get_all_certificate_types(db: DatabaseInterface, project_id: int = None) -> List[str]:
    """Hämta alla tillgängliga certifikattyper (global + projektspecifik)"""
    global_types = db.get_global_certificate_types()
    project_types = db.get_project_certificate_types(project_id) if project_id else []
    return project_types + global_types
```

---

### 4. Charge Selector Widget

**Koncept:** Smart dropdown med färgkodning (grå/grön/gul).

```python
# ui/widgets/charge_selector.py
class ChargeSelector(QWidget):
    """
    Smart charge-väljare:
    - Grå: Manuell inmatning (inga val)
    - Grön: Matchad (ett val)
    - Gul: Val krävs (flera val)
    """

    def __init__(self, available_charges: List[str], current_value: str = ""):
        # ...
        if len(available_charges) == 0:
            self._set_gray_style()
        elif len(available_charges) == 1:
            self._set_green_style()
            self.combo.setCurrentText(available_charges[0])
        else:
            self._set_yellow_style()
```

---

### 5. Watermark-funktion

**Koncept:** CSS-baserad watermark (FA-TEC).

```python
# ui/styles.py
def get_css_with_watermark() -> tuple[str, str]:
    """Returnera CSS med watermark"""
    css = """
    body.watermarked::before {
        content: "FA-TEC";
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) rotate(-45deg);
        font-size: 120px;
        color: rgba(0, 0, 0, 0.05);
        z-index: -1;
    }
    """
    return css, "watermarked"
```

---

## 🔍 Felsökning

### Vanliga problem

#### Chrome inte installerad
```python
# Symptom: EnvironmentError vid PDF-generering
# Lösning:
# 1. Installera Chrome från https://google.com/chrome
# 2. Verifiera: shutil.which('chrome')
```

#### Import misslyckas
```python
# Debug import-validering
try:
    articles = import_ops.import_nivalista(file_path)
except ImportValidationError as e:
    logger.error(f"Import failed: {e.message}")
    logger.error(f"Details: {e.details}")
```

#### Matchning hittar inga resultat
```python
# Debug matchningslogik
logger.debug(f"Searching for: {article.article_number}")
matches = [item for item in inventory if item.article_number == article.article_number]
logger.debug(f"Found {len(matches)} matches")
```

---

## 📈 Prestandaoptimering

### Pandas optimeringar
```python
# Använd vectorized operations
df['new_col'] = df['col1'] * df['col2']  # Bra

# Läs bara nödvändiga kolumner
df = pd.read_excel(file, usecols=['A', 'B', 'C'])

# Använd chunks för stora filer
for chunk in pd.read_excel(file, chunksize=1000):
    process(chunk)
```

### Qt optimeringar
```python
# Använd QThread för tunga operationer
class MatchingThread(QThread):
    progress = Signal(int)

    def run(self):
        for i in range(100):
            self.progress.emit(i)
            # Process...
```

### Rapport-pipeline robusthet
```python
# Streaming merge för stora PDF-filer
def merge_pdfs_streaming(main_pdf: Path, certificates: List[Path]) -> bytes:
    """Merge PDF:er utan att läsa allt i minnet"""
    # Implementation...

# Retry-logik med exponential backoff
def _retry_operation(operation: Callable, max_retries: int = 3) -> any:
    for attempt in range(max_retries):
        try:
            return operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)  # 1s, 2s, 4s
```

---

## 🤝 För AI-assistenter

### När du hjälper till med detta projekt:

1. **Följ lagerad arkitektur**
   - UI → AppContext → Operations → Domain → Database
   - ALDRIG blanda lager (t.ex. databas-queries i UI)

2. **Använd dependency injection**
   - Alla operations får `db: DatabaseInterface` som parameter
   - Inga globala variabler

3. **Skriv rena funktioner**
   - Helpers: Max 20 rader
   - Orchestrators: Max 40-60 rader
   - Tydliga input/output

4. **Använd custom exceptions**
   - `ImportValidationError`, `DatabaseError`, etc.
   - Alltid med message + details

5. **Testa först**
   - Skriv tests tillsammans med ny funktionalitet
   - Mock DatabaseInterface för unit tests

6. **Dokumentera väl**
   - Docstrings på alla publika funktioner
   - Förklara "varför", inte bara "vad"

### Exempel på bra kodgenerering:

```python
def update_article_charge(
    db: DatabaseInterface,
    project_id: int,
    article_number: str,
    new_charge: str
) -> bool:
    """
    Uppdatera chargenummer för artikel.

    Om charge ändras: Ta bort befintliga certifikat för artikeln.

    Args:
        db: Database instance (injected)
        project_id: Projekt-ID
        article_number: Artikelnummer
        new_charge: Nytt chargenummer

    Returns:
        True om uppdateringen lyckades

    Raises:
        DatabaseError: Om uppdateringen misslyckades
    """
    logger.debug(f"Updating charge for {article_number} to {new_charge}")

    try:
        # Hämta artikel
        article = db.get_article(project_id, article_number)

        if article.charge_number != new_charge:
            # Uppdatera charge
            article.charge_number = new_charge
            db.update_project_article(article)

            # Ta bort certifikat (ny charge = nya certifikat behövs)
            db.delete_certificates_for_article(article_number, project_id)
            logger.info(f"Updated charge and removed certificates for {article_number}")

        return True

    except Exception as e:
        logger.exception(f"Failed to update charge for {article_number}")
        raise DatabaseError(
            f"Kunde inte uppdatera charge: {e}",
            details={'article_number': article_number, 'new_charge': new_charge}
        )
```

---

## 🏁 Success Metrics

### Tekniska mål
- ✅ **Kodreduktion:** 16,000 → 8,500 rader (-47%)
- ✅ **Max funktion:** 350 → 20-60 rader
- ✅ **Max fil:** 1,275 → 200 rader
- ✅ **Test coverage:** 20% → 80%
- ✅ **.exe storlek:** ~35-50 MB (standalone)
- ✅ **Startup tid:** <1s (native kod)

### Funktionella mål
- ✅ **100% feature parity** med v1
- ✅ **6 nya funktioner** (global notes, update, cert types, charge selector, watermark, Chrome checker)
- ✅ **Noll data loss** vid migration
- ✅ **Samma eller bättre prestanda**
- ✅ **Enkel distribution** (standalone .exe)

---

## 📚 Referenser

### Utvecklingsplan
- **[new_tobbes_plan.md](./new_tobbes_plan.md)** - Komplett 6-veckors utvecklingsplan

### Externa resurser
- [PySide6 Documentation](https://doc.qt.io/qtforpython/)
- [Pandas User Guide](https://pandas.pydata.org/docs/user_guide/)
- [Playwright Documentation](https://playwright.dev/python/)
- [Nuitka Documentation](https://nuitka.net/)
- [Poetry Documentation](https://python-poetry.org/)

---

*Version: 2.0.0*
*Senast uppdaterad: 2025-10-06*
*Status: Ready for Implementation*
