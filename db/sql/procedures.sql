-- Stored function: department turnover rate over a trailing period.
-- Applied by Alembic migration 8f1c2b6a1d4e_views_triggers_procedures.
--
-- Turnover rate = terminations in the period / headcount that was present at
-- some point during the period (still active, or terminated within it),
-- expressed as a percentage.
CREATE OR REPLACE FUNCTION fn_department_turnover_rate(
    p_department_id INTEGER,
    p_period_months INTEGER DEFAULT 12
) RETURNS NUMERIC AS $$
DECLARE
    v_terminations   INTEGER;
    v_period_headcount INTEGER;
    v_period_start   DATE := CURRENT_DATE - (p_period_months || ' months')::INTERVAL;
BEGIN
    SELECT COUNT(*) INTO v_terminations
    FROM employees
    WHERE department_id = p_department_id
      AND employment_status = 'terminated'
      AND termination_date >= v_period_start;

    SELECT COUNT(*) INTO v_period_headcount
    FROM employees
    WHERE department_id = p_department_id
      AND (employment_status <> 'terminated' OR termination_date >= v_period_start);

    IF v_period_headcount = 0 THEN
        RETURN 0;
    END IF;

    RETURN ROUND((v_terminations::NUMERIC / v_period_headcount) * 100, 2);
END;
$$ LANGUAGE plpgsql;
