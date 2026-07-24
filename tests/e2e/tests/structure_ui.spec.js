const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Довідники v2 page loads with all tabs', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await expect(page.locator('.tile-title')).toContainText('Довідники v2')
  for (const label of ['Служби', 'Підрозділи', 'Номенклатура', 'Склади']) {
    await expect(page.locator('.tt-btn', { hasText: label })).toBeVisible()
  }
})

test('creating a unit shows an auto-created warehouse in the Склади tab', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/structure`)

  // Switch to Підрозділи, add one
  await page.locator('.tt-btn', { hasText: 'Підрозділи' }).click()
  await page.locator('.btn-add').click()
  const name = `UI Рота ${Date.now()}`
  await page.locator('.modal .fi').first().fill(name)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: name })).toBeVisible()

  // Its warehouse appears under Склади
  await page.locator('.tt-btn', { hasText: 'Склади' }).click()
  await expect(page.locator('td.td-name', { hasText: `Склад ${name}` })).toBeVisible()
})
