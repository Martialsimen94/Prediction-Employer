import { Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { ProtectedRoute } from './components/ProtectedRoute'
import { ROLES_WITH_EMPLOYEES_READ, ROLES_WITH_EMPLOYEES_WRITE } from './auth/permissions'
import { LoginPage } from './pages/LoginPage'
import { HomePage } from './pages/HomePage'
import { EmployeesPage } from './pages/EmployeesPage'
import { EmployeeFormPage } from './pages/EmployeeFormPage'
import { EmployeeDetailPage } from './pages/EmployeeDetailPage'
import { DepartmentsPage } from './pages/DepartmentsPage'
import { NotificationsPage } from './pages/NotificationsPage'
import { NotFoundPage } from './pages/NotFoundPage'

export function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<HomePage />} />
        <Route
          path="/employees"
          element={
            <ProtectedRoute roles={ROLES_WITH_EMPLOYEES_READ}>
              <EmployeesPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/employees/new"
          element={
            <ProtectedRoute roles={ROLES_WITH_EMPLOYEES_WRITE}>
              <EmployeeFormPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/employees/:id"
          element={
            <ProtectedRoute roles={ROLES_WITH_EMPLOYEES_READ}>
              <EmployeeDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/departments"
          element={
            <ProtectedRoute roles={ROLES_WITH_EMPLOYEES_READ}>
              <DepartmentsPage />
            </ProtectedRoute>
          }
        />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
