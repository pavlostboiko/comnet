const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

test('Users page: create an МВО user scoped to a unit warehouse', async ({ page }) => {
  await uiLogin(page)
  const ts = Date.now()
  const unit = `UsrРота ${ts}`
  const username = `mvo_${ts}`

  // Need a unit (auto-warehouse) first
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Підрозділи' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(unit)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: unit })).toBeVisible()

  // Create the МВО user
  await page.goto(`${URL}/users`)
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').nth(0).fill(username)
  await page.locator('.modal .fi').nth(1).fill('mvopass')
  await page.locator('.modal select').first().selectOption('mvo')
  await page.locator('.modal select').nth(1).selectOption({ label: unit })  // unit → warehouse auto
  await page.locator('.btn-pri', { hasText: 'Створити' }).click()

  const row = page.locator('tbody tr', { hasText: username }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText('МВО')
  await expect(row).toContainText(`Склад ${unit}`)
})

test('МВО login: no admin nav, stock opens on own warehouse', async ({ page }) => {
  // Setup: unit + mvo user (admin session)
  await uiLogin(page)
  const ts = Date.now()
  const unit = `MvoРота ${ts}`
  const username = `mvo2_${ts}`
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Підрозділи' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(unit)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: unit })).toBeVisible()

  await page.goto(`${URL}/users`)
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').nth(0).fill(username)
  await page.locator('.modal .fi').nth(1).fill('mvopass')
  await page.locator('.modal select').first().selectOption('mvo')
  await page.locator('.modal select').nth(1).selectOption({ label: unit })
  await page.locator('.btn-pri', { hasText: 'Створити' }).click()
  await expect(page.locator('tbody tr', { hasText: username })).toBeVisible()

  // Log out, log in as the МВО
  await page.locator('.user-pill').click()   // logout → /login
  await uiLogin(page, { user: username, pass: 'mvopass' })

  // No admin-only nav links; operational pages visible
  await expect(page.locator('.nav-link', { hasText: 'Довідники' })).toHaveCount(0)
  await expect(page.locator('.nav-link', { hasText: 'Користувачі' })).toHaveCount(0)
  await expect(page.locator('.nav-link', { hasText: 'Майно' })).toBeVisible()
  await expect(page.locator('.nav-link', { hasText: 'Залишки' })).toBeVisible()

  // Stock auto-opens on their warehouse (unified table visible, no «оберіть склад»)
  await page.locator('.nav-link', { hasText: 'Залишки' }).click()
  await expect(page.locator('.wh-select')).toBeVisible()
  await expect(page.locator('.empty', { hasText: 'Оберіть склад' })).toHaveCount(0)
})
