-- Migration 003: Certificate Types
-- Creates tables for managing certificate types (global and project-specific)
-- Allows users to define custom certificate types beyond the default keywords
-- Includes sort_order for user-defined ordering (intervals of 10 for easy insertion)

-- ==================== Global Certificate Types ====================
-- Stores certificate types available in ALL projects
CREATE TABLE IF NOT EXISTS certificate_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name TEXT NOT NULL UNIQUE,
    search_path TEXT,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default certificate types with explicit sort_order (intervals of 10)
INSERT OR IGNORE INTO certificate_types (type_name, sort_order) VALUES
    ('Material Certificate', 10),
    ('Certificate', 20),
    ('Welding Log', 30),
    ('Inspection Report', 40),
    ('Test Protocol', 50),
    ('Supplier Certificate', 60),
    ('Quality Certificate', 70),
    ('Other Documents', 80);

-- ==================== Project-Specific Certificate Types ====================
-- Stores certificate types specific to individual projects
CREATE TABLE IF NOT EXISTS project_certificate_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    type_name TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    UNIQUE(project_id, type_name)  -- Prevent duplicates within a project
);

-- Indexes for faster lookups and sorting
CREATE INDEX IF NOT EXISTS idx_project_cert_types_project ON project_certificate_types(project_id);
CREATE INDEX IF NOT EXISTS idx_cert_types_sort_order ON certificate_types(sort_order);
CREATE INDEX IF NOT EXISTS idx_project_cert_types_sort_order ON project_certificate_types(project_id, sort_order);
