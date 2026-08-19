// Types mirroring the backend's Pydantic schemas (backend/app/schemas/).
// Kept hand-written rather than generated: the API is small and stable
// enough that a codegen step isn't worth the build-time dependency yet.

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export type EmploymentStatus = 'active' | 'on_leave' | 'terminated'
export type SalaryChangeReason = 'initial' | 'raise' | 'promotion' | 'adjustment' | 'correction'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'
export type RecommendationAction =
  | 'salary_increase'
  | 'training'
  | 'promotion'
  | 'internal_mobility'
  | 'coaching'
  | 'team_change'
  | 'workload_reduction'
  | 'mentoring'
export type RecommendationPriority = 'low' | 'medium' | 'high'
export type RecommendationStatus = 'pending' | 'in_progress' | 'completed' | 'dismissed'

export interface User {
  id: number
  email: string
  is_active: boolean
  roles: string[]
  employee_id: number | null
}

export interface TokenPair {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Department {
  id: number
  name: string
  description: string | null
  manager_id: number | null
}

export interface Employee {
  id: number
  employee_number: string
  first_name: string
  last_name: string
  email: string
  hire_date: string
  birth_date: string | null
  department_id: number | null
  manager_id: number | null
  job_title: string
  employment_status: EmploymentStatus
  termination_date: string | null
  gender: string | null
  marital_status: string | null
  education_level: string | null
  distance_from_home_km: string | null
}

export interface EmployeeInput {
  employee_number: string
  first_name: string
  last_name: string
  email: string
  hire_date: string
  birth_date?: string | null
  department_id?: number | null
  manager_id?: number | null
  job_title: string
  employment_status?: EmploymentStatus
  gender?: string | null
  marital_status?: string | null
  education_level?: string | null
  distance_from_home_km?: string | null
}

export interface Salary {
  id: number
  employee_id: number
  amount: string
  currency: string
  effective_date: string
  end_date: string | null
  reason: SalaryChangeReason
}

export interface Promotion {
  id: number
  employee_id: number
  previous_job_title: string
  new_job_title: string
  previous_department_id: number | null
  new_department_id: number | null
  promotion_date: string
  approved_by: number | null
}

export interface Notification {
  id: number
  title: string
  body: string
  notification_type: string
  related_entity_type: string | null
  related_entity_id: number | null
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface Recommendation {
  id: number
  prediction_id: number
  action_type: RecommendationAction
  rationale: string
  priority: RecommendationPriority
  status: RecommendationStatus
  resolved_at: string | null
}

export interface PredictionDetail {
  id: number
  employee_id: number
  model_registry_id: number | null
  risk_score: string
  risk_level: RiskLevel
  predicted_at: string
  top_features: Record<string, number>
  shap_values: Record<string, number>
  recommendations: Recommendation[]
}

export interface DepartmentKPI {
  department_id: number
  department_name: string
  active_headcount: number
  terminations_last_12_months: number
  avg_current_salary: string | null
  avg_tenure_years: string | null
  turnover_rate_12mo: string
}

export interface Employee360 {
  employee_id: number
  employee_number: string
  first_name: string
  last_name: string
  email: string
  job_title: string
  employment_status: string
  hire_date: string
  tenure_years: string | null
  department_id: number | null
  department_name: string | null
  manager_id: number | null
  manager_name: string | null
  current_salary: string | null
  current_salary_currency: string | null
  latest_performance_score: string | null
  latest_performance_review_date: string | null
  latest_attrition_risk_level: RiskLevel | null
  latest_attrition_risk_score: string | null
  latest_prediction_at: string | null
}
