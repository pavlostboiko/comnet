/**
 * UI smoke: «+ Рух» is gone; «Додати переміщення» to a unit warehouse shows a
 * per-row person picker; picking a person issues the item on transfer.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

const S = 'TXUI'

test('transfer modal issues to a person on a unit destination; «+ Рух» removed', async ({ page, request }) => {
  const api = await loginApi(request)
  const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
  const nom = await api.post('/api/nomenclature', { data: {
    name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
  const mkUnit = async (n) => {
    const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    return { unit: u, wh: whs.find(w => w.unit_id === u.id) }
  }
  const A = await mkUnit('A'), B = await mkUnit('B')
  await api.post('/api/settings/persons', { data: { last_name: `Бійць${S}`, unit_id: B.unit.id } })
  await api.post('/api/custody/movements', { data: {
    type: 'receipt', to_warehouse_id: A.wh.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' } })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)

  // «+ Рух» is gone
  await expect(page.locator('button:has-text("+ Рух")')).toHaveCount(0)

  // Select source warehouse A, open the transfer modal
  await page.click(`.wh-btn:has-text("${A.wh.name}")`)
  await page.click('button:has-text("Додати переміщення")')

  // Choose unit destination B → person picker appears
  await page.selectOption('.doc-top select', { label: B.wh.name })
  await expect(page.locator('.row-person')).toBeVisible()

  // Nomenclature
  await page.locator('.row-nom input').fill(`Річ${S}`)
  await page.locator('.ac-dropdown .ac-item').first().click()
  await page.locator('.row-qty').fill('2')

  // Person (custom searchable picker)
  await page.locator('.row-person input').fill(`Бійць${S}`)
  await page.locator('.ac-dropdown .ac-item').first().click()

  await page.click('.modal-foot button:has-text("Провести")')

  // Assignment created on B for the person
  await expect(async () => {
    const asg = await api.get(`/api/assignments?warehouse_id=${B.wh.id}`).then(r => r.json())
    expect(asg).toHaveLength(1)
    expect(Number(asg[0].quantity)).toBe(2)
  }).toPass()
  await api.dispose()
})
