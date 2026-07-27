/**
 * UI smoke: a draft document form has a «+ додати позицію» button that opens a
 * picker of undocumented movements of the same direction; adding one and saving
 * yields a second position row.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

const S = 'ADDUI'

test('draft form: «+ додати позицію» adds an undocumented same-direction move', async ({ page, request }) => {
  const api = await loginApi(request)
  const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  const mkUnit = async (n) => {
    const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    return whs.find(w => w.unit_id === u.id)
  }
  const A = await mkUnit('A'), B = await mkUnit('B')
  const mv = (data) => api.post('/api/custody/movements', { data }).then(r => r.json())
  await mv({ type: 'receipt', to_warehouse_id: A.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' })
  const t1 = await mv({ type: 'transfer', from_warehouse_id: A.id, to_warehouse_id: B.id, nomenclature_id: nom.id, quantity: 2, date: '2026-07-02' })
  await mv({ type: 'transfer', from_warehouse_id: A.id, to_warehouse_id: B.id, nomenclature_id: nom.id, quantity: 1, date: '2026-07-03' })
  const doc = await api.post('/api/custody/documents', { data: {
    operation: 'transfer', form: 'накладна', movement_ids: [t1.id] } }).then(r => r.json())
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/docs/${doc.id}`)

  const posRows = page.locator('.tile', { has: page.locator('.tile-title:has-text("Позиції")') }).locator('tbody tr')
  await expect(posRows).toHaveCount(1)

  await page.click('button:has-text("+ додати позицію")')
  await page.locator('.modal tbody tr').first().locator('input[type=checkbox]').check()
  await page.click('.modal-foot button:has-text("Додати")')
  await expect(posRows).toHaveCount(2)

  await page.click('button:has-text("Зберегти")')
  // Persisted: reload keeps two positions
  await page.reload()
  await expect(posRows).toHaveCount(2)
})
