/**
 * A service-role user sees only their own service's nomenclature (and totals);
 * admin sees everything.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('nomenclature + totals scoped to own service for a service user', async ({ request }) => {
  const admin = await loginApi(request)
  const S = Date.now()
  const svcX = await admin.post('/api/settings/services', { data: { name: `SvcX-${S}` } }).then(r => r.json())
  const svcY = await admin.post('/api/settings/services', { data: { name: `SvcY-${S}` } }).then(r => r.json())
  const mkNom = (svc, tag) => admin.post('/api/nomenclature', { data: {
    name: `Nom${tag}-${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  const nomX = await mkNom(svcX, 'X')
  const nomY = await mkNom(svcY, 'Y')
  // stock for both (to exercise totals scoping)
  const u = await admin.post('/api/structure/units', { data: { name: `U-${S}` } }).then(r => r.json())
  const wh = (await admin.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
  await admin.post('/api/custody/movements', { data: { type: 'receipt', to_warehouse_id: wh.id, nomenclature_id: nomX.id, quantity: 5, date: '2026-07-10' } })
  await admin.post('/api/custody/movements', { data: { type: 'receipt', to_warehouse_id: wh.id, nomenclature_id: nomY.id, quantity: 3, date: '2026-07-10' } })
  const username = `svcuser-${S}`
  await admin.post('/api/users', { data: { username, password: 'test1234', role: 'service', service_id: svcX.id } })

  // admin sees both
  const adminNoms = await admin.get('/api/nomenclature').then(r => r.json())
  expect(adminNoms.some(n => n.id === nomX.id)).toBe(true)
  expect(adminNoms.some(n => n.id === nomY.id)).toBe(true)
  await admin.dispose()

  // service user sees only their service
  const svcApi = await loginApi(request, { user: username, pass: 'test1234' })
  try {
    const noms = await svcApi.get('/api/nomenclature').then(r => r.json())
    expect(noms.some(n => n.id === nomX.id)).toBe(true)
    expect(noms.some(n => n.id === nomY.id)).toBe(false)
    expect(noms.every(n => n.service_id === svcX.id)).toBe(true)

    const totals = await svcApi.get('/api/custody/totals').then(r => r.json())
    expect(totals[String(nomX.id)]).toBeTruthy()
    expect(totals[String(nomY.id)]).toBeUndefined()
  } finally {
    await svcApi.dispose()
  }
})
