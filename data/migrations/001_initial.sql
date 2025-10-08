-- Migration 001: Initial database schema
-- Creates core tables for projects, articles, inventory, and certificates

-- ==================== Projects Table ====================
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    order_number TEXT NOT NULL UNIQUE,  -- e.g., "TO-12345"
    customer TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL  -- Username
);

-- Index for faster lookups by order number
CREATE INDEX IF NOT EXISTS idx_projects_order_number ON projects(order_number);

-- Trigger to update updated_at on projects
CREATE TRIGGER IF NOT EXISTS update_projects_timestamp
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ==================== Project Articles Table ====================
-- Stores project-specific articles from nivålista/BOM
CREATE TABLE IF NOT EXISTS project_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    article_number TEXT NOT NULL,
    description TEXT,
    quantity REAL NOT NULL DEFAULT 0.0,
    level TEXT,  -- e.g., "1", "1.1", "1.1.1" (stored as text for flexibility)
    parent_article TEXT,  -- Reference to parent article number
    charge_number TEXT,  -- Selected charge for this article
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, article_number, level)  -- Allow same article at different levels
);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_project_articles_project ON project_articles(project_id);
CREATE INDEX IF NOT EXISTS idx_project_articles_article ON project_articles(article_number);
CREATE INDEX IF NOT EXISTS idx_project_articles_parent ON project_articles(parent_article);

-- Trigger to update updated_at on project_articles
CREATE TRIGGER IF NOT EXISTS update_project_articles_timestamp
AFTER UPDATE ON project_articles
BEGIN
    UPDATE project_articles SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ==================== Inventory Items Table ====================
-- Stores inventory/lagerlogg data with charges
CREATE TABLE IF NOT EXISTS inventory_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    article_number TEXT NOT NULL,
    charge_number TEXT NOT NULL,
    batch_id TEXT,  -- Optional batch identifier
    quantity REAL NOT NULL DEFAULT 0.0,
    location TEXT,  -- Storage location
    received_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Indexes for charge lookups
CREATE INDEX IF NOT EXISTS idx_inventory_project ON inventory_items(project_id);
CREATE INDEX IF NOT EXISTS idx_inventory_article ON inventory_items(article_number);
CREATE INDEX IF NOT EXISTS idx_inventory_charge ON inventory_items(charge_number);
CREATE INDEX IF NOT EXISTS idx_inventory_project_article ON inventory_items(project_id, article_number);

-- ==================== Certificates Table ====================
-- Stores certificates/PDF files for articles
-- Consolidated schema (includes fields from migrations 006 and 007)
CREATE TABLE IF NOT EXISTS certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    article_number TEXT NOT NULL,
    certificate_id TEXT NOT NULL,  -- Unique certificate identifier (e.g., "ART_12345_Materialintyg_20250108_143022")
    certificate_type TEXT NOT NULL,  -- e.g., "Materialintyg", "Svetslogg"
    stored_path TEXT NOT NULL,  -- Full absolute path to stored certificate file
    stored_name TEXT NOT NULL,  -- Filename in storage (with certificate_id)
    original_name TEXT NOT NULL,  -- Original filename when uploaded
    page_count INTEGER DEFAULT 0,
    project_article_id INTEGER,  -- Optional FK to project_articles
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (project_article_id) REFERENCES project_articles(id) ON DELETE SET NULL
);

-- Indexes for certificate lookups
CREATE INDEX IF NOT EXISTS idx_certificates_project ON certificates(project_id);
CREATE INDEX IF NOT EXISTS idx_certificates_article ON certificates(article_number);
CREATE INDEX IF NOT EXISTS idx_certificates_type ON certificates(certificate_type);
CREATE INDEX IF NOT EXISTS idx_certificates_project_article ON certificates(project_id, article_number);
CREATE INDEX IF NOT EXISTS idx_certificates_cert_id ON certificates(certificate_id);
