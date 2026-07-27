const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Майно is the landing page and lists nomenclature', async ({ page }) => {
  await uiLogin(page)
  // login lands on /catalog
  await expect(page).toHaveURL(/\/catalog/)
  await expect(page.locator('.tile-title')).toContainText('Майно')
  await expect(page.locator('.sel')).toBeVisible()          // service selector
  await expect(page.locator('.search-row input')).toBeVisible()
})

test('add nomenclature with a category, then filter by service + search', async ({ page }) => {
  await uiLogin(page)
  const ts = Date.now()
  const svc = `CatSvc ${ts}`
  const name = `Рація ${ts}`
  const cat = `Зв'язок ${ts}`

  // Need a service (Довідники → Служби)
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Служби' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(svc)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: svc })).toBeVisible()

  // Add nomenclature on the Майно page
  await page.goto(`${URL}/catalog`)
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()
  await page.locator('.modal input.fi').nth(0).fill(name)                   // name (inputs only)
  await page.locator('.modal select').first().selectOption({ label: svc })  // service
  await page.locator('.modal input.fi').nth(1).fill(cat)                    // category
  await page.locator('.btn-pri', { hasText: 'Зберегти' }).click()

  // Filter to the service; the item and its category are shown
  await page.locator('.tile-header .sel').selectOption({ label: svc })
  const row = page.locator('tbody tr', { hasText: name }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText(cat)

  // Search narrows it
  await page.locator('.search-row input').fill('zzz-none')
  await expect(page.locator('tbody .empty')).toBeVisible()
})
