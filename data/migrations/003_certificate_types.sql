-- Migration 003: Certificate Types
-- Creates tables for managing certificate types (global and project-specific)
-- Allows users to define custom certificate types beyond the default keywords

-- ==================== Global Certificate Types ====================
-- Stores certificate types available in ALL projects
CREATE TABLE IF NOT EXISTS certificate_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default certificate types
INSERT OR IGNORE INTO certificate_types (type_name) VALUES
    ('Materialintyg'),
    ('Certifikat'),
    ('Svetslogg'),
    ('Kontrollrapport'),
    ('Provningsprotokoll'),
    ('Leverantörsintyg'),
    ('Kvalitetsintyg'),
    ('Andra handlingar');

-- ==================== Project-Specific Certificate Types ====================
-- Stores certificate types specific to individual projects
CREATE TABLE IF NOT EXISTS project_certificate_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    type_name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, type_name)  -- Prevent duplicates within a project
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_project_cert_types_project ON project_certificate_types(project_id);
