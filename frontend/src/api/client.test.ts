import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, api, setAccessToken, setUnauthorizedHandler } from './client'

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('api client', () => {
  beforeEach(() => {
    setAccessToken(null)
    setUnauthorizedHandler(null)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches the bearer token to authenticated requests', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchSpy)

    setAccessToken('test-token')
    await api.get('/employees')

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer test-token')
  })

  it('omits the Authorization header for anonymous requests', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(jsonResponse({ access_token: 'x' }))
    vi.stubGlobal('fetch', fetchSpy)

    setAccessToken('test-token')
    await api.post('/auth/login', { email: 'a@b.com', password: 'x' }, { anonymous: true })

    const [, init] = fetchSpy.mock.calls[0] as [string, RequestInit]
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined()
  })

  it('throws an ApiError carrying the response detail on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse({ detail: 'Employee not found' }, 404)),
    )

    await expect(api.get('/employees/999')).rejects.toMatchObject(
      new ApiError(404, 'Employee not found'),
    )
  })

  it('calls the unauthorized handler on a 401', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ detail: 'nope' }, 401)))
    const onUnauthorized = vi.fn()
    setUnauthorizedHandler(onUnauthorized)

    await expect(api.get('/employees')).rejects.toBeInstanceOf(ApiError)
    expect(onUnauthorized).toHaveBeenCalledOnce()
  })

  it('drops empty/undefined query params rather than sending them', async () => {
    const fetchSpy = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchSpy)

    await api.get('/employees', { search: '', department_id: undefined, limit: 20 })

    const [url] = fetchSpy.mock.calls[0] as [string]
    expect(url).toContain('limit=20')
    expect(url).not.toContain('search=')
    expect(url).not.toContain('department_id=')
  })
})
