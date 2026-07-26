const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// «Видати в підрозділ» is now «Додати переміщення» and no longer asks for a
// накладна number — the invoice is formed later on «Документи».
test('«Додати переміщення» modal: renamed, no invoice-number field', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const tag = `AddTr ${Date.now()}`
  const svc = await api.post('/api/settings/services', { data: { name: tag } }).then(r => r.json())
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-select').selectOption({ label: svcWh.name })
  await page.locator('button', { hasText: 'Додати переміщення' }).click()

  await expect(page.locator('.modal-title', { hasText: 'Додати переміщення' })).toBeVisible()
  await expect(page.locator('.modal .fl', { hasText: '№ накладної' })).toHaveCount(0)
  await expect(page.locator('.modal .doc-hint')).toContainText('Без документа')

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
