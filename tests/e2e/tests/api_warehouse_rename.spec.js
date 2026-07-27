const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('rename a warehouse (name only; type/binding unchanged)', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `rn-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const unit = await postJson(api, '/api/structure/units', { name: `Дуже довга назва підрозділу ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`)
    const wh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === unit.id)
    expect(wh.name).toContain('Дуже довга')

    const resp = await api.put(`/api/structure/warehouses/${wh.id}`, { data: { name: `СК-${tag}` } })
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.name).toBe(`СК-${tag}`)
    expect(body.type).toBe('unit')          // unchanged
    expect(body.unit_id).toBe(unit.id)      // unchanged

    // empty name rejected
    const bad = await api.put(`/api/structure/warehouses/${wh.id}`, { data: { name: '  ' } })
    expect(bad.status()).toBe(400)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
