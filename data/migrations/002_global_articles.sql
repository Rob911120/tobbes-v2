-- Migration 002: Global Articles
-- Creates table for article data shared across all projects
-- This enables users to maintain notes and information that persists between projects

-- ==================== Global Articles Table ====================
-- Stores article data that is shared across ALL projects
CREATE TABLE IF NOT EXISTS global_articles (
    article_number TEXT PRIMARY KEY,  -- Unique article identifier
    description TEXT,  -- Standard article description
    notes TEXT,  -- User notes visible in all projects
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    changed_by TEXT  -- Username of last person to edit
);

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_global_articles_updated ON global_articles(updated_at DESC);

-- Trigger to update updated_at on global_articles
CREATE TRIGGER IF NOT EXISTS update_global_articles_timestamp
AFTER UPDATE ON global_articles
BEGIN
    UPDATE global_articles SET updated_at = CURRENT_TIMESTAMP WHERE article_number = NEW.article_number;
END;
