const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// «Додати переміщення»: searchable nomenclature dropdown + no duplicates
// (same serial instance can't be picked twice; same non-serial card can't be
// added twice).
test('transfer modal: search + dedup instances/cards', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())

  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `TSvc ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)

  // serial card with two instances placed at the source warehouse
  const ak = await j('/api/nomenclature', { name: `Автомат ${ts}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
  const a1 = await j(`/api/nomenclature/${ak.id}/instances`, { serial_no: `AK-1-${ts}` })
  const a2 = await j(`/api/nomenclature/${ak.id}/instances`, { serial_no: `AK-2-${ts}` })
  for (const inst of [a1, a2]) {
    await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: ak.id, instance_id: inst.id, to_warehouse_id: svcWh.id })
  }
  // non-serial card with stock
  const hat = await j('/api/nomenclature', { name: `Каска ${ts}`, service_id: svc.id, unit_of_measure: 'шт', price: 50 })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: hat.id, to_warehouse_id: svcWh.id, quantity: 10 })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await page.locator('button', { hasText: 'Додати переміщення' }).click()

  const pick = async (rowIdx, query, optionText) => {
    const input = page.locator('.doc-row').nth(rowIdx).locator('.cell-input')
    await input.click()
    await input.fill(query)
    await page.locator('.ac-item', { hasText: optionText }).first().click()
  }

  // row 0: search «Автомат» → select → pick instance AK-1
  await pick(0, 'Автом', `Автомат ${ts}`)
  const sel0 = page.locator('.doc-row').nth(0).locator('select.row-qty')
  await expect(sel0).toBeVisible()
  await sel0.selectOption({ label: `AK-1-${ts}` })

  // row 1: same serial card → instance dropdown must EXCLUDE AK-1 (only AK-2 left)
  await page.locator('.btn-addrow', { hasText: 'Додати позицію' }).click()
  await pick(1, 'Автом', `Автомат ${ts}`)
  const sel1 = page.locator('.doc-row').nth(1).locator('select.row-qty')
  await expect(sel1.locator('option', { hasText: `AK-2-${ts}` })).toHaveCount(1)
  await expect(sel1.locator('option', { hasText: `AK-1-${ts}` })).toHaveCount(0)

  // row 2: non-serial «Каска»; row 3: same card again → error, no duplicate
  await page.locator('.btn-addrow', { hasText: 'Додати позицію' }).click()
  await pick(2, 'Каск', `Каска ${ts}`)
  await page.locator('.btn-addrow', { hasText: 'Додати позицію' }).click()
  await pick(3, 'Каск', `Каска ${ts}`)
  await expect(page.locator('.modal .err')).toContainText('вже додано')

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
