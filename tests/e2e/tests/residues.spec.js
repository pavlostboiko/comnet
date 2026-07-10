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

test('opening a unit detail exposes an «Історія» button per row', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/residues`)

  const rows = page.locator('tbody .click-row')
  if (await rows.count() === 0) {
    test.skip()
    return
  }

  // Open the first unit's detail
  await rows.first().click()
  await page.waitForSelector('.detail-title')

  // Wait for either the search row (data present) or empty state
  const anyRow = page.locator('tbody tr').filter({ hasNot: page.locator('.empty') })
  const rowCount = await anyRow.count()
  if (rowCount === 0) {
    test.skip()
    return
  }

  // At least one row has an Історія button (rows tied to a known item_id)
  const histButtons = page.locator('.btn-hist')
  expect(await histButtons.count()).toBeGreaterThan(0)

  // Clicking opens the history modal
  await histButtons.first().click()
  await expect(page.locator('.modal-title')).toBeVisible()
  await expect(page.locator('.modal-title')).toContainText('Історія')

  // Close via × button
  await page.locator('.modal-close').click()
  await expect(page.locator('.modal-title')).toHaveCount(0)
})

test('opening a unit detail exposes a «Видати» button per row that opens the issue modal', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/residues`)

  const rows = page.locator('tbody .click-row')
  if (await rows.count() === 0) {
    test.skip()
    return
  }

  await rows.first().click()
  await page.waitForSelector('.detail-title')

  const issueButtons = page.locator('.btn-issue')
  if (await issueButtons.count() === 0) {
    test.skip()
    return
  }

  await issueButtons.first().click()
  await expect(page.locator('.modal-title').filter({ hasText: 'Видати' })).toBeVisible()
  // «Кому» field is present with recipient autocomplete
  await expect(page.locator('.rc-input').first()).toBeVisible()
  // Submit button disabled until a recipient is selected
  await expect(page.locator('.btn-primary')).toBeDisabled()
  await page.locator('.modal-close').click()
})
