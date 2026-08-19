import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ROLES_WITH_EMPLOYEES_READ } from '../auth/permissions'

const NAV_LINK_CLASS = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-3 py-2 text-sm font-medium ${
    isActive ? 'bg-brand-blue/10 text-brand-blue' : 'text-gray-600 hover:bg-gray-100'
  }`

export function Layout() {
  const { user, logout, hasRole } = useAuth()

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="border-b border-gray-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-6">
            <span className="text-sm font-semibold text-gray-900">Retention Platform</span>
            <nav className="flex gap-1">
              {hasRole(...ROLES_WITH_EMPLOYEES_READ) && (
                <>
                  <NavLink to="/employees" className={NAV_LINK_CLASS}>
                    Employees
                  </NavLink>
                  <NavLink to="/departments" className={NAV_LINK_CLASS}>
                    Departments
                  </NavLink>
                </>
              )}
              <NavLink to="/notifications" className={NAV_LINK_CLASS}>
                Notifications
              </NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-600">
            <span>{user?.email}</span>
            <button
              type="button"
              onClick={logout}
              className="rounded-md border border-gray-300 px-3 py-1.5 font-medium text-gray-700 hover:bg-gray-100"
            >
              Log out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  )
}
