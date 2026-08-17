-- Database triggers: automatic updated_at maintenance + audit trail on
-- sensitive tables (compensation and promotions). Applied by Alembic
-- migration 8f1c2b6a1d4e_views_triggers_procedures.

-- Keeps `updated_at` correct for ANY writer (ORM, psql, ETL jobs), not just
-- SQLAlchemy's onupdate=func.now(), which only fires for updates issued
-- through the ORM.
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t text;
BEGIN
    FOR t IN
        SELECT unnest(ARRAY[
            'departments', 'employees', 'salaries', 'performance_reviews', 'promotions',
            'absences', 'trainings', 'employee_trainings', 'skills', 'users', 'roles',
            'permissions', 'ml_model_registry', 'attrition_predictions', 'recommendations',
            'notifications', 'data_drift_reports'
        ])
    LOOP
        EXECUTE format('DROP TRIGGER IF EXISTS trg_set_updated_at ON %I', t);
        EXECUTE format(
            'CREATE TRIGGER trg_set_updated_at BEFORE UPDATE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            t
        );
    END LOOP;
END $$;

-- Generic audit-log writer: records every INSERT/UPDATE/DELETE on the tables
-- it's attached to, independent of which layer of the application made the
-- change.
CREATE OR REPLACE FUNCTION audit_trigger_fn() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD), NULL);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW));
        RETURN NEW;
    ELSE
        INSERT INTO audit_log (table_name, record_id, action, old_data, new_data)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', NULL, row_to_json(NEW));
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_salaries ON salaries;
CREATE TRIGGER trg_audit_salaries
    AFTER INSERT OR UPDATE OR DELETE ON salaries
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();

DROP TRIGGER IF EXISTS trg_audit_promotions ON promotions;
CREATE TRIGGER trg_audit_promotions
    AFTER INSERT OR UPDATE OR DELETE ON promotions
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn();
