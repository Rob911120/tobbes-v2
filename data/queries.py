"""
SQL queries as constants for better maintainability.

All queries are defined here to avoid SQL string literals scattered
throughout the codebase. This makes it easier to:
- Review SQL security
- Optimize queries
- Update schema changes
"""

# ==================== Project Queries ====================

INSERT_PROJECT = """
    INSERT INTO projects (project_name, order_number, customer, created_by, description,
                         purchase_order_number, project_type)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

UPDATE_PROJECT = """
    UPDATE projects
    SET project_name = ?, order_number = ?, customer = ?, description = ?,
        purchase_order_number = ?, project_type = ?
    WHERE id = ?
"""

SELECT_PROJECT_BY_ID = """
    SELECT id, project_name, order_number, customer, description,
           purchase_order_number, project_type,
           created_at, updated_at, created_by
    FROM projects
    WHERE id = ?
"""

SELECT_ALL_PROJECTS = """
    SELECT id, project_name, order_number, customer, description,
           purchase_order_number, project_type,
           created_at, updated_at, created_by
    FROM projects
    ORDER BY {order_by}
    LIMIT ? OFFSET ?
"""

DELETE_PROJECT = """
    DELETE FROM projects WHERE id = ?
"""

# ==================== Global Article Queries ====================

UPSERT_GLOBAL_ARTICLE = """
    INSERT INTO global_articles (article_number, description, notes, changed_by)
    VALUES (?, ?, ?, ?)
    ON CONFLICT(article_number) DO UPDATE SET
        description = excluded.description,
        notes = excluded.notes,
        changed_by = excluded.changed_by
"""

SELECT_GLOBAL_ARTICLE = """
    SELECT article_number, description, notes, updated_at, changed_by
    FROM global_articles
    WHERE article_number = ?
"""

UPDATE_ARTICLE_NOTES = """
    UPDATE global_articles
    SET notes = ?, changed_by = ?
    WHERE article_number = ?
"""

SELECT_NOTES_HISTORY = """
    SELECT article_number, old_notes, new_notes, changed_by, changed_at
    FROM article_notes_audit
    WHERE article_number = ?
    ORDER BY changed_at DESC
    LIMIT ?
"""

# ==================== Project Article Queries ====================

INSERT_PROJECT_ARTICLE = """
    INSERT INTO project_articles
    (project_id, article_number, description, quantity, level, parent_article, charge_number)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(project_id, article_number, level) DO UPDATE SET
        description = excluded.description,
        quantity = excluded.quantity,
        parent_article = excluded.parent_article,
        charge_number = excluded.charge_number
"""

SELECT_PROJECT_ARTICLES = """
    SELECT id, project_id, article_number, description, quantity,
           level, parent_article, charge_number, created_at, updated_at
    FROM project_articles
    WHERE project_id = ?
    ORDER BY level, article_number
"""

SELECT_PROJECT_ARTICLES_WITH_GLOBAL = """
    SELECT
        pa.id,
        pa.project_id,
        pa.article_number,
        pa.description,
        pa.quantity,
        pa.level,
        pa.parent_article,
        pa.charge_number,
        pa.created_at,
        pa.updated_at,
        ga.notes AS global_notes,
        ga.description AS global_description
    FROM project_articles pa
    LEFT JOIN global_articles ga ON pa.article_number = ga.article_number
    WHERE pa.project_id = ?
    ORDER BY pa.level, pa.article_number
"""

UPDATE_ARTICLE_CHARGE = """
    UPDATE project_articles
    SET charge_number = ?
    WHERE project_id = ? AND article_number = ?
"""

UPDATE_ARTICLE_QUANTITY = """
    UPDATE project_articles
    SET quantity = ?
    WHERE project_id = ? AND article_number = ?
"""

UPDATE_ARTICLE_LEVEL = """
    UPDATE project_articles
    SET level_number = ?
    WHERE project_id = ? AND article_number = ?
"""

# ==================== Inventory Queries ====================

INSERT_INVENTORY_ITEM = """
    INSERT INTO inventory_items
    (project_id, article_number, charge_number, batch_id, quantity, location, received_date)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

SELECT_INVENTORY_ITEMS = """
    SELECT id, project_id, article_number, charge_number, batch_id,
           quantity, location, received_date, created_at
    FROM inventory_items
    WHERE project_id = ?
    ORDER BY article_number, received_date DESC
"""

SELECT_AVAILABLE_CHARGES = """
    SELECT DISTINCT charge_number
    FROM inventory_items
    WHERE project_id = ? AND article_number = ?
    ORDER BY received_date DESC
"""

# ==================== Certificate Queries ====================

INSERT_CERTIFICATE = """
    INSERT INTO certificates
    (project_id, article_number, certificate_type, file_path,
     original_filename, page_count, project_article_id)
    VALUES (?, ?, ?, ?, ?, ?, ?)
"""

SELECT_CERTIFICATES_BY_ARTICLE = """
    SELECT id, project_id, article_number, certificate_type, file_path,
           original_filename, page_count, project_article_id, created_at
    FROM certificates
    WHERE project_id = ? AND article_number = ?
    ORDER BY created_at DESC
"""

SELECT_CERTIFICATES_BY_PROJECT = """
    SELECT id, project_id, article_number, certificate_type, file_path,
           original_filename, page_count, project_article_id, created_at
    FROM certificates
    WHERE project_id = ?
    ORDER BY article_number, created_at DESC
"""

DELETE_CERTIFICATE = """
    DELETE FROM certificates WHERE id = ?
"""

# ==================== Certificate Type Queries ====================

SELECT_GLOBAL_CERTIFICATE_TYPES = """
    SELECT type_name
    FROM certificate_types
    ORDER BY type_name
"""

SELECT_PROJECT_CERTIFICATE_TYPES = """
    SELECT type_name
    FROM project_certificate_types
    WHERE project_id = ?
    ORDER BY type_name
"""

INSERT_GLOBAL_CERTIFICATE_TYPE = """
    INSERT OR IGNORE INTO certificate_types (type_name)
    VALUES (?)
"""

INSERT_PROJECT_CERTIFICATE_TYPE = """
    INSERT OR IGNORE INTO project_certificate_types (project_id, type_name)
    VALUES (?, ?)
"""

DELETE_GLOBAL_CERTIFICATE_TYPE = """
    DELETE FROM certificate_types WHERE type_name = ?
"""

DELETE_PROJECT_CERTIFICATE_TYPE = """
    DELETE FROM project_certificate_types
    WHERE project_id = ? AND type_name = ?
"""

# ==================== Statistics Queries ====================

SELECT_PROJECT_STATISTICS = """
    SELECT
        COUNT(DISTINCT pa.article_number) AS total_articles,
        COUNT(DISTINCT c.article_number) AS verified_articles
    FROM project_articles pa
    LEFT JOIN certificates c ON c.project_id = pa.project_id
                             AND c.article_number = pa.article_number
    WHERE pa.project_id = ?
"""
