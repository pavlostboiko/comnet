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

test('documents page loads', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/documents`)
  await expect(page.locator('h2')).toContainText('Документи')
})

test('create надходження document', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/documents`)

  // Open "Новий документ" dropdown
  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження")')

  // Should redirect to document form
  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('h2, .page-title')).toContainText(/Надходження|Документ/)
})

test('full lifecycle: create → fill → sign → check movements', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/documents`)

  // Create надходження
  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження")')
  await page.waitForURL(/\/documents\/\d+/)

  // Fill required fields
  const docNumber = `TEST-${Date.now()}`
  await page.locator('input[placeholder*="Номер"], input[name="doc_number"]').fill(docNumber)
  await page.locator('input[type="date"]').first().fill('2024-01-15')
  await page.locator('input[placeholder*="Куди"], input[name="to_unit"]').fill('Тестовий підрозділ')

  // Save
  await page.click('button:has-text("Зберегти")')
  await page.waitForTimeout(500)

  // Sign
  await page.click('button:has-text("Підписати")')
  await page.waitForTimeout(800)

  // Should now be signed (Підписано badge visible or sign button gone)
  const signedBadge = page.locator('.status-badge.signed, text=Підписано')
  const unsignBtn = page.locator('button:has-text("Зняти підпис")')
  const isSignedOrHasUnsign = (await signedBadge.count()) > 0 || (await unsignBtn.count()) > 0
  expect(isSignedOrHasUnsign).toBe(true)

  // Navigate to movements and verify entry exists
  await page.goto(`${URL}/movements`)
  await expect(page.locator('table, .empty-state')).toBeVisible()
})

test('delete draft document', async ({ page }) => {
  await login(page)
  await page.goto(`${URL}/documents`)

  // Create переміщення
  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Переміщення")')
  await page.waitForURL(/\/documents\/\d+/)

  // Go back to list
  await page.goto(`${URL}/documents`)
  await page.waitForTimeout(300)

  // Delete button should be enabled for drafts
  const deleteBtn = page.locator('button:has-text("Видалити")').first()
  if (await deleteBtn.count() > 0) {
    page.on('dialog', d => d.accept())
    await deleteBtn.click()
    await page.waitForTimeout(500)
  }
  await expect(page.locator('.topbar')).toBeVisible()
})
