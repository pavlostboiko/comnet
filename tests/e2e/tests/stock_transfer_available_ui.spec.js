const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// «Додати переміщення» dropdown lists only майно actually available on the
// current warehouse: cards with no stock here are hidden, and issued serial
// instances are excluded.
test('transfer dropdown shows only available stock on the current warehouse', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const move = (b) => j('/api/custody/movements', b)

  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `AvSvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `AvРота ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const person = await j('/api/settings/persons', { first_name: 'І', last_name: `Боєць${ts}`, unit_id: unit.id })

  // A: serial at svc (available here)
  const A = await j('/api/nomenclature', { name: `Ая ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const iA = await j(`/api/nomenclature/${A.id}/instances`, { serial_no: `A-${ts}` })
  await move({ date: '2026-07-01', type: 'receipt', nomenclature_id: A.id, instance_id: iA.id, to_warehouse_id: svcWh.id })
  // B: serial received to svc then moved to unit (NOT at svc; available at unit)
  const B = await j('/api/nomenclature', { name: `Бя ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const iB = await j(`/api/nomenclature/${B.id}/instances`, { serial_no: `B-${ts}` })
  await move({ date: '2026-07-01', type: 'receipt', nomenclature_id: B.id, instance_id: iB.id, to_warehouse_id: svcWh.id })
  await move({ date: '2026-07-02', type: 'transfer', nomenclature_id: B.id, instance_id: iB.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id })
  // C: non-serial with stock at svc
  const C = await j('/api/nomenclature', { name: `Ця ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await move({ date: '2026-07-01', type: 'receipt', nomenclature_id: C.id, to_warehouse_id: svcWh.id, quantity: 5 })
  // D: no stock anywhere
  const D = await j('/api/nomenclature', { name: `Дя ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  // E: serial moved to unit then issued to a person (unavailable for transfer)
  const E = await j('/api/nomenclature', { name: `Ея ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const iE = await j(`/api/nomenclature/${E.id}/instances`, { serial_no: `E-${ts}` })
  await move({ date: '2026-07-01', type: 'receipt', nomenclature_id: E.id, instance_id: iE.id, to_warehouse_id: svcWh.id })
  await move({ date: '2026-07-02', type: 'transfer', nomenclature_id: E.id, instance_id: iE.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id })
  await j('/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: E.id, instance_id: iE.id, quantity: 1, is_official: true, issued_date: '2026-07-03' })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)

  const search = async (query) => {
    const input = page.locator('.doc-row').first().locator('.cell-input')
    await input.click(); await input.fill(query)
  }

  // From the SERVICE warehouse: A and C available; B, D absent
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await page.locator('button', { hasText: 'Додати переміщення' }).click()
  await search(`Ая ${ts}`); await expect(page.locator('.ac-item', { hasText: `Ая ${ts}` })).toHaveCount(1)
  await search(`Ця ${ts}`); await expect(page.locator('.ac-item', { hasText: `Ця ${ts}` })).toHaveCount(1)
  await search(`Бя ${ts}`); await expect(page.locator('.ac-item', { hasText: `Бя ${ts}` })).toHaveCount(0)
  await search(`Дя ${ts}`); await expect(page.locator('.ac-item', { hasText: `Дя ${ts}` })).toHaveCount(0)
  await page.locator('.modal-close').click()

  // From the UNIT warehouse: B available (here, not issued); E absent (issued)
  await page.locator('.wh-btn', { hasText: unitWh.name }).click()
  await page.locator('button', { hasText: 'Додати переміщення' }).click()
  await search(`Бя ${ts}`); await expect(page.locator('.ac-item', { hasText: `Бя ${ts}` })).toHaveCount(1)
  await search(`Ея ${ts}`); await expect(page.locator('.ac-item', { hasText: `Ея ${ts}` })).toHaveCount(0)

  await api.delete(`/api/settings/persons/${person.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
