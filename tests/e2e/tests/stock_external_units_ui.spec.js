const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// External units are excluded from the Залишки warehouse buttons, and appear as
// the source in «Прийняти майно → від кого».
test('external units: hidden from stock buttons, shown as receipt source', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())

  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `ExSvc ${ts}` })
  const intUnit = await j('/api/structure/units', { name: `Внутр ${ts}` })
  const extUnit = await j('/api/structure/units', { name: `Зовн ${ts}`, is_external: true })

  await uiLogin(page)
  await page.goto(`${URL}/stock`)

  // internal unit's warehouse button is shown; external one is not
  await expect(page.locator('.wh-btn', { hasText: `Склад Внутр ${ts}` })).toHaveCount(1)
  await expect(page.locator('.wh-btn', { hasText: `Склад Зовн ${ts}` })).toHaveCount(0)

  // «Прийняти майно → від кого» lists the external unit
  await page.locator('.wh-btn', { hasText: `Склад ExSvc ${ts}` }).click()
  await page.locator('button', { hasText: 'Прийняти майно' }).click()
  const fromSel = page.locator('.modal select').filter({ has: page.locator('option', { hasText: `Зовн ${ts}` }) })
  await expect(fromSel).toHaveCount(1)

  await api.delete(`/api/structure/units/${intUnit.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${extUnit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})
