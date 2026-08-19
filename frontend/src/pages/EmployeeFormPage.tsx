import { useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAllDepartments, useCreateEmployee } from '../api/queries'
import { ApiError } from '../api/client'
import type { EmploymentStatus } from '../api/types'

export function EmployeeFormPage() {
  const navigate = useNavigate()
  const departments = useAllDepartments()
  const createEmployee = useCreateEmployee()

  const [form, setForm] = useState({
    employee_number: '',
    first_name: '',
    last_name: '',
    email: '',
    hire_date: '',
    job_title: '',
    department_id: '',
    employment_status: 'active' as EmploymentStatus,
  })
  const [error, setError] = useState<string | null>(null)

  function update<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((previous) => ({ ...previous, [key]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const employee = await createEmployee.mutateAsync({
        employee_number: form.employee_number,
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        hire_date: form.hire_date,
        job_title: form.job_title,
        employment_status: form.employment_status,
        department_id: form.department_id ? Number(form.department_id) : null,
      })
      navigate(`/employees/${employee.id}`)
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to create the employee.')
    }
  }

  return (
    <div className="max-w-xl">
      <h1 className="text-xl font-semibold text-gray-900">New employee</h1>

      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Employee number">
            <input
              required
              value={form.employee_number}
              onChange={(event) => update('employee_number', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Job title">
            <input
              required
              value={form.job_title}
              onChange={(event) => update('job_title', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="First name">
            <input
              required
              value={form.first_name}
              onChange={(event) => update('first_name', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Last name">
            <input
              required
              value={form.last_name}
              onChange={(event) => update('last_name', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Email">
            <input
              required
              type="email"
              value={form.email}
              onChange={(event) => update('email', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Hire date">
            <input
              required
              type="date"
              value={form.hire_date}
              onChange={(event) => update('hire_date', event.target.value)}
              className="input"
            />
          </Field>
          <Field label="Department">
            <select
              value={form.department_id}
              onChange={(event) => update('department_id', event.target.value)}
              className="input"
            >
              <option value="">Unassigned</option>
              {departments.data?.items.map((department) => (
                <option key={department.id} value={department.id}>
                  {department.name}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {error && <p className="text-sm text-status-critical">{error}</p>}

        <div className="flex gap-3">
          <button
            type="submit"
            disabled={createEmployee.isPending}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            {createEmployee.isPending ? 'Creating…' : 'Create employee'}
          </button>
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-md border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <div className="mt-1">{children}</div>
    </label>
  )
}
