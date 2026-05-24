const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('login and logout', async ({ page }) => {
  await uiLogin(page)
  await expect(page.locator('.topbar')).toBeVisible()

  // logout via user pill click
  await page.locator('.user-pill').click()
  await expect(page).toHaveURL(/\/login/)
})

test('redirect to login when not authenticated', async ({ page }) => {
  await page.goto(`${URL}/items`)
  await expect(page).toHaveURL(/\/login/)
})
