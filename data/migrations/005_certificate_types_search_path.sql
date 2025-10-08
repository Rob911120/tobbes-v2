-- Migration 005: Add search_path to certificate_types
-- Adds ability to configure a default search directory for each certificate type
-- This enables fuzzy matching and auto-suggestion of certificate files

-- Add search_path column to certificate_types table
ALTER TABLE certificate_types ADD COLUMN search_path TEXT DEFAULT NULL;

-- Update comment
-- search_path: Optional directory path where certificates of this type are typically stored
-- Example: '/project/certificates/material' or 'C:\Projects\Certs\Material'
-- NULL means no auto-search configured for this certificate type
