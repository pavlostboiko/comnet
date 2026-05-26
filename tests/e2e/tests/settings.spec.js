const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('settings page loads with tabs', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/settings`)
  await expect(page.locator('button:has-text("Підрозділ")')).toBeVisible()
  await expect(page.locator('button:has-text("Особи")')).toBeVisible()
  await expect(page.locator('button:has-text("Типи операцій")')).toBeVisible()
  await expect(page.locator('button:has-text("Служби")')).toBeVisible()
})

test('Users tab visible to admin and lists rows', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/settings`)
  // Tab is admin-only — visible because the default seed user is admin
  const tab = page.locator('button.tt-btn:has-text("Користувачі")')
  await expect(tab).toBeVisible()
  await tab.click()
  // The bootstrapped admin user appears at minimum
  await expect(page.locator('tbody tr', { hasText: 'admin' }).first()).toBeVisible()
  // «Додати користувача» button is in the actions area
  await expect(page.locator('button:has-text("Додати користувача")')).toBeVisible()
})

test('add person — modal closes; exactly one row added', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/settings`)
  await page.click('button:has-text("Особи")')

  const countBefore = await page.locator('tbody tr').count()

  await page.click('button:has-text("Додати особу")')
  await expect(page.locator('.overlay.open')).toBeVisible()

  const tag = `Тест${Date.now()}`
  await page.fill('input[placeholder="Іваненко"]', tag)
  await page.fill('input[placeholder="Іван"]', 'Тест')
  await page.fill('input[placeholder="Іванович"]', 'Тестович')

  await page.locator('.overlay.open .modal-foot .btn-primary').click()
  await page.waitForTimeout(800)

  await expect(page.locator('.overlay.open')).not.toBeVisible()
  expect(await page.locator('tbody tr').count()).toBe(countBefore + 1)

  // Cleanup
  const row = page.locator('tbody tr', { hasText: tag }).first()
  await row.hover()
  page.on('dialog', d => d.accept())
  await row.locator('.act.d').click()
  await page.waitForTimeout(500)
})

test('edit person saves correctly', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/settings`)
  await page.click('button:has-text("Особи")')

  const rows = page.locator('tbody tr')
  if ((await rows.count()) === 0) {
    test.skip()
    return
  }

  await rows.first().hover()
  await rows.first().locator('.act.e').click({ force: true })
  await expect(page.locator('.overlay.open')).toBeVisible()

  const rankInput = page.locator('input[placeholder="Капітан"]')
  await rankInput.fill('Майор')

  await page.locator('.overlay.open .modal-foot .btn-primary').click()
  await page.waitForTimeout(800)

  await expect(page.locator('.overlay.open')).not.toBeVisible()
  await expect(page.locator('.toast.show')).toContainText('збережено')
})
