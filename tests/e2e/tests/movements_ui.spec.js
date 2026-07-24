const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Переміщення page loads with a warehouse filter and log table', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/custody`)
  await expect(page.locator('.tile-title')).toContainText('Переміщення')
  await expect(page.locator('.wh-select')).toBeVisible()
  // The log table header is present
  await expect(page.locator('thead th', { hasText: 'Звідки → Куди' })).toBeVisible()
})
