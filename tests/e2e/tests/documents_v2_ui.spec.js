const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Документи page groups movements by накладна number', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/docs`)
  await expect(page.locator('.tile-title')).toContainText('Документи')
  await expect(page.locator('thead th', { hasText: 'Накладна №' })).toBeVisible()
  await expect(page.locator('.search-row input')).toBeVisible()
})
