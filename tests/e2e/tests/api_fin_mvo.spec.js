/**
 * Global фінслужба МВО (kind='fin'): warehouse-less, one active at a time,
 * visible to ALL users (not service-scoped).
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { closeActiveFin } = require('./helpers/mvo')

test('fin МВО is global, single-active, visible to all', async ({ request }) => {
  const admin = await loginApi(request)
  const S = Date.now()
  try {
    await closeActiveFin(admin)   // global fin is a singleton — start clean
    const p1 = await admin.post('/api/settings/persons', { data: { last_name: `Фін1-${S}` } }).then(r => r.json())
    const p2 = await admin.post('/api/settings/persons', { data: { last_name: `Фін2-${S}` } }).then(r => r.json())

    // Create the global fin МВО (no warehouse)
    const m1 = await admin.post('/api/structure/mvo', { data: {
      kind: 'fin', person_id: p1.id, from_date: '2026-01-01' } })
    expect(m1.status()).toBe(201)
    const m1row = await m1.json()
    expect(m1row.kind).toBe('fin')
    expect(m1row.warehouse_id ?? null).toBeNull()
    expect(m1row.to_date).toBeNull()

    // Second active fin → 409
    const dup = await admin.post('/api/structure/mvo', { data: {
      kind: 'fin', person_id: p2.id, from_date: '2026-06-01' } })
    expect(dup.status()).toBe(409)

    // Rotation: close m1, then a new active fin is allowed
    await admin.put(`/api/structure/mvo/${m1row.id}`, { data: { to_date: '2026-06-30' } })
    const m2 = await admin.post('/api/structure/mvo', { data: {
      kind: 'fin', person_id: p2.id, from_date: '2026-07-01' } })
    expect(m2.status()).toBe(201)

    // Visible to a service-role user (not scoped)
    const username = `svc-fin-${S}`
    const svc = await admin.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    await admin.post('/api/users', { data: { username, password: 'test1234', role: 'service', service_id: svc.id } })
    const svcApi = await loginApi(request, { user: username, pass: 'test1234' })
    const seen = await svcApi.get('/api/structure/mvo').then(r => r.json())
    expect(seen.some(m => m.kind === 'fin' && m.person_id === p2.id && m.to_date === null)).toBe(true)
    await svcApi.dispose()
  } finally {
    await admin.dispose()
  }
})
