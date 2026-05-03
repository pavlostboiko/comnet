const { test, expect } = require('@playwright/test')

const URL = 'http://frontend'
const USER = process.env.TEST_USER || 'admin'
const PASS = process.env.TEST_PASS || 'admin123'

test('login and logout', async ({ page }) => {
  await page.goto(`${URL}/login`)
  await page.fill('input[type="text"], input[name="username"]', USER)
  await page.fill('input[type="password"]', PASS)
  await page.click('button[type="submit"]')

  await expect(page).toHaveURL(/\/items/)
  await expect(page.locator('.topbar')).toBeVisible()

  // logout via user pill click
  await page.locator('.user-pill').click()
  await expect(page).toHaveURL(/\/login/)
})

test('redirect to login when not authenticated', async ({ page }) => {
  await page.goto(`${URL}/items`)
  await expect(page).toHaveURL(/\/login/)
})
