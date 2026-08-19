// Mirrors ROLE_PERMISSIONS from the Module 3/11 seed migrations
// (backend/alembic/versions/4a06f51a9827_..., d71f9bb415d4_...). This is a
// UX convenience only -- it decides what to *show*, not what's allowed;
// the API is the actual enforcement point and returns 403 regardless of
// what the UI renders.
export const ROLES_WITH_EMPLOYEES_READ = ['admin', 'hr', 'manager', 'executive']
export const ROLES_WITH_EMPLOYEES_WRITE = ['admin', 'hr']
export const ROLES_WITH_SALARIES_READ = ['admin', 'hr', 'executive']
export const ROLES_WITH_SALARIES_WRITE = ['admin', 'hr']
export const ROLES_WITH_PREDICTIONS_READ = ['admin', 'hr', 'manager', 'data_scientist', 'executive']
export const ROLES_WITH_PREDICTIONS_WRITE = ['admin', 'data_scientist']
export const ROLES_WITH_AUDIT_READ = ['admin', 'hr', 'data_scientist', 'executive']
