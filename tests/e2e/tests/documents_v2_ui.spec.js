const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Документи page has both tabs and switches to «Без документа»', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/docs`)
  await expect(page.locator('.tile-title')).toContainText('Документи')
  await expect(page.locator('.tabs button', { hasText: 'Накладні / акти' })).toBeVisible()
  const freeTab = page.locator('.tabs button', { hasText: 'Без документа' })
  await expect(freeTab).toBeVisible()
  await freeTab.click()
  await expect(freeTab).toHaveClass(/on/)
})
