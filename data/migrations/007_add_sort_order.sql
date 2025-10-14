-- Migration 007: Add sort_order to project_articles
-- Preserves the original import order from nivålista (Excel file)
-- CRITICAL: Article order from nivålista must NEVER change

-- Add sort_order column to project_articles table
ALTER TABLE project_articles ADD COLUMN sort_order INTEGER DEFAULT 0;

-- Create index for faster sorting by sort_order
CREATE INDEX IF NOT EXISTS idx_project_articles_sort_order ON project_articles(sort_order);

-- Update existing rows: Set sort_order = id (simple default based on insert order)
-- NOTE: This is a best-effort for existing data. New imports will have explicit sort_order.
UPDATE project_articles SET sort_order = id WHERE sort_order = 0;

-- Note:
-- - New imports will get sort_order = row number from Excel (0, 1, 2, ...)
-- - Queries will now ORDER BY sort_order instead of level, article_number
-- - This ensures articles always appear in the same order as the nivålista
