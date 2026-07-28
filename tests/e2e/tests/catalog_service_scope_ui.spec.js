/**
 * UI smoke: a service-role user on «Майно» sees NO services dropdown and only
 * their own service's items.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('service user: no services dropdown, only own-service items on «Майно»', async ({ page, request }) => {
  const admin = await loginApi(request)
  const S = Date.now()
  const svcX = await admin.post('/api/settings/services', { data: { name: `SvcUIX-${S}` } }).then(r => r.json())
  const svcY = await admin.post('/api/settings/services', { data: { name: `SvcUIY-${S}` } }).then(r => r.json())
  await admin.post('/api/nomenclature', { data: { name: `Своя-${S}`, service_id: svcX.id, is_serialized: false, unit_of_measure: 'шт' } })
  await admin.post('/api/nomenclature', { data: { name: `Чужа-${S}`, service_id: svcY.id, is_serialized: false, unit_of_measure: 'шт' } })
  const username = `svcui-${S}`
  await admin.post('/api/users', { data: { username, password: 'test1234', role: 'service', service_id: svcX.id } })
  await admin.dispose()

  await uiLogin(page, { user: username, pass: 'test1234' })
  await page.goto(`${URL}/catalog`)
  await expect(page.locator('.tile-title')).toContainText('Майно')

  // No services dropdown for a service user
  await expect(page.locator('.sel')).toHaveCount(0)
  // Sees own item, not the other service's
  await expect(page.locator('tbody tr', { hasText: `Своя-${S}` })).toBeVisible()
  await expect(page.locator('tbody tr', { hasText: `Чужа-${S}` })).toHaveCount(0)
})
