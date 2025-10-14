-- Migration 006: Add original_path to certificates
-- Enables re-processing certificates with different types without re-uploading
-- Stores the original file path so we can re-process with new certificate type

-- Add original_path column to certificates table
ALTER TABLE certificates ADD COLUMN original_path TEXT DEFAULT NULL;

-- Note: existing certificates will have NULL original_path
-- Only new certificates (uploaded after this migration) will have original_path
-- The "Change Type" button will only be enabled for certificates with original_path
