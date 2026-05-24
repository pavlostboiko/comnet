const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('documents page loads', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)
  await expect(page.locator('.tile-title').first()).toContainText('Документи')
})

test('create надходження document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження")')

  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.type-badge')).toContainText('Надходження')
})

test('create переміщення (накладна_25) document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  // After the 878a6b5 rename, dropdown only has «Надходження» and «Переміщення»
  // («Переміщення» → внутрішньо doc_type=накладна_25 з повною формою)
  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Переміщення")')

  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.type-badge')).toContainText('Переміщення')
  // The нaкладна form has the «Сторони» 3-column block
  await expect(page.locator('.party-head:has-text("Звідки")')).toBeVisible()
})

test('delete draft document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження")')
  await page.waitForURL(/\/documents\/\d+/)

  await page.goto(`${URL}/documents`)
  await page.waitForTimeout(300)

  // Count drafts before; delete one; count should drop by 1
  const draftRows = page.locator('tbody tr', { hasText: 'Чернетка' })
  const beforeCount = await draftRows.count()
  expect(beforeCount).toBeGreaterThanOrEqual(1)

  // Find a draft row whose delete button is enabled (drafts are deletable)
  const draftRow = draftRows.first()
  await draftRow.hover()
  page.on('dialog', d => d.accept())
  await draftRow.locator('button[title="Видалити"]:not([disabled])').click()
  await page.waitForTimeout(700)

  await expect(draftRows).toHaveCount(beforeCount - 1)
})
