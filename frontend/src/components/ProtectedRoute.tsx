import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useAuth } from '../auth/useAuth'
import { LoadingState } from './AsyncState'

export function ProtectedRoute({ children, roles }: { children: ReactNode; roles?: string[] }) {
  const { user, isLoading, hasRole } = useAuth()

  if (isLoading) return <LoadingState label="Checking your session…" />
  if (!user) return <Navigate to="/login" replace />
  if (roles && !hasRole(...roles)) {
    return (
      <div className="mx-auto max-w-lg py-16 text-center text-gray-600">
        You don&apos;t have access to this page.
      </div>
    )
  }
  return <>{children}</>
}
