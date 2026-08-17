-- Reporting views used by dashboards and the API's read models.
-- Applied by Alembic migration 8f1c2b6a1d4e_views_triggers_procedures.

-- v_employee_360: one row per employee, consolidating current department/manager,
-- current salary, latest performance review and latest attrition prediction.
CREATE OR REPLACE VIEW v_employee_360 AS
SELECT
    e.id                                                                          AS employee_id,
    e.employee_number,
    e.first_name,
    e.last_name,
    e.email,
    e.job_title,
    e.employment_status,
    e.hire_date,
    DATE_PART('year', AGE(COALESCE(e.termination_date, CURRENT_DATE), e.hire_date)) AS tenure_years,
    d.id                                                                          AS department_id,
    d.name                                                                        AS department_name,
    m.id                                                                          AS manager_id,
    m.first_name || ' ' || m.last_name                                           AS manager_name,
    s.amount                                                                      AS current_salary,
    s.currency                                                                    AS current_salary_currency,
    pr.score                                                                      AS latest_performance_score,
    pr.review_date                                                                AS latest_performance_review_date,
    ap.risk_level                                                                 AS latest_attrition_risk_level,
    ap.risk_score                                                                 AS latest_attrition_risk_score,
    ap.predicted_at                                                               AS latest_prediction_at
FROM employees e
LEFT JOIN departments d ON d.id = e.department_id
LEFT JOIN employees m ON m.id = e.manager_id
LEFT JOIN LATERAL (
    SELECT amount, currency
    FROM salaries
    WHERE employee_id = e.id AND end_date IS NULL
    ORDER BY effective_date DESC
    LIMIT 1
) s ON TRUE
LEFT JOIN LATERAL (
    SELECT score, review_date
    FROM performance_reviews
    WHERE employee_id = e.id
    ORDER BY review_date DESC
    LIMIT 1
) pr ON TRUE
LEFT JOIN LATERAL (
    SELECT risk_level, risk_score, predicted_at
    FROM attrition_predictions
    WHERE employee_id = e.id
    ORDER BY predicted_at DESC
    LIMIT 1
) ap ON TRUE;

-- v_department_kpis: per-department headcount, salary and tenure/turnover KPIs
-- for the HR and Executive dashboards.
CREATE OR REPLACE VIEW v_department_kpis AS
SELECT
    d.id                                                                                    AS department_id,
    d.name                                                                                  AS department_name,
    COUNT(e.id) FILTER (WHERE e.employment_status = 'active')                               AS active_headcount,
    COUNT(e.id) FILTER (
        WHERE e.employment_status = 'terminated'
          AND e.termination_date >= CURRENT_DATE - INTERVAL '12 months'
    )                                                                                        AS terminations_last_12_months,
    ROUND(AVG(s.amount), 2)                                                                  AS avg_current_salary,
    ROUND(
        AVG(DATE_PART('year', AGE(COALESCE(e.termination_date, CURRENT_DATE), e.hire_date)))::numeric, 1
    )                                                                                        AS avg_tenure_years
FROM departments d
LEFT JOIN employees e ON e.department_id = d.id
LEFT JOIN LATERAL (
    SELECT amount
    FROM salaries
    WHERE employee_id = e.id AND end_date IS NULL
    ORDER BY effective_date DESC
    LIMIT 1
) s ON TRUE
GROUP BY d.id, d.name;

-- v_attrition_risk_summary: latest attrition prediction per employee, for the
-- Data Scientist and Manager dashboards.
CREATE OR REPLACE VIEW v_attrition_risk_summary AS
SELECT DISTINCT ON (ap.employee_id)
    ap.employee_id,
    e.employee_number,
    e.first_name,
    e.last_name,
    e.department_id,
    d.name AS department_name,
    ap.risk_score,
    ap.risk_level,
    ap.predicted_at,
    ap.top_features
FROM attrition_predictions ap
JOIN employees e ON e.id = ap.employee_id
LEFT JOIN departments d ON d.id = e.department_id
ORDER BY ap.employee_id, ap.predicted_at DESC;
