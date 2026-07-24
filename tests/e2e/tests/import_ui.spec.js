const path = require('path')
const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Import page uploads a file and shows a result summary', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/import`)
  await expect(page.locator('.tile-title')).toContainText('Імпорт')

  await page.locator('input[type="file"]').setInputFiles(
    path.join(__dirname, 'fixtures/import_v2_items.xlsx'))
  await page.locator('.btn-pri', { hasText: 'Імпортувати' }).click()

  // Result grid appears with a row count
  await expect(page.locator('.res-title', { hasText: 'Готово' })).toBeVisible()
  await expect(page.locator('.res-cell', { hasText: 'Рядків' })).toContainText('3')
})
