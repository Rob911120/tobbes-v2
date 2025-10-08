-- Migration 008: Add batch_number to project_articles
-- Batch numbers from lagerlogg (inventory log)
-- Similar to charge_number but can be independent

-- Add batch_number column to project_articles
ALTER TABLE project_articles ADD COLUMN batch_number TEXT;

-- Index for faster batch lookups
CREATE INDEX IF NOT EXISTS idx_project_articles_batch ON project_articles(batch_number);

-- Note: Unlike charge_number, batch_number can also be empty
-- Batch and charge are independent - article can have:
-- - Only batch (no charge)
-- - Only charge (no batch)
-- - Both batch and charge
-- - Neither (empty strings)
