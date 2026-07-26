const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// Залишки has a search field (like Майно): filters the current warehouse's rows
// by name/serial, and «/» focuses it.
test('Залишки search filters rows and «/» focuses it', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())

  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `SSvc ${ts}` })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const alpha = await j('/api/nomenclature', { name: `Alpha ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  const beta = await j('/api/nomenclature', { name: `Beta ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: alpha.id, to_warehouse_id: svcWh.id, quantity: 3 })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: beta.id, to_warehouse_id: svcWh.id, quantity: 4 })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-select').selectOption({ label: svcWh.name })

  // both rows visible initially
  await expect(page.locator('tbody tr', { hasText: `Alpha ${ts}` })).toBeVisible()
  await expect(page.locator('tbody tr', { hasText: `Beta ${ts}` })).toBeVisible()

  // «/» focuses the search input, then typing filters
  await page.locator('body').click()
  await page.keyboard.press('/')
  await expect(page.locator('.search-row input')).toBeFocused()
  await page.keyboard.type(`Alpha ${ts}`)
  await expect(page.locator('tbody tr', { hasText: `Alpha ${ts}` })).toBeVisible()
  await expect(page.locator('tbody tr', { hasText: `Beta ${ts}` })).toHaveCount(0)

  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
