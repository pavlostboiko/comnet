/**
 * Integration tests for /api/users — CRUD + admin-only enforcement.
 *
 * Uses the bootstrap admin (TEST_USER/TEST_PASS, role=admin) and creates
 * disposable users with unique names so a parallel run doesn't collide.
 */
const { test, expect, request: pwRequest } = require('@playwright/test')
const { API, loginApi, getToken } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Users API', () => {
  let api
  let extraCleanup

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    extraCleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, extraCleanup)
    await api.dispose()
  })

  test('admin CRUD round-trip: create → list → update role → set password → delete', async () => {
    const username = `u-${Date.now()}`
    const password = 'pw-initial'

    // create
    const created = await postJson(api, '/api/users', {
      username, password, role: 'operator', is_active: true,
    })
    extraCleanup.push(`/api/users/${created.id}`)
    expect(created.username).toBe(username)
    expect(created.role).toBe('operator')
    expect(created.is_active).toBe(true)

    // list — should include our new user
    const list = await api.get('/api/users').then(r => r.json())
    expect(list.some(u => u.id === created.id)).toBe(true)

    // update role + deactivate
    const updated = await api.put(`/api/users/${created.id}`, { data: {
      role: 'admin', is_active: false,
    }}).then(r => r.json())
    expect(updated.role).toBe('admin')
    expect(updated.is_active).toBe(false)

    // set password to a new value (no response body for 204)
    const pwResp = await api.post(`/api/users/${created.id}/password`, { data: {
      password: 'pw-rotated',
    }})
    expect(pwResp.status()).toBe(204)
  })

  test('username uniqueness: duplicate POST returns 409', async () => {
    const username = `dup-${Date.now()}`
    const a = await postJson(api, '/api/users', {
      username, password: 'first', role: 'admin', is_active: true,
    })
    extraCleanup.push(`/api/users/${a.id}`)

    const resp = await api.post('/api/users', { data: {
      username, password: 'second', role: 'admin', is_active: true,
    }})
    expect(resp.status()).toBe(409)
  })

  test('cannot delete yourself', async () => {
    const me = await api.get('/api/auth/me').then(r => r.json())
    const resp = await api.delete(`/api/users/${me.id}`)
    expect(resp.status()).toBe(400)
  })

  test('non-admin user gets 403 on /api/users', async ({ request }) => {
    // Create an operator via admin api
    const username = `op-${Date.now()}`
    const password = 'pw-op'
    const op = await postJson(api, '/api/users', {
      username, password, role: 'operator', is_active: true,
    })
    extraCleanup.push(`/api/users/${op.id}`)

    // Log in AS that operator and try to list users
    const opToken = await getToken(request, { user: username, pass: password })
    const opApi = await pwRequest.newContext({
      baseURL: API,
      extraHTTPHeaders: { Authorization: `Bearer ${opToken}` },
    })
    try {
      const resp = await opApi.get('/api/users')
      expect(resp.status()).toBe(403)
    } finally {
      await opApi.dispose()
    }
  })
})
