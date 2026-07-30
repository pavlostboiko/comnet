/**
 * МВО journal entries can be fully edited (person + dates) and deleted.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('mvo entry: full edit (person + dates) and delete', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const u = await api.post('/api/structure/units', { data: { name: `U${S}` } }).then(r => r.json())
    const wh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
    const pA = await api.post('/api/settings/persons', { data: { last_name: `A${S}` } }).then(r => r.json())
    const pB = await api.post('/api/settings/persons', { data: { last_name: `B${S}` } }).then(r => r.json())

    const m = await api.post('/api/structure/mvo', { data: {
      warehouse_id: wh.id, person_id: pA.id, from_date: '2026-01-01' } }).then(r => r.json())

    // Full edit: change person + both dates
    const upd = await api.put(`/api/structure/mvo/${m.id}`, { data: {
      person_id: pB.id, from_date: '2026-02-01', to_date: '2026-03-01' } })
    expect(upd.ok()).toBe(true)
    const row = await upd.json()
    expect(row.person_id).toBe(pB.id)
    expect(row.from_date).toBe('2026-02-01')
    expect(row.to_date).toBe('2026-03-01')

    // Bad period → 400
    const bad = await api.put(`/api/structure/mvo/${m.id}`, { data: { to_date: '2026-01-15' } })
    expect(bad.status()).toBe(400)

    // Delete
    expect((await api.delete(`/api/structure/mvo/${m.id}`)).status()).toBe(204)
    const after = await api.get('/api/structure/mvo').then(r => r.json())
    expect(after.some(x => x.id === m.id)).toBe(false)
  } finally {
    await api.dispose()
  }
})
