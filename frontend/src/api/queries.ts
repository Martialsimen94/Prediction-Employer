// TanStack Query hooks wrapping the REST client. One module for the whole
// app: the API surface is small enough that per-resource files would just
// add indirection without paying for itself yet.

import { useMutation, useQuery, useQueryClient, type UseQueryOptions } from '@tanstack/react-query'
import { api } from './client'
import type {
  Department,
  Employee,
  Employee360,
  EmployeeInput,
  DepartmentKPI,
  Notification,
  Page,
  PredictionDetail,
  Promotion,
  RecommendationStatus,
  Salary,
  SalaryChangeReason,
} from './types'

// --- Employees -------------------------------------------------------

export interface EmployeeListParams {
  search?: string
  department_id?: number
  employment_status?: string
  manager_id?: number
  limit?: number
  offset?: number
}

export function useEmployees(params: EmployeeListParams) {
  return useQuery({
    queryKey: ['employees', params],
    queryFn: () => api.get<Page<Employee>>('/employees', { ...params }),
    placeholderData: (previous) => previous,
  })
}

export function useEmployee(id: number | undefined) {
  return useQuery({
    queryKey: ['employees', id],
    queryFn: () => api.get<Employee>(`/employees/${id}`),
    enabled: id !== undefined,
  })
}

export function useCreateEmployee() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: EmployeeInput) => api.post<Employee>('/employees', input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees'] }),
  })
}

export function useUpdateEmployee(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: Partial<EmployeeInput> & { termination_date?: string | null }) =>
      api.patch<Employee>(`/employees/${id}`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees'] })
    },
  })
}

// --- Departments -------------------------------------------------------

export interface DepartmentListParams {
  search?: string
  limit?: number
  offset?: number
}

export function useDepartments(params: DepartmentListParams = {}) {
  return useQuery({
    queryKey: ['departments', params],
    queryFn: () => api.get<Page<Department>>('/departments', { ...params }),
    placeholderData: (previous) => previous,
  })
}

export function useAllDepartments(options?: Partial<UseQueryOptions<Page<Department>>>) {
  return useQuery({
    queryKey: ['departments', 'all'],
    queryFn: () => api.get<Page<Department>>('/departments', { limit: 100 }),
    ...options,
  })
}

export function useCreateDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      name: string
      description?: string | null
      manager_id?: number | null
    }) => api.post<Department>('/departments', input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}

export function useUpdateDepartment(id: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      name?: string
      description?: string | null
      manager_id?: number | null
    }) => api.patch<Department>(`/departments/${id}`, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}

export function useDeleteDepartment() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.delete<void>(`/departments/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['departments'] }),
  })
}

// --- Salaries & promotions (nested under an employee) ------------------

export function useEmployeeSalaries(employeeId: number) {
  return useQuery({
    queryKey: ['employees', employeeId, 'salaries'],
    queryFn: () => api.get<Page<Salary>>(`/employees/${employeeId}/salaries`, { limit: 100 }),
  })
}

export function useCreateSalary(employeeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: { amount: string; effective_date: string; reason: SalaryChangeReason }) =>
      api.post<Salary>(`/employees/${employeeId}/salaries`, input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId, 'salaries'] }),
  })
}

export function useEmployeePromotions(employeeId: number) {
  return useQuery({
    queryKey: ['employees', employeeId, 'promotions'],
    queryFn: () => api.get<Page<Promotion>>(`/employees/${employeeId}/promotions`, { limit: 100 }),
  })
}

export function useCreatePromotion(employeeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (input: {
      previous_job_title: string
      new_job_title: string
      new_department_id?: number | null
      promotion_date: string
    }) => api.post<Promotion>(`/employees/${employeeId}/promotions`, input),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId, 'promotions'] })
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId] })
    },
  })
}

// --- Predictions & recommendations --------------------------------------

export function useEmployeePredictions(employeeId: number) {
  return useQuery({
    queryKey: ['employees', employeeId, 'predictions'],
    queryFn: () =>
      api.get<Page<PredictionDetail>>(`/employees/${employeeId}/predictions`, { limit: 20 }),
  })
}

export function useTriggerPrediction(employeeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<PredictionDetail>(`/employees/${employeeId}/predictions`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId, 'predictions'] })
      queryClient.invalidateQueries({ queryKey: ['reports', 'employee-360', employeeId] })
    },
  })
}

export function useUpdateRecommendationStatus(employeeId: number) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ id, status }: { id: number; status: RecommendationStatus }) =>
      api.patch(`/recommendations/${id}`, { status }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ['employees', employeeId, 'predictions'] }),
  })
}

// --- Notifications -------------------------------------------------------

export function useNotifications(unreadOnly: boolean) {
  return useQuery({
    queryKey: ['notifications', { unreadOnly }],
    queryFn: () =>
      api.get<Page<Notification>>('/notifications', {
        unread_only: unreadOnly,
        limit: 50,
      }),
  })
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => api.patch<Notification>(`/notifications/${id}/read`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  })
}

// --- Reports (Module 11) -------------------------------------------------

export function useDepartmentKPIs() {
  return useQuery({
    queryKey: ['reports', 'department-kpis'],
    queryFn: () => api.get<DepartmentKPI[]>('/reports/department-kpis'),
  })
}

export function useEmployee360(employeeId: number | undefined) {
  return useQuery({
    queryKey: ['reports', 'employee-360', employeeId],
    queryFn: () => api.get<Employee360>(`/reports/employees/${employeeId}/360`),
    enabled: employeeId !== undefined,
  })
}
