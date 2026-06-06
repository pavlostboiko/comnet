/**
 * /api/recipients CRUD + uniqueness check.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Recipients API', () => {
  let api
  let cleanup

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    cleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  })

  test('CRUD: create → list → update → delete', async () => {
    const callsign = `Test-${Date.now()}`

    const created = await postJson(api, '/api/recipients', { callsign })
    cleanup.push(`/api/recipients/${created.id}`)
    expect(created.callsign).toBe(callsign)
    expect(created.is_active).toBe(true)

    const list = await api.get('/api/recipients').then(r => r.json())
    expect(list.some(r => r.id === created.id)).toBe(true)

    // PUT requires admin (test seed user is admin)
    const updated = await api.put(`/api/recipients/${created.id}`, { data: {
      callsign: `${callsign}-renamed`, is_active: false,
    }}).then(r => r.json())
    expect(updated.callsign).toBe(`${callsign}-renamed`)
    expect(updated.is_active).toBe(false)
  })

  test('callsign uniqueness: duplicate POST returns 409', async () => {
    const callsign = `Dup-${Date.now()}`
    const first = await postJson(api, '/api/recipients', { callsign })
    cleanup.push(`/api/recipients/${first.id}`)

    const resp = await api.post('/api/recipients', { data: { callsign } })
    expect(resp.status()).toBe(409)
  })

  test('empty callsign rejected with 400', async () => {
    const resp = await api.post('/api/recipients', { data: { callsign: '   ' } })
    expect(resp.status()).toBe(400)
  })
})
