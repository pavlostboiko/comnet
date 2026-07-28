/**
 * МВО can be assigned to a SERVICE warehouse (needed for document signatories /
 * фінслужба) and to INTERNAL unit warehouses, but NOT to external ones.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('mvo: service + internal unit warehouses allowed, external forbidden', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const svcWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.service_id === svc.id && w.type === 'service')
    const person = await api.post('/api/settings/persons', { data: { last_name: `МВО${S}` } }).then(r => r.json())
    const whOf = async (unit) => (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === unit.id)
    const inUnit = await api.post('/api/structure/units', { data: { name: `In${S}`, is_external: false } }).then(r => r.json())
    const exUnit = await api.post('/api/structure/units', { data: { name: `Ex${S}`, is_external: true } }).then(r => r.json())

    // Service warehouse → allowed
    const onSvc = await api.post('/api/structure/mvo', { data: {
      warehouse_id: svcWh.id, person_id: person.id, from_date: '2026-07-01' } })
    expect(onSvc.status()).toBe(201)

    // Internal unit → allowed
    const onIn = await api.post('/api/structure/mvo', { data: {
      warehouse_id: (await whOf(inUnit)).id, person_id: person.id, from_date: '2026-07-01' } })
    expect(onIn.status()).toBe(201)

    // External unit → forbidden
    const onEx = await api.post('/api/structure/mvo', { data: {
      warehouse_id: (await whOf(exUnit)).id, person_id: person.id, from_date: '2026-07-01' } })
    expect(onEx.status()).toBe(400)
    expect((await onEx.json()).detail).toContain('зовнішн')
  } finally {
    await api.dispose()
  }
})
