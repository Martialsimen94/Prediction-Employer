import { Navigate } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { ROLES_WITH_EMPLOYEES_READ } from '../auth/permissions'

/** "/" has no content of its own -- it just routes each role to the page
 * that's actually useful to them. */
export function HomePage() {
  const { hasRole } = useAuth()
  const destination = hasRole(...ROLES_WITH_EMPLOYEES_READ) ? '/employees' : '/notifications'
  return <Navigate to={destination} replace />
}
