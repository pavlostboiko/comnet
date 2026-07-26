const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// «Прийняти майно» uses the same searchable autocomplete as transfer, listing
// the WHOLE catalog (receiving new stock — not filtered by current warehouse).
test('receive nomenclature picker is a searchable autocomplete (full catalog)', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `RsSvc ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  // a card with NO stock here — must still be findable on receive
  await j('/api/nomenclature', { name: `Каска ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: svcWh.name }).click()
  await page.locator('button', { hasText: 'Прийняти майно' }).click()

  const input = page.locator('.recv-row .cell-input').first()
  await input.click()
  await input.fill('Каска')
  await page.locator('.ac-item', { hasText: `Каска ${ts}` }).first().click()

  // non-serial card selected → qty input appears in the row
  await expect(page.locator('.recv-row').first().locator('input[type="number"]')).toBeVisible()

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
