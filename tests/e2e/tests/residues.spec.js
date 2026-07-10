const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('residues page renders both tabs with a search row', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/residues`)

  // Master view for the default tab «По підрозділах» has a search input
  const unitSearch = page.locator('.search-row input').first()
  await expect(unitSearch).toBeVisible()

  // Switch to «По особах» — a search input is present there too
  await page.click('.tt-btn:has-text("По особах")')
  await expect(page.locator('.search-row input').first()).toBeVisible()
})

test('search on master «По підрозділах» filters rows to a subset', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/residues`)

  const rowsBefore = await page.locator('tbody tr:not(.empty)').count()
  if (rowsBefore < 2) {
    test.skip()
    return
  }

  // Extract a substring from the first row's «Підрозділ» cell to ensure a match
  const firstUnit = (await page.locator('tbody .td-unit-name').first().innerText()).trim()
  const needle = firstUnit.slice(0, Math.min(3, firstUnit.length))

  await page.locator('.search-row input').first().fill(needle)
  await page.waitForTimeout(200)

  const rowsAfter = await page.locator('tbody tr').count()
  // The row we sampled from must still be present
  await expect(page.locator('tbody .td-unit-name').filter({ hasText: firstUnit }).first()).toBeVisible()

  // Impossible needle → empty result state shows
  await page.locator('.search-row input').first().fill('zzz_never_matches_xyz')
  await page.waitForTimeout(200)
  await expect(page.locator('tbody .empty').filter({ hasText: /не знайдено/i })).toBeVisible()

  // Clearing via the × button restores original count
  await page.locator('.search-clear').first().click()
  await page.waitForTimeout(200)
  const rowsRestored = await page.locator('tbody tr:not(.empty)').count()
  expect(rowsRestored).toBe(rowsBefore)
})

test('«/» hotkey focuses the visible search input', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/residues`)
  await page.waitForSelector('.search-row input')

  // Body has focus initially; pressing «/» should redirect it into the search
  await page.locator('body').click()
  await page.keyboard.press('/')
  await expect(page.locator('.search-row input').first()).toBeFocused()
})
