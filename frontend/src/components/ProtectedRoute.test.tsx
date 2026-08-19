import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext'
import { ProtectedRoute } from './ProtectedRoute'

function renderProtected(roles?: string[]) {
  return render(
    <MemoryRouter initialEntries={['/employees']}>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<div>login screen</div>} />
          <Route
            path="/employees"
            element={
              <ProtectedRoute roles={roles}>
                <div>employees content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('ProtectedRoute', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('redirects to /login when there is no session', async () => {
    renderProtected()
    expect(await screen.findByText('login screen')).toBeInTheDocument()
  })
})
