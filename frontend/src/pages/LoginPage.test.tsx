import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from './LoginPage'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('shows the API error message when login fails', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Invalid email or password' }, 401)),
    )
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Email'), 'wrong@example.com')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Invalid email or password')).toBeInTheDocument()
  })

  it('requests a token pair then the current user on successful login', async () => {
    const fetchSpy = vi.fn().mockImplementation((url: string) => {
      if (url.toString().includes('/auth/login')) {
        return Promise.resolve(
          jsonResponse({ access_token: 'access', refresh_token: 'refresh', token_type: 'bearer' }),
        )
      }
      return Promise.resolve(
        jsonResponse({
          id: 1,
          email: 'hr@example.com',
          is_active: true,
          roles: ['hr'],
          employee_id: null,
        }),
      )
    })
    vi.stubGlobal('fetch', fetchSpy)
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Email'), 'hr@example.com')
    await user.type(screen.getByLabelText('Password'), 'correct-horse-1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        expect.stringContaining('/auth/login'),
        expect.objectContaining({ method: 'POST' }),
      )
      expect(fetchSpy).toHaveBeenCalledWith(expect.stringContaining('/auth/me'), expect.anything())
    })
  })
})
