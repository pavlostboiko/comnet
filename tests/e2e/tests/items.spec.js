const { test, expect } = require('@playwright/test')

const URL = 'http://frontend'
const USER = process.env.TEST_USER || 'admin'
const PASS = process.env.TEST_PASS || 'admin123'

async function login(page) {
  await page.goto(`${URL}/login`)
  await page.fill('input[type="text"], input[name="username"]', USER)
  await page.fill('input[type="password"]', PASS)
  await page.click('button[type="submit"]')
  await page.waitForURL(/\/items/)
}

test('items page loads', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/items`)
  await expect(page.locator('h2')).toContainText('Майно')
  // table or empty state visible
  const table = page.locator('.data-table, .empty-state')
  await expect(table.first()).toBeVisible()
})

test('can search items', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/items`)
  const searchInput = page.locator('input[placeholder*="Пошук"], input[type="search"]')
  if (await searchInput.count() > 0) {
    await searchInput.fill('test')
    await page.waitForTimeout(400) // debounce
  }
  // page should not crash
  await expect(page.locator('.topbar')).toBeVisible()
})
