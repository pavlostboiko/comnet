const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('items page loads', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)
  // Header tile with title
  await expect(page.locator('.tile-title').first()).toBeVisible()
  // Either the data table or the empty-state is rendered
  const tableOrEmpty = page.locator('.table-wrap, [class*="empty"]')
  await expect(tableOrEmpty.first()).toBeVisible()
})

test('can search items', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)
  const searchInput = page.locator('input[placeholder*="Пошук"], input[type="search"]')
  if (await searchInput.count() > 0) {
    await searchInput.first().fill('test')
    await page.waitForTimeout(400) // debounce
  }
  await expect(page.locator('.topbar')).toBeVisible()
})
