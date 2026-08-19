import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, setAccessToken, setUnauthorizedHandler } from '../api/client'
import type { TokenPair, User } from '../api/types'

const STORAGE_KEY = 'retention-platform.auth'

interface StoredAuth {
  access_token: string
  refresh_token: string
}

function readStoredAuth(): StoredAuth | null {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as StoredAuth
  } catch {
    return null
  }
}

function writeStoredAuth(auth: StoredAuth | null): void {
  if (auth) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(auth))
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export interface AuthContextValue {
  user: User | null
  /** True while the initial session (if any) is being rehydrated on load. */
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  hasRole: (...roles: string[]) => boolean
}

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    setAccessToken(null)
    writeStoredAuth(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(null)
  }, [logout])

  useEffect(() => {
    const stored = readStoredAuth()
    if (!stored) {
      setIsLoading(false)
      return
    }
    setAccessToken(stored.access_token)
    api
      .get<User>('/auth/me')
      .then(setUser)
      .catch(() => {
        writeStoredAuth(null)
        setAccessToken(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await api.post<TokenPair>(
      '/auth/login',
      { email, password },
      { anonymous: true },
    )
    setAccessToken(tokens.access_token)
    writeStoredAuth({ access_token: tokens.access_token, refresh_token: tokens.refresh_token })
    const me = await api.get<User>('/auth/me')
    setUser(me)
  }, [])

  const hasRole = useCallback(
    (...roles: string[]) => user !== null && roles.some((role) => user.roles.includes(role)),
    [user],
  )

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, logout, hasRole }),
    [user, isLoading, login, logout, hasRole],
  )

  return <AuthContext value={value}>{children}</AuthContext>
}
