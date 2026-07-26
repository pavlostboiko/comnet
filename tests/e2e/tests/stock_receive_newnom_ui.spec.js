const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// «+ нова номенклатура» on receive opens the SAME card form as Майно (with a
// price field), and the created card is selected into the row.
test('receive «+ нова номенклатура» uses the shared card form (with price)', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const ts = Date.now()
  const svc = await api.post('/api/settings/services', { data: { name: `NnSvc ${ts}` } }).then(r => r.json())
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await page.locator('button', { hasText: 'Прийняти майно' }).click()
  await page.locator('.recv-row select.row-nom').first().selectOption('__new__')

  // The shared card modal opens and includes the price field
  const nm = page.locator('.overlay:has(.modal-title:has-text("Додати майно"))')
  await expect(nm).toBeVisible()
  await expect(nm.locator('.fl', { hasText: 'Вартість' })).toBeVisible()

  const name = `Новий ${ts}`
  await nm.locator('input.fi').nth(0).fill(name)                 // name
  await nm.locator('select').first().selectOption({ label: `NnSvc ${ts}` })  // service
  await nm.locator('input.fi').nth(3).fill('123')               // price
  await nm.locator('.btn-pri', { hasText: 'Зберегти' }).click()

  // Modal closed; the new card is selected in the row → non-serial qty appears
  await expect(nm).toBeHidden()
  await expect(page.locator('.recv-row').first().locator('input[type="number"]')).toBeVisible()
  // and the card now exists in the catalog with the price
  const noms = await api.get('/api/nomenclature').then(r => r.json())
  const created = noms.find(n => n.name === name)
  expect(created).toBeTruthy()
  expect(Number(created.price)).toBe(123)

  await api.delete(`/api/nomenclature/${created.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
