/**
 * UI smoke: on a SERVICE warehouse, the облік/НДМ filter works and an НДМ item
 * can be issued directly to a person (no unit binding).
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')


// Пікер особи в модалці «Видати» — пошуковий (ItemAutocomplete), не <select>.
async function pickPerson(page, text) {
  await page.locator('.modal .ac-field input').fill(text)
  await page.locator('.ac-dropdown .ac-item', { hasText: text }).first().click()
}

test('НДМ on service warehouse: filter + direct issue', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  const svcName = `SvcNDMUI-${S}`
  const svc = await api.post('/api/settings/services', { data: { name: svcName } }).then(r => r.json())
  const svcWh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.service_id === svc.id && w.type === 'service')
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Пальне-${S}`, service_id: svc.id, is_serialized: false, is_official: false, unit_of_measure: 'л' } }).then(r => r.json())
  const unit = await api.post('/api/structure/units', { data: { name: `U-${S}` } }).then(r => r.json())
  const soldier = `Боєць${S}`
  await api.post('/api/settings/persons', { data: { last_name: soldier, unit_id: unit.id } })
  await api.post('/api/custody/documents/receive', { data: {
    to_warehouse_id: svcWh.id, form: 'без документа', doc_date: '2026-07-10',
    items: [{ nomenclature_id: nom.id, quantity: 10 }] } })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: `Склад ${svcName}` }).click()

  // облік/НДМ filter present; select НДМ
  await page.locator('.f-chip', { hasText: 'НДМ' }).click()
  const row = page.locator('tbody tr', { hasText: `Пальне-${S}` }).first()
  await expect(row).toBeVisible()

  // Issue directly to the person (of another unit)
  await row.locator('.btn-issue').click()
  await pickPerson(page, soldier)
  await page.locator('.modal input[type="number"]').fill('3')
  await page.locator('.btn-pri', { hasText: 'Видати' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)

  // Assignment recorded on the service warehouse
  await expect(async () => {
    const asg = await api.get(`/api/assignments?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(asg).toHaveLength(1)
    expect(Number(asg[0].quantity)).toBe(3)
  }).toPass()
  await api.dispose()
})
