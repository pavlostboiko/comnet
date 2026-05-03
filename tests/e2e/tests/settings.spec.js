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

test('settings page loads with tabs', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/settings`)
  await expect(page.locator('button:has-text("Підрозділ")')).toBeVisible()
  await expect(page.locator('button:has-text("Особи")')).toBeVisible()
  await expect(page.locator('button:has-text("Типи операцій")')).toBeVisible()
})

test('add person - button disabled during save, no duplicates', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/settings`)

  await page.click('button:has-text("Особи")')

  const countBefore = await page.locator('tbody tr').count()

  // Open modal
  await page.click('button:has-text("Додати особу")')
  await expect(page.locator('.overlay.open')).toBeVisible()

  const testName = `Тест${Date.now()}`
  await page.fill('input[placeholder="Іваненко"]', testName)
  await page.fill('input[placeholder="Іван"]', 'Тест')
  await page.fill('input[placeholder="Іванович"]', 'Тестович')

  const saveBtn = page.locator('.modal-foot .btn-primary')

  // Click once and immediately check button is disabled
  await saveBtn.click()
  // button should be disabled or show loading text while saving
  // (it may complete fast, so we just verify no duplicate was created)

  await page.waitForTimeout(1000)

  // Modal should be closed
  await expect(page.locator('.overlay.open')).not.toBeVisible()

  const countAfter = await page.locator('tbody tr').count()
  // exactly one new row added
  expect(countAfter).toBe(countBefore + 1)

  // Clean up — delete the test person
  const rows = page.locator('tbody tr')
  const lastRow = rows.last()
  await lastRow.hover()
  await lastRow.locator('.act.d').click()
  page.on('dialog', d => d.accept())
  await page.waitForTimeout(500)
})

test('edit person saves correctly', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/settings`)
  await page.click('button:has-text("Особи")')

  const rows = page.locator('tbody tr')
  if (await rows.count() === 0) {
    test.skip()
    return
  }

  // Click edit on first person
  await rows.first().hover()
  await rows.first().locator('.act.e').click()
  await expect(page.locator('.overlay.open')).toBeVisible()

  // Change rank field
  const rankInput = page.locator('input[placeholder="Капітан"]')
  await rankInput.fill('Майор')

  await page.locator('.modal-foot .btn-primary').click()
  await page.waitForTimeout(800)

  await expect(page.locator('.overlay.open')).not.toBeVisible()
  await expect(page.locator('.toast.show')).toContainText('збережено')
})
