-- Migration 009: Translate Certificate Types to English
-- Updates existing certificate type records from Swedish to English

-- Update global certificate types from Swedish to English
UPDATE certificate_types SET type_name = 'Material Certificate' WHERE type_name = 'Materialintyg';
UPDATE certificate_types SET type_name = 'Certificate' WHERE type_name = 'Certifikat';
UPDATE certificate_types SET type_name = 'Welding Log' WHERE type_name = 'Svetslogg';
UPDATE certificate_types SET type_name = 'Inspection Report' WHERE type_name = 'Kontrollrapport';
UPDATE certificate_types SET type_name = 'Test Protocol' WHERE type_name = 'Provningsprotokoll';
UPDATE certificate_types SET type_name = 'Supplier Certificate' WHERE type_name = 'Leverantörsintyg';
UPDATE certificate_types SET type_name = 'Quality Certificate' WHERE type_name = 'Kvalitetsintyg';
UPDATE certificate_types SET type_name = 'Other Documents' WHERE type_name = 'Andra handlingar';

-- Update project-specific certificate types from Swedish to English
UPDATE project_certificate_types SET type_name = 'Material Certificate' WHERE type_name = 'Materialintyg';
UPDATE project_certificate_types SET type_name = 'Certificate' WHERE type_name = 'Certifikat';
UPDATE project_certificate_types SET type_name = 'Welding Log' WHERE type_name = 'Svetslogg';
UPDATE project_certificate_types SET type_name = 'Inspection Report' WHERE type_name = 'Kontrollrapport';
UPDATE project_certificate_types SET type_name = 'Test Protocol' WHERE type_name = 'Provningsprotokoll';
UPDATE project_certificate_types SET type_name = 'Supplier Certificate' WHERE type_name = 'Leverantörsintyg';
UPDATE project_certificate_types SET type_name = 'Quality Certificate' WHERE type_name = 'Kvalitetsintyg';
UPDATE project_certificate_types SET type_name = 'Other Documents' WHERE type_name = 'Andra handlingar';

-- Update certificate records from Swedish to English
UPDATE certificates SET certificate_type = 'Material Certificate' WHERE certificate_type = 'Materialintyg';
UPDATE certificates SET certificate_type = 'Certificate' WHERE certificate_type = 'Certifikat';
UPDATE certificates SET certificate_type = 'Welding Log' WHERE certificate_type = 'Svetslogg';
UPDATE certificates SET certificate_type = 'Inspection Report' WHERE certificate_type = 'Kontrollrapport';
UPDATE certificates SET certificate_type = 'Test Protocol' WHERE certificate_type = 'Provningsprotokoll';
UPDATE certificates SET certificate_type = 'Supplier Certificate' WHERE certificate_type = 'Leverantörsintyg';
UPDATE certificates SET certificate_type = 'Quality Certificate' WHERE certificate_type = 'Kvalitetsintyg';
UPDATE certificates SET certificate_type = 'Other Documents' WHERE certificate_type = 'Andra handlingar';
