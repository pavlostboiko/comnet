const path = require('path')
const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Import page: catalog upload shows a result summary', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/import`)
  await expect(page.locator('.tile-title')).toContainText('Імпорт')
  await expect(page.locator('.block-title', { hasText: '1. Каталог' })).toBeVisible()
  await expect(page.locator('.block-title', { hasText: '2. Переміщення' })).toBeVisible()

  // Upload the catalog (Items) fixture via the Каталог block's file input
  const catBlock = page.locator('.block', { has: page.locator('.block-title', { hasText: '1. Каталог' }) })
  await catBlock.locator('input[type="file"]').setInputFiles(
    path.join(__dirname, 'fixtures/import_v2_ui.xlsx'))
  await catBlock.locator('.btn-pri', { hasText: 'Імпортувати каталог' }).click()

  // Result grid shows the row count (raw key «rows»)
  const rowsCell = page.locator('.res-cell', { hasText: 'rows' })
  await expect(rowsCell).toContainText('3')
})
