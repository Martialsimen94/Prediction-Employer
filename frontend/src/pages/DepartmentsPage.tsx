import { useState, type FormEvent } from 'react'
import {
  useCreateDepartment,
  useDeleteDepartment,
  useDepartments,
  useUpdateDepartment,
} from '../api/queries'
import { useAuth } from '../auth/useAuth'
import { ROLES_WITH_EMPLOYEES_WRITE } from '../auth/permissions'
import { ErrorState, LoadingState } from '../components/AsyncState'
import { ApiError } from '../api/client'
import type { Department } from '../api/types'

export function DepartmentsPage() {
  const { hasRole } = useAuth()
  const canManage = hasRole(...ROLES_WITH_EMPLOYEES_WRITE)
  const departments = useDepartments({ limit: 100 })
  const createDepartment = useCreateDepartment()
  const [showForm, setShowForm] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleCreate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    // Captured before the `await`: React nulls out a SyntheticEvent's
    // currentTarget once the handler yields, so `event.currentTarget` is no
    // longer safe to read after this point.
    const form = event.currentTarget
    const formData = new FormData(form)
    try {
      await createDepartment.mutateAsync({ name: String(formData.get('name')) })
      setShowForm(false)
      form.reset()
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to create the department.')
    }
  }

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Departments</h1>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowForm((value) => !value)}
            className="rounded-md bg-brand-blue px-3 py-2 text-sm font-medium text-white hover:bg-brand-blue/90"
          >
            {showForm ? 'Cancel' : 'New department'}
          </button>
        )}
      </div>

      {showForm && (
        <form onSubmit={handleCreate} className="mt-4 flex max-w-md items-end gap-3">
          <label className="flex-1 text-sm font-medium text-gray-700">
            Name
            <input name="name" required className="input mt-1" />
          </label>
          <button
            type="submit"
            disabled={createDepartment.isPending}
            className="rounded-md bg-brand-blue px-4 py-2 text-sm font-medium text-white hover:bg-brand-blue/90 disabled:opacity-60"
          >
            Save
          </button>
        </form>
      )}
      {error && <p className="mt-3 text-sm text-status-critical">{error}</p>}

      <div className="mt-4 overflow-hidden rounded-lg border border-gray-200 bg-white">
        {departments.isLoading && <LoadingState />}
        {departments.isError && <ErrorState message="Failed to load departments." />}
        {departments.data && (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 bg-gray-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-2 font-medium">Name</th>
                <th className="px-4 py-2 font-medium">Description</th>
                {canManage && <th className="px-4 py-2 font-medium" />}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {departments.data.items.map((department) => (
                <DepartmentRow key={department.id} department={department} canManage={canManage} />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

function DepartmentRow({ department, canManage }: { department: Department; canManage: boolean }) {
  const updateDepartment = useUpdateDepartment(department.id)
  const deleteDepartment = useDeleteDepartment()
  const [isEditing, setIsEditing] = useState(false)

  if (isEditing) {
    return (
      <tr>
        <td className="px-4 py-2" colSpan={canManage ? 3 : 2}>
          <form
            className="flex items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault()
              const formData = new FormData(event.currentTarget)
              updateDepartment.mutate(
                {
                  name: String(formData.get('name')),
                  description: String(formData.get('description') || '') || null,
                },
                { onSuccess: () => setIsEditing(false) },
              )
            }}
          >
            <input name="name" defaultValue={department.name} className="input" />
            <input
              name="description"
              defaultValue={department.description ?? ''}
              placeholder="Description"
              className="input"
            />
            <button
              type="submit"
              className="whitespace-nowrap rounded-md bg-brand-blue px-3 py-1.5 text-sm text-white"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="whitespace-nowrap rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700"
            >
              Cancel
            </button>
          </form>
        </td>
      </tr>
    )
  }

  return (
    <tr>
      <td className="px-4 py-3 font-medium text-gray-900">{department.name}</td>
      <td className="px-4 py-3 text-gray-600">{department.description ?? '—'}</td>
      {canManage && (
        <td className="px-4 py-3 text-right">
          <button
            type="button"
            onClick={() => setIsEditing(true)}
            className="mr-3 text-sm text-brand-blue hover:underline"
          >
            Edit
          </button>
          <button
            type="button"
            onClick={() => {
              if (confirm(`Delete ${department.name}?`)) {
                deleteDepartment.mutate(department.id)
              }
            }}
            className="text-sm text-status-critical hover:underline"
          >
            Delete
          </button>
        </td>
      )}
    </tr>
  )
}
