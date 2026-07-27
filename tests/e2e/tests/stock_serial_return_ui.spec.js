const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// A serial item at a unit warehouse: issue to a person, then the row itself
// offers «Повернути» (no need to hunt the «Видано особам» section).
test('serial issue then row-level return on Залишки', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())

  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `SRSvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `SRРота ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const person = await j('/api/settings/persons', { first_name: 'С', last_name: `Боєць${ts}`, unit_id: unit.id })
  const nom = await j('/api/nomenclature', { name: `Рація ${ts}`, service_id: svc.id, unit_of_measure: 'шт', price: 100, is_serialized: true })
  const inst = await j(`/api/nomenclature/${nom.id}/instances`, { serial_no: `SN-${ts}` })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, instance_id: inst.id, to_warehouse_id: svcWh.id })
  await j('/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, instance_id: inst.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id })

  page.on('dialog', d => d.accept())   // confirm() on return
  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: unitWh.name }).click()

  const row = page.locator('tbody tr', { hasText: `SN-${ts}` }).first()
  await expect(row.locator('.btn-issue')).toBeVisible()          // free → «Видати»
  await row.locator('.btn-issue').click()
  await page.locator('.modal select').first().selectOption({ label: `Боєць${ts} С` })
  await page.locator('.btn-pri', { hasText: 'Видати' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)

  // now the same row offers «Повернути»
  const rowAfter = page.locator('tbody tr', { hasText: `SN-${ts}` }).first()
  await expect(rowAfter.locator('.btn-return')).toBeVisible()
  await rowAfter.locator('.btn-return').click()

  // returned → row is issuable again
  await expect(page.locator('tbody tr', { hasText: `SN-${ts}` }).first().locator('.btn-issue')).toBeVisible()

  // per-instance history lists the issue/return events
  await page.locator('tbody tr', { hasText: `SN-${ts}` }).first().locator('.btn-hist').click()
  await expect(page.locator('.modal-title', { hasText: 'Історія' })).toBeVisible()
  await expect(page.locator('.modal').filter({ hasText: 'видано' })).toBeVisible()

  await api.delete(`/api/settings/persons/${person.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
