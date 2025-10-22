-- Migration 008: Remove project_type column from projects table
--
-- SQLite doesn't support DROP COLUMN directly, so we need to:
-- 1. Create new table without project_type
-- 2. Copy data from old table
-- 3. Drop old table
-- 4. Rename new table
-- 5. Recreate triggers and indexes

-- Step 1: Drop index on project_type
DROP INDEX IF EXISTS idx_projects_type;

-- Step 2: Create new table without project_type
CREATE TABLE projects_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    order_number TEXT NOT NULL UNIQUE,
    customer TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT NOT NULL,
    purchase_order_number TEXT
);

-- Step 3: Copy data from old table (excluding project_type)
INSERT INTO projects_new (
    id, project_name, order_number, customer, description,
    created_at, updated_at, created_by, purchase_order_number
)
SELECT
    id, project_name, order_number, customer, description,
    created_at, updated_at, created_by, purchase_order_number
FROM projects;

-- Step 4: Drop old table
DROP TABLE projects;

-- Step 5: Rename new table
ALTER TABLE projects_new RENAME TO projects;

-- Step 6: Recreate index on order_number
CREATE INDEX idx_projects_order_number ON projects(order_number);

-- Step 7: Recreate update trigger
CREATE TRIGGER update_projects_timestamp
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
