/**
 * UI smoke (2c): the document form no longer has signatory person pickers —
 * «Підписанти (МВО)» are read-only with a hint that they come from the journal.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('document form: signatories are read-only (from journal), no pickers', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  const mkWh = async (n) => {
    const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
    return (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
  }
  const whA = await mkWh('A'), whB = await mkWh('B')
  await api.post('/api/custody/movements', { data: { type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' } })
  const mv = await api.post('/api/custody/movements', { data: { type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id, nomenclature_id: nom.id, quantity: 2, date: '2026-07-10' } }).then(r => r.json())
  const doc = await api.post('/api/custody/documents', { data: { operation: 'transfer', form: 'накладна', doc_number: `NK-${S}`, doc_date: '2026-07-10', movement_ids: [mv.id] } }).then(r => r.json())
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/docs/${doc.id}`)

  const tile = page.locator('.tile', { has: page.locator('.tile-title:has-text("Підписанти")') })
  await expect(tile).toBeVisible()
  await expect(tile.locator('.hint-mvo')).toContainText('журналу МВО')
  await expect(tile.locator('.ro-val')).toHaveCount(3)     // read-only signatories
  await expect(tile.locator('select')).toHaveCount(0)      // no person pickers
})
