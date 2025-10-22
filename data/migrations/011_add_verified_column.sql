-- Migration 011: Add verified column to project_articles table
--
-- Purpose: Add 'verified' column to track which articles have been verified.
--          This column is used by:
--          - UI verification checkbox (article_card.py)
--          - Project statistics (SELECT_PROJECT_STATISTICS query)
--          - Article updates (update_project_article method)
--
-- SQLite uses INTEGER for BOOLEAN values:
-- 0 = false (not verified)
-- 1 = true (verified)

-- Add verified column with default value 0 (not verified)
ALTER TABLE project_articles
ADD COLUMN verified INTEGER DEFAULT 0;

-- Create index for faster queries when filtering by verification status
CREATE INDEX IF NOT EXISTS idx_project_articles_verified
ON project_articles(verified);
