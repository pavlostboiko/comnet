const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

// Issue-to-person loop through the UI: seed a unit warehouse with 10 (via API),
// then issue 3 to a person and verify «Видане»/«На складі» split — custody
// balance (10) is unchanged, issuance only records who holds what.
test('issue non-serial to a person; custody balance unchanged', async ({ page, request }) => {
  const ts = Date.now()
  const svcName = `AsgSvc ${ts}`
  const unitName = `AsgРота ${ts}`
  const nomName = `Бушлат ${ts}`
  const soldier = `Боєць${ts}`

  // Seed dictionaries + stock via API; the issuance is exercised in the UI
  const api = await loginApi(request)
  const svc = await api.post('/api/settings/services', { data: { name: svcName } }).then(r => r.json())
  const unit = await api.post('/api/structure/units', { data: { name: unitName } }).then(r => r.json())
  const nom = await api.post('/api/nomenclature', { data: {
    name: nomName, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  await api.post('/api/settings/persons', { data: { last_name: soldier, unit_id: unit.id } })
  const unitWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === unit.id)
  await api.post('/api/custody/movements', { data: {
    type: 'receipt', to_warehouse_id: unitWh.id, nomenclature_id: nom.id, quantity: 10, date: '2026-07-01' } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: `Склад ${unitName}` }).click()

  const balRow = page.locator('tbody tr', { hasText: nomName }).first()
  await expect(balRow.locator('.td-num').first()).toContainText('10')

  // Issue 3 to the soldier
  await balRow.locator('.btn-issue').click()
  await page.locator('.modal select').first().selectOption({ label: soldier })
  await page.locator('.modal input[type="number"]').fill('3')
  await page.locator('.btn-pri', { hasText: 'Видати' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)

  // «Видане» shows the soldier with 3
  await page.locator('.f-chip', { hasText: 'Видане' }).click()
  const issuedRow = page.locator('tbody tr', { hasText: soldier }).first()
  await expect(issuedRow).toBeVisible()
  await expect(issuedRow).toContainText('3')
  // «На складі» shows the remaining 7 (custody 10 unchanged, split by location)
  await page.locator('.f-chip', { hasText: 'На складі' }).click()
  const stockRow = page.locator('tbody tr', { hasText: nomName }).first()
  await expect(stockRow.locator('.td-num').first()).toContainText('7')
})
