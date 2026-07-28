const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('Залишки page loads with warehouse selector', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await expect(page.locator('.tile-title')).toContainText('Залишки')
  await expect(page.locator('.wh-tabs')).toBeVisible()
  // «Додати переміщення» disabled until a warehouse is chosen
  await expect(page.locator('.btn-add')).toBeDisabled()
})

test('receipt increases the non-serial balance (Прийняти майно UI)', async ({ page, request }) => {
  const ts = Date.now()
  const svcName = `Stock Svc ${ts}`
  const nomName = `Бушлат ${ts}`

  // Seed the dictionary bits via API; the receipt itself is exercised in the UI
  const api = await loginApi(request)
  const svc = await api.post('/api/settings/services', { data: { name: svcName } }).then(r => r.json())
  await api.post('/api/nomenclature', { data: {
    name: nomName, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: `Склад ${svcName}` }).click()

  // Receipt of 7 via «Прийняти майно»
  await page.locator('button', { hasText: 'Прийняти майно' }).click()
  await page.locator('.row-nom input').fill(nomName)
  await page.locator('.ac-dropdown .ac-item').first().click()
  await page.locator('.recv-row input[type="number"]').fill('7')
  await page.locator('.modal-foot button', { hasText: 'Прийняти' }).click()

  // Balance row shows qty 7
  const row = page.locator('tbody tr', { hasText: nomName }).first()
  await expect(row).toBeVisible()
  await expect(row.locator('.td-num').first()).toContainText('7')
})
