-- Migration 005: Add project metadata fields
-- Adds purchase_order_number and project_type to projects table

-- Add purchase_order_number (Beställningsnummer)
ALTER TABLE projects ADD COLUMN purchase_order_number TEXT;

-- Add project_type (Doc/Ej Doc)
ALTER TABLE projects ADD COLUMN project_type TEXT DEFAULT 'Doc';

-- Create index for faster filtering by project type
CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(project_type);
