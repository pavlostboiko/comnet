const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('clicking a Майно row opens the «Де знаходиться» modal', async ({ page }) => {
  await uiLogin(page)
  const ts = Date.now()
  const svc = `WSvc ${ts}`
  const name = `Ноутбук ${ts}`

  // service
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Служби' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(svc)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: svc })).toBeVisible()

  // nomenclature via Майно
  await page.goto(`${URL}/catalog`)
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()
  await page.locator('.modal input.fi').nth(0).fill(name)
  await page.locator('.modal select').first().selectOption({ label: svc })
  await page.locator('.btn-pri', { hasText: 'Зберегти' }).click()

  // click the row → «Де знаходиться» modal opens
  await page.locator('tbody tr.click-row', { hasText: name }).first().click()
  await expect(page.locator('.modal-title', { hasText: 'Де знаходиться' })).toBeVisible()
  await expect(page.locator('.modal-title')).toContainText(name)
})
