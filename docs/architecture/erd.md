# Entity-relationship diagram

The schema is 22 tables (Module 2's initial migration, plus
`employee_feature_snapshots` added in Module 9 — see
[`backend/app/models/`](../../backend/app/models/) for the SQLAlchemy source
of truth and [`db/sql/`](../../db/sql/) for the reporting views, triggers and
stored function layered on top). Split into two diagrams below by domain;
`employees` is the join point between them.

## HR domain + auth/RBAC

```mermaid
erDiagram
    departments {
        int id PK
        string name UK
        int manager_id FK
    }
    employees {
        int id PK
        string employee_number UK
        string email UK
        int department_id FK
        int manager_id FK
        string employment_status
    }
    salaries {
        int id PK
        int employee_id FK
        numeric amount
        date effective_date
        date end_date
        string reason
    }
    performance_reviews {
        int id PK
        int employee_id FK
        int reviewer_id FK
        numeric score
    }
    promotions {
        int id PK
        int employee_id FK
        int previous_department_id FK
        int new_department_id FK
        int approved_by FK
    }
    absences {
        int id PK
        int employee_id FK
        string absence_type
        bool approved
    }
    trainings {
        int id PK
        string name UK
    }
    employee_trainings {
        int id PK
        int employee_id FK
        int training_id FK
        string status
    }
    skills {
        int id PK
        string name UK
    }
    employee_skills {
        int employee_id PK,FK
        int skill_id PK,FK
    }
    users {
        int id PK
        string email UK
        int employee_id FK "nullable, unique"
    }
    roles {
        int id PK
        string name UK
    }
    permissions {
        int id PK
        string code UK
    }
    user_roles {
        int user_id PK,FK
        int role_id PK,FK
    }
    role_permissions {
        int role_id PK,FK
        int permission_id PK,FK
    }
    notifications {
        int id PK
        int user_id FK
        bool is_read
    }
    audit_log {
        int id PK
        string table_name
        int record_id
        int changed_by FK "nullable"
    }

    departments ||--o{ employees : "department_id"
    employees ||--o{ employees : "manager_id"
    employees ||--o| departments : "manager_id (dept head)"
    employees ||--o{ salaries : "employee_id"
    employees ||--o{ performance_reviews : "employee_id / reviewer_id"
    employees ||--o{ promotions : "employee_id / approved_by"
    departments ||--o{ promotions : "previous/new department"
    employees ||--o{ absences : "employee_id"
    employees ||--o{ employee_trainings : "employee_id"
    trainings ||--o{ employee_trainings : "training_id"
    employees ||--o{ employee_skills : "employee_id"
    skills ||--o{ employee_skills : "skill_id"
    employees ||--o| users : "employee_id (self-service login)"
    users ||--o{ user_roles : "user_id"
    roles ||--o{ user_roles : "role_id"
    roles ||--o{ role_permissions : "role_id"
    permissions ||--o{ role_permissions : "permission_id"
    users ||--o{ notifications : "user_id"
    users ||--o{ audit_log : "changed_by"
```

`departments.manager_id` and `employees.manager_id` are a circular pair
(a department points at its head, an employee points at their manager) —
`departments.manager_id`'s FK is declared `use_alter=True` in
[`department.py`](../../backend/app/models/department.py) so Alembic can
create both tables before wiring the constraint that closes the loop.

## ML / MLOps domain

```mermaid
erDiagram
    employees {
        int id PK
    }
    employee_feature_snapshots {
        int id PK
        int employee_id FK "unique"
        json features
        timestamp computed_at
    }
    ml_model_registry {
        int id PK
        string model_name
        string version
        string mlflow_run_id UK
        string stage
    }
    attrition_predictions {
        int id PK
        int employee_id FK
        int model_registry_id FK "nullable"
        numeric risk_score
        string risk_level
        json shap_values
    }
    recommendations {
        int id PK
        int prediction_id FK
        string action_type
        string priority
        string status
    }
    data_drift_reports {
        int id PK
        string feature_name
        numeric drift_score
        bool drift_detected
        string method
    }

    employees ||--o| employee_feature_snapshots : "employee_id (Module 6 ETL)"
    employees ||--o{ attrition_predictions : "employee_id (Module 9)"
    ml_model_registry ||--o{ attrition_predictions : "model_registry_id"
    attrition_predictions ||--o{ recommendations : "prediction_id (Module 8)"
```

`data_drift_reports` (Module 10) has no FK into the HR schema by design —
each row is a feature-level statistic (`feature_name`, e.g. `"OverTime"`)
comparing two `employee_feature_snapshots` periods, not a fact about any
one employee.
