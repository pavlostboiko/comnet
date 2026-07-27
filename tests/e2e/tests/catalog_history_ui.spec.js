const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// Seeds an item, opens its «Де знаходиться» modal in the catalog, and switches
// to the «Історія» tab.
test('catalog item modal has «Історія» tab', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const tag = `HistUi ${Date.now()}`
  const svc = await api.post('/api/settings/services', { data: { name: tag } }).then(r => r.json())
  await api.post('/api/nomenclature', { data: { name: `Річ ${tag}`, service_id: svc.id, unit_of_measure: 'шт' } })

  await uiLogin(page)
  await page.goto(`${URL}/catalog`)
  await page.locator('td.td-name', { hasText: `Річ ${tag}` }).click()
  await expect(page.locator('.wtabs button', { hasText: 'Де знаходиться' })).toBeVisible()
  await page.locator('.wtabs button', { hasText: 'Історія' }).click()
  await expect(page.locator('.modal th', { hasText: 'Подія' })).toBeVisible()

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
