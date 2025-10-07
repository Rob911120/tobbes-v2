-- Migration 004: Article Notes Audit Log
-- Creates audit table and triggers to track all changes to article notes
-- This provides a complete history of who changed what and when

-- ==================== Audit Log Table ====================
-- Stores history of all changes to global_articles.notes
CREATE TABLE IF NOT EXISTS article_notes_audit (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_number TEXT NOT NULL,
    old_notes TEXT,  -- Previous notes value
    new_notes TEXT,  -- New notes value
    changed_by TEXT NOT NULL,  -- Username of person making change
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (article_number) REFERENCES global_articles(article_number) ON DELETE CASCADE
);

-- Index for faster history queries
CREATE INDEX IF NOT EXISTS idx_audit_article ON article_notes_audit(article_number, changed_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_changed_at ON article_notes_audit(changed_at DESC);

-- ==================== Audit Trigger ====================
-- Automatically logs changes to global_articles.notes
-- Triggers AFTER UPDATE only when notes field changes
CREATE TRIGGER IF NOT EXISTS audit_article_notes_update
AFTER UPDATE OF notes ON global_articles
WHEN OLD.notes IS NOT NEW.notes  -- Only log if notes actually changed
BEGIN
    INSERT INTO article_notes_audit (
        article_number,
        old_notes,
        new_notes,
        changed_by
    ) VALUES (
        NEW.article_number,
        OLD.notes,
        NEW.notes,
        NEW.changed_by
    );
END;

-- ==================== Initial Notes Trigger ====================
-- Logs when notes are first created (INSERT with notes)
-- This ensures we have a complete history from the start
CREATE TRIGGER IF NOT EXISTS audit_article_notes_insert
AFTER INSERT ON global_articles
WHEN NEW.notes IS NOT NULL AND NEW.notes != ''
BEGIN
    INSERT INTO article_notes_audit (
        article_number,
        old_notes,
        new_notes,
        changed_by
    ) VALUES (
        NEW.article_number,
        NULL,  -- No previous value
        NEW.notes,
        NEW.changed_by
    );
END;
