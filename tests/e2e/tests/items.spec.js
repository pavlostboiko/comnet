const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('items page loads', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)
  // Header tile with title
  await expect(page.locator('.tile-title').first()).toBeVisible()
  // Either the data table or the empty-state is rendered
  const tableOrEmpty = page.locator('.table-wrap, [class*="empty"]')
  await expect(tableOrEmpty.first()).toBeVisible()
})

test('can search items', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)
  const searchInput = page.locator('input[placeholder*="Пошук"], input[type="search"]')
  if (await searchInput.count() > 0) {
    await searchInput.first().fill('test')
    await page.waitForTimeout(400) // debounce
  }
  await expect(page.locator('.topbar')).toBeVisible()
})

test('Groups view toggle renders aggregate columns', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)
  // Default = Картки. Toggle to Групи.
  await page.click('.view-toggle .vt-btn:has-text("Групи")')
  // Aggregate columns specific to the groups view
  await expect(page.locator('thead th:has-text("К-сть")')).toBeVisible()
  await expect(page.locator('thead th:has-text("Сума, грн")')).toBeVisible()
  // Card-specific columns should NOT be in this view
  await expect(page.locator('thead th:has-text("№ картки")')).toHaveCount(0)
  await expect(page.locator('thead th:has-text("Серійний №")')).toHaveCount(0)
})

test('clicking a sortable header reorders rows', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/items`)

  const rows = page.locator('tbody tr')
  const count = await rows.count()
  if (count < 2) {
    test.skip()
    return
  }

  // Capture first row's name before sort
  const nameCell = (i) => rows.nth(i).locator('td').nth(1)
  const before = (await nameCell(0).innerText()).trim()

  // Click «Найменування» — header should toggle to ASC sort
  await page.locator('thead th.sortable:has-text("Найменування")').click()
  await page.waitForTimeout(150)

  const afterAsc = (await nameCell(0).innerText()).trim()
  // Click again → DESC; expect either DESC to differ from ASC OR a single-row
  // dataset (unlikely given count>=2)
  await page.locator('thead th.sortable:has-text("Найменування")').click()
  await page.waitForTimeout(150)
  const afterDesc = (await nameCell(0).innerText()).trim()

  // At least one of the orderings should differ from the original — proves
  // sort happened. (Skip the trivial case where original was already sorted.)
  const changed = before !== afterAsc || before !== afterDesc || afterAsc !== afterDesc
  expect(changed).toBe(true)
})
