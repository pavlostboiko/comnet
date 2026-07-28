/**
 * UI smoke: non-serial rows on «Залишки» have an «Історія» button too, and the
 * timeline shows the issuance (видано) — same as serial.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('non-serial item has history with issuance on «Залишки»', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
  const unit = await api.post('/api/structure/units', { data: { name: `U${S}` } }).then(r => r.json())
  const unitWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === unit.id)
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Бушлат${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  const soldier = `Боєць${S}`
  const person = await api.post('/api/settings/persons', { data: { last_name: soldier, unit_id: unit.id } }).then(r => r.json())
  await api.post('/api/custody/movements', { data: {
    type: 'receipt', to_warehouse_id: unitWh.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-10' } })
  await api.post('/api/assignments', { data: {
    warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 2 } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: `Склад ${unit.name}` }).click()

  // Non-serial row has «Історія»
  const row = page.locator('tbody tr', { hasText: `Бушлат${S}` }).first()
  await row.locator('.btn-hist').click()

  // Timeline shows the issuance (видано)
  await expect(page.locator('.modal-title')).toContainText('Історія')
  await expect(page.locator('.h-table .chip', { hasText: 'видано' })).toBeVisible()
})
