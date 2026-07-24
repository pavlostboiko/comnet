const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Залишки page loads with warehouse selector', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await expect(page.locator('.tile-title')).toContainText('Залишки')
  await expect(page.locator('.wh-select')).toBeVisible()
  // «+ Рух» disabled until a warehouse is chosen
  await expect(page.locator('.btn-add')).toBeDisabled()
})

test('receipt increases the non-serial balance (full UI loop)', async ({ page }) => {
  await uiLogin(page)
  const ts = Date.now()
  const svcName = `Stock Svc ${ts}`
  const nomName = `Бушлат ${ts}`

  // Create a service (auto-warehouse) via Довідники
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Служби' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(svcName)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: svcName })).toBeVisible()

  // Create a non-serial nomenclature on the Майно page
  await page.goto(`${URL}/catalog`)
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()
  await page.locator('.modal .fi').first().fill(nomName)
  await page.locator('.modal select').first().selectOption({ label: svcName })
  await page.locator('.btn-pri', { hasText: 'Зберегти' }).click()
  await expect(page.locator('td.td-name', { hasText: nomName })).toBeVisible()

  // Go to Stock, pick the service warehouse, do a receipt of 7
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-select').selectOption({ label: `Склад ${svcName}` })
  await page.locator('.btn-add', { hasText: '+ Рух' }).click()
  await page.locator('.modal select').nth(0).selectOption('receipt')       // type
  await page.locator('.modal select').nth(1).selectOption({ label: `${nomName} (несерійне)` })
  await page.locator('.modal input[type="number"]').fill('7')
  await page.locator('.btn-pri', { hasText: 'Провести' }).click()

  // Balance row shows qty 7
  const row = page.locator('tbody tr', { hasText: nomName }).first()
  await expect(row).toBeVisible()
  await expect(row.locator('.td-num').first()).toContainText('7')
})
