-- Migration 010: Add sort_order to certificate types
-- Allows users to reorder certificate types (both global and project-specific)
-- This affects the order in dropdowns, TOC, and PDF section order

-- ==================== Add sort_order columns ====================

-- Add sort_order to global certificate types
ALTER TABLE certificate_types ADD COLUMN sort_order INTEGER DEFAULT 0;

-- Add sort_order to project-specific certificate types
ALTER TABLE project_certificate_types ADD COLUMN sort_order INTEGER DEFAULT 0;

-- ==================== Set initial sort_order for existing types ====================

-- Global types: Assign explicit order (intervals of 10 for easy insertion)
UPDATE certificate_types SET sort_order =
  CASE type_name
    WHEN 'Material Certificate' THEN 10
    WHEN 'Certificate' THEN 20
    WHEN 'Welding Log' THEN 30
    WHEN 'Inspection Report' THEN 40
    WHEN 'Test Protocol' THEN 50
    WHEN 'Supplier Certificate' THEN 60
    WHEN 'Quality Certificate' THEN 70
    WHEN 'Other Documents' THEN 80
    ELSE (id * 10)  -- Fallback for custom types
  END;

-- Project-specific types: Use id-based ordering as default
UPDATE project_certificate_types SET sort_order = id * 10 WHERE sort_order = 0;

-- ==================== Create indexes for performance ====================

CREATE INDEX IF NOT EXISTS idx_cert_types_sort_order ON certificate_types(sort_order);
CREATE INDEX IF NOT EXISTS idx_project_cert_types_sort_order ON project_certificate_types(project_id, sort_order);
