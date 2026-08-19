import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAllDepartments, useEmployees } from '../api/queries'
import { useAuth } from '../auth/useAuth'
import { ROLES_WITH_EMPLOYEES_WRITE } from '../auth/permissions'
import { StatusBadge } from '../components/StatusBadge'
import { Pagination } from '../components/Pagination'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { ApiError } from '../api/client'

const LIMIT = 20

export function EmployeesPage() {
  const { hasRole } = useAuth()
  const [search, setSearch] = useState('')
  const [departmentId, setDepartmentId] = useState<number | undefined>(undefined)
  const [offset, setOffset] = useState(0)

  const departments = useAllDepartments()
  const employees = useEmployees({
    search: search || undefined,
    department_id: departmentId,
    limit: LIMIT,
    offset,
  })

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Employees</h1>
        {hasRole(...ROLES_WITH_EMPLOYEES_WRITE) && (
          <Link
            to="/employees/new"
            className="rounded-md bg-brand-blue px-3 py-2 text-sm font-medium text-white hover:bg-brand-blue/90"
          >
            New employee
          </Link>
        )}
      </div>

      <div className="mt-4 flex gap-3">
        <input
          type="search"
          placeholder="Search by name, email, employee number…"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setOffset(0)
          }}
          className="w-72 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
        />
        <select
          value={departmentId ?? ''}
          onChange={(event) => {
            setDepartmentId(event.target.value ? Number(event.target.value) : undefined)
            setOffset(0)
          }}
          className="rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-brand-blue focus:outline-none"
        >
          <option value="">All departments</option>
          {departments.data?.items.map((department) => (
            <option key={department.id} value={department.id}>
              {department.name}
            </option>
          ))}
        </select>
      </div>

      <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 bg-white">
        {employees.isLoading && <LoadingState />}
        {employees.isError && (
          <ErrorState
            message={
              employees.error instanceof ApiError
                ? employees.error.detail
                : 'Failed to load employees.'
            }
          />
        )}
        {employees.data && (
          <>
            <table className="w-full text-left text-sm">
              <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Employee</th>
                  <th className="px-4 py-2 font-medium">Job title</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {employees.data.items.map((employee) => (
                  <tr key={employee.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <Link
                        to={`/employees/${employee.id}`}
                        className="font-medium text-brand-blue hover:underline"
                      >
                        {employee.first_name} {employee.last_name}
                      </Link>
                      <div className="text-xs text-gray-500">{employee.employee_number}</div>
                    </td>
                    <td className="px-4 py-3 text-gray-700">{employee.job_title}</td>
                    <td className="px-4 py-3">
                      <StatusBadge value={employee.employment_status} />
                    </td>
                  </tr>
                ))}
                {employees.data.items.length === 0 && (
                  <tr>
                    <td colSpan={3} className="px-4 py-8 text-center text-sm text-gray-500">
                      No employees match your search.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
            <div className="px-4">
              <Pagination
                total={employees.data.total}
                limit={LIMIT}
                offset={offset}
                onOffsetChange={setOffset}
              />
            </div>
          </>
        )}
      </div>
    </div>
  )
}
