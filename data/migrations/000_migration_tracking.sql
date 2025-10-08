-- Migration 000: Migration Tracking System
-- Creates table to track which migrations have been applied
-- This MUST be the first migration (000) to run before all others

-- Create schema_migrations table to track applied migrations
CREATE TABLE IF NOT EXISTS schema_migrations (
    migration_name TEXT PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Note: This migration itself will be recorded after successful execution
-- All existing migrations will be automatically marked as applied if their
-- schema changes already exist in the database
