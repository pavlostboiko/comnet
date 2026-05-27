const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('documents page loads', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)
  await expect(page.locator('.tile-title').first()).toContainText('Документи')
})

test('create Надходження — Накладна document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження — Накладна (вимога)")')

  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.type-badge')).toContainText('Надходження')
  // For Надходження + Накладна: «Звідки» must be a free-text INPUT, not a select
  const fromInput = page.locator('.party-head:has-text("Звідки")').locator('..').locator('input.party-select')
  await expect(fromInput).toBeVisible()
})

test('create Надходження — Акт document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження — Акт прийому-передачі")')

  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.type-badge')).toContainText('Надходження')
  // Акт form: no «Сторони» 3-col block, no XLSX button
  await expect(page.locator('.party-head:has-text("Звідки")')).toHaveCount(0)
  await expect(page.locator('button:has-text("XLSX")')).toHaveCount(0)
})

test('create Переміщення — Накладна document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Переміщення — Накладна (вимога)")')

  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.type-badge')).toContainText('Переміщення')
  // For Переміщення: «Звідки» is a SELECT (subdivision picker)
  const fromSelect = page.locator('.party-head:has-text("Звідки")').locator('..').locator('select.party-select')
  await expect(fromSelect).toBeVisible()
})

test('type-switch dropdown reshapes draft form between накладна↔акт', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  // Start with Переміщення — Накладна; form shows the «Сторони» tile
  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Переміщення — Накладна (вимога)")')
  await page.waitForURL(/\/documents\/\d+/)
  await expect(page.locator('.party-head:has-text("Звідки")')).toBeVisible()

  // Switch via the on-form dropdown to Надходження — Акт
  await page.locator('.type-switch-select').selectOption({ label: 'Надходження — Акт прийому-передачі' })
  // Сторони tile disappears; «Реквізити акту» tile-title appears instead
  await expect(page.locator('.party-head:has-text("Звідки")')).toHaveCount(0)
  await expect(page.locator('.tile-title:has-text("Реквізити акту")')).toBeVisible()
  // XLSX button is hidden for акт
  await expect(page.locator('button:has-text("XLSX")')).toHaveCount(0)

  // Switch back to накладна — Сторони returns
  await page.locator('.type-switch-select').selectOption({ label: 'Переміщення — Накладна (вимога)' })
  await expect(page.locator('.party-head:has-text("Звідки")')).toBeVisible()
})

test('delete draft document', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/documents`)

  await page.click('button:has-text("Новий документ")')
  await page.click('.dropdown-item:has-text("Надходження — Акт прийому-передачі")')
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
