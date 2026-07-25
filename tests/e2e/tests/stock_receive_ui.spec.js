const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// Seeds a service warehouse via API, then opens the «Прийняти майно» modal in the
// UI and checks its key fields render (form, counterparty, add-position).
test('Stock «Прийняти майно» modal opens with receipt fields', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const tag = `RecvUi ${Date.now()}`
  const svc = await api.post('/api/settings/services', { data: { name: tag } }).then(r => r.json())
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-select').selectOption({ label: svcWh.name })
  await page.locator('button', { hasText: 'Прийняти майно' }).click()
  await expect(page.locator('.modal-title', { hasText: 'Прийняти майно' })).toBeVisible()
  await expect(page.locator('.modal input[placeholder*="контрагент"], .modal input[placeholder*="постачальник"]')).toBeVisible()
  await expect(page.locator('.modal .btn-addrow', { hasText: 'Додати позицію' })).toBeVisible()

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
