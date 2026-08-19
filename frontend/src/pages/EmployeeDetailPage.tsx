import { useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import {
  useAllDepartments,
  useCreatePromotion,
  useCreateSalary,
  useEmployee,
  useEmployee360,
  useEmployeePredictions,
  useEmployeePromotions,
  useEmployeeSalaries,
  useTriggerPrediction,
  useUpdateEmployee,
  useUpdateRecommendationStatus,
} from '../api/queries'
import { useAuth } from '../auth/useAuth'
import {
  ROLES_WITH_EMPLOYEES_WRITE,
  ROLES_WITH_PREDICTIONS_WRITE,
  ROLES_WITH_SALARIES_WRITE,
} from '../auth/permissions'
import { RiskBadge } from '../components/RiskBadge'
import { StatusBadge } from '../components/StatusBadge'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { ApiError } from '../api/client'
import type { EmploymentStatus, RecommendationStatus, SalaryChangeReason } from '../api/types'

const TABS = ['Overview', 'Salary', 'Promotions', 'Predictions'] as const
type Tab = (typeof TABS)[number]

export function EmployeeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const employeeId = Number(id)
  const [tab, setTab] = useState<Tab>('Overview')

  const employee = useEmployee(employeeId)
  const overview = useEmployee360(employeeId)

  if (employee.isLoading) return <LoadingState />
  if (employee.isError || !employee.data) return <ErrorState message="Employee not found." />

  return (
    <div>
      <div className="flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">
            {employee.data.first_name} {employee.data.last_name}
          </h1>
          <p className="text-sm text-gray-500">
            {employee.data.employee_number} &middot; {employee.data.job_title}
          </p>
        </div>
        {overview.data?.latest_attrition_risk_level && (
          <RiskBadge level={overview.data.latest_attrition_risk_level} />
        )}
      </div>

      <div className="mt-4 border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {TABS.map((candidate) => (
            <button
              key={candidate}
              type="button"
              onClick={() => setTab(candidate)}
              className={`border-b-2 px-1 py-2 text-sm font-medium ${
                tab === candidate
                  ? 'border-brand-blue text-brand-blue'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {candidate}
            </button>
          ))}
        </nav>
      </div>

      <div className="mt-6">
        {tab === 'Overview' && <OverviewTab employeeId={employeeId} />}
        {tab === 'Salary' && <SalaryTab employeeId={employeeId} />}
        {tab === 'Promotions' && <PromotionsTab employeeId={employeeId} />}
        {tab === 'Predictions' && <PredictionsTab employeeId={employeeId} />}
      </div>
    </div>
  )
}

function OverviewTab({ employeeId }: { employeeId: number }) {
  const { hasRole } = useAuth()
  const employee = useEmployee(employeeId)
  const overview = useEmployee360(employeeId)
  const departments = useAllDepartments()
  const updateEmployee = useUpdateEmployee(employeeId)
  const [isEditing, setIsEditing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!employee.data) return <LoadingState />
  const canEdit = hasRole(...ROLES_WITH_EMPLOYEES_WRITE)

  async function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    const formData = new FormData(event.currentTarget)
    try {
      await updateEmployee.mutateAsync({
        job_title: String(formData.get('job_title')),
        employment_status: formData.get('employment_status') as EmploymentStatus,
        department_id: formData.get('department_id') ? Number(formData.get('department_id')) : null,
      })
      setIsEditing(false)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to save changes.')
    }
  }

  if (isEditing && employee.data) {
    return (
      <form onSubmit={handleSave} className="max-w-md space-y-4">
        <label className="block text-sm font-medium text-gray-700">
          Job title
          <input name="job_title" defaultValue={employee.data.job_title} className="input mt-1" />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Department
          <select
            name="department_id"
            defaultValue={employee.data.department_id ?? ''}
            className="input mt-1"
          >
            <option value="">Unassigned</option>
            {departments.data?.items.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Employment status
          <select
            name="employment_status"
            defaultValue={employee.data.employment_status}
            className="input mt-1"
          >
            <option value="active">Active</option>
            <option value="on_leave">On leave</option>
            <option value="terminated">Terminated</option>
          </select>
        </label>
        {error && <p className="text-sm text-status-critical">{error}</p>}
        <div className="flex gap-3">
          <button
            type="submit"
            disabled={updateEmployee.isPending}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            Save
          </button>
          <button
            type="button"
            onClick={() => setIsEditing(false)}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </form>
    )
  }

  return (
    <div className="grid max-w-2xl grid-cols-2 gap-x-8 gap-y-4 text-sm">
      <DetailRow label="Email" value={employee.data.email} />
      <DetailRow label="Hire date" value={employee.data.hire_date} />
      <DetailRow label="Department" value={overview.data?.department_name ?? '—'} />
      <DetailRow label="Manager" value={overview.data?.manager_name ?? '—'} />
      <DetailRow
        label="Current salary"
        value={
          overview.data?.current_salary
            ? `${overview.data.current_salary} ${overview.data.current_salary_currency}`
            : '—'
        }
      />
      <DetailRow
        label="Tenure"
        value={overview.data?.tenure_years ? `${overview.data.tenure_years} yrs` : '—'}
      />
      <DetailRow
        label="Latest performance score"
        value={overview.data?.latest_performance_score ?? '—'}
      />
      <div>
        <dt className="text-gray-500">Status</dt>
        <dd className="mt-1">
          <StatusBadge value={employee.data.employment_status} />
        </dd>
      </div>
      {canEdit && (
        <div className="col-span-2">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Edit
          </button>
        </div>
      )}
    </div>
  )
}

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-gray-500">{label}</dt>
      <dd className="mt-1 text-gray-900">{value}</dd>
    </div>
  )
}

function SalaryTab({ employeeId }: { employeeId: number }) {
  const { hasRole } = useAuth()
  const salaries = useEmployeeSalaries(employeeId)
  const createSalary = useCreateSalary(employeeId)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    // Captured before the `await` -- see the equivalent comment in
    // DepartmentsPage.handleCreate.
    const form = event.currentTarget
    const formData = new FormData(form)
    try {
      await createSalary.mutateAsync({
        amount: String(formData.get('amount')),
        effective_date: String(formData.get('effective_date')),
        reason: formData.get('reason') as SalaryChangeReason,
      })
      setShowForm(false)
      form.reset()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to record the salary change.')
    }
  }

  return (
    <div>
      {hasRole(...ROLES_WITH_SALARIES_WRITE) && (
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="mb-4 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
        >
          {showForm ? 'Cancel' : 'Record salary change'}
        </button>
      )}
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 flex max-w-xl items-end gap-3">
          <label className="block text-sm font-medium text-gray-700">
            Amount
            <input name="amount" type="number" step="0.01" required className="input mt-1" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Effective date
            <input name="effective_date" type="date" required className="input mt-1" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Reason
            <select name="reason" className="input mt-1" defaultValue="raise">
              <option value="raise">Raise</option>
              <option value="promotion">Promotion</option>
              <option value="adjustment">Adjustment</option>
              <option value="correction">Correction</option>
            </select>
          </label>
          <button
            type="submit"
            disabled={createSalary.isPending}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            Save
          </button>
        </form>
      )}
      {error && <p className="mb-4 text-sm text-status-critical">{error}</p>}

      {salaries.isLoading && <LoadingState />}
      {salaries.data && (
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2 font-medium">Amount</th>
              <th className="py-2 font-medium">Effective</th>
              <th className="py-2 font-medium">Ended</th>
              <th className="py-2 font-medium">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {salaries.data.items.map((salary) => (
              <tr key={salary.id}>
                <td className="py-2">
                  {salary.amount} {salary.currency}
                </td>
                <td className="py-2 text-gray-600">{salary.effective_date}</td>
                <td className="py-2 text-gray-600">{salary.end_date ?? '—'}</td>
                <td className="py-2">
                  <StatusBadge value={salary.reason} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function PromotionsTab({ employeeId }: { employeeId: number }) {
  const { hasRole } = useAuth()
  const employee = useEmployee(employeeId)
  const promotions = useEmployeePromotions(employeeId)
  const createPromotion = useCreatePromotion(employeeId)
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    // Captured before the `await` -- see the equivalent comment in
    // DepartmentsPage.handleCreate.
    const form = event.currentTarget
    const formData = new FormData(form)
    try {
      await createPromotion.mutateAsync({
        previous_job_title: employee.data?.job_title ?? '',
        new_job_title: String(formData.get('new_job_title')),
        promotion_date: String(formData.get('promotion_date')),
      })
      setShowForm(false)
      form.reset()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to record the promotion.')
    }
  }

  return (
    <div>
      {hasRole(...ROLES_WITH_EMPLOYEES_WRITE) && (
        <button
          type="button"
          onClick={() => setShowForm((value) => !value)}
          className="mb-4 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
        >
          {showForm ? 'Cancel' : 'Record promotion'}
        </button>
      )}
      {showForm && (
        <form onSubmit={handleSubmit} className="mb-6 flex max-w-xl items-end gap-3">
          <label className="block text-sm font-medium text-gray-700">
            New job title
            <input name="new_job_title" required className="input mt-1" />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Date
            <input name="promotion_date" type="date" required className="input mt-1" />
          </label>
          <button
            type="submit"
            disabled={createPromotion.isPending}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            Save
          </button>
        </form>
      )}
      {error && <p className="mb-4 text-sm text-status-critical">{error}</p>}

      {promotions.data && (
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
            <tr>
              <th className="py-2 font-medium">Date</th>
              <th className="py-2 font-medium">From</th>
              <th className="py-2 font-medium">To</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {promotions.data.items.map((promotion) => (
              <tr key={promotion.id}>
                <td className="py-2 text-gray-600">{promotion.promotion_date}</td>
                <td className="py-2 text-gray-600">{promotion.previous_job_title}</td>
                <td className="py-2 font-medium text-gray-900">{promotion.new_job_title}</td>
              </tr>
            ))}
            {promotions.data.items.length === 0 && (
              <tr>
                <td colSpan={3} className="py-6 text-center text-gray-500">
                  No promotions on record.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  )
}

function PredictionsTab({ employeeId }: { employeeId: number }) {
  const { hasRole } = useAuth()
  const predictions = useEmployeePredictions(employeeId)
  const triggerPrediction = useTriggerPrediction(employeeId)
  const updateStatus = useUpdateRecommendationStatus(employeeId)
  const [error, setError] = useState<string | null>(null)

  async function handleTrigger() {
    setError(null)
    try {
      await triggerPrediction.mutateAsync()
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail
          : 'Failed to score this employee. Has the ETL pipeline run yet?',
      )
    }
  }

  return (
    <div>
      {hasRole(...ROLES_WITH_PREDICTIONS_WRITE) && (
        <button
          type="button"
          onClick={handleTrigger}
          disabled={triggerPrediction.isPending}
          className="mb-4 rounded-md bg-brand-blue px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
        >
          {triggerPrediction.isPending ? 'Scoring…' : 'Run new prediction'}
        </button>
      )}
      {error && <p className="mb-4 text-sm text-status-critical">{error}</p>}

      {predictions.isLoading && <LoadingState />}
      {predictions.data?.items.length === 0 && (
        <p className="text-sm text-gray-500">No predictions on record for this employee yet.</p>
      )}
      <div className="space-y-4">
        {predictions.data?.items.map((prediction) => (
          <div key={prediction.id} className="rounded-lg border border-gray-200 bg-white p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <RiskBadge level={prediction.risk_level} />
                <span className="text-sm text-gray-600">
                  risk score {Number(prediction.risk_score).toFixed(2)}
                </span>
              </div>
              <span className="text-xs text-gray-400">
                {new Date(prediction.predicted_at).toLocaleString()}
              </span>
            </div>
            {prediction.recommendations.length > 0 && (
              <ul className="mt-3 space-y-2">
                {prediction.recommendations.map((recommendation) => (
                  <li
                    key={recommendation.id}
                    className="flex items-center justify-between gap-3 rounded-md bg-gray-50 px-3 py-2 text-sm"
                  >
                    <div>
                      <span className="font-medium capitalize text-gray-900">
                        {recommendation.action_type.replaceAll('_', ' ')}
                      </span>
                      <p className="text-gray-600">{recommendation.rationale}</p>
                    </div>
                    {hasRole(...ROLES_WITH_PREDICTIONS_WRITE) ? (
                      <select
                        value={recommendation.status}
                        onChange={(event) =>
                          updateStatus.mutate({
                            id: recommendation.id,
                            status: event.target.value as RecommendationStatus,
                          })
                        }
                        className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                      >
                        <option value="pending">Pending</option>
                        <option value="in_progress">In progress</option>
                        <option value="completed">Completed</option>
                        <option value="dismissed">Dismissed</option>
                      </select>
                    ) : (
                      <StatusBadge value={recommendation.status} />
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
