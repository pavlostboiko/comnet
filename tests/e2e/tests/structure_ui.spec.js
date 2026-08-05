const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('Довідники page loads with all tabs', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await expect(page.locator('.tile-title')).toContainText('Довідники')
  for (const label of ['Служби', 'Підрозділи', 'Склади', 'Підписанти', 'Групи', 'Особи', 'Типи операцій', 'Реквізити']) {
    await expect(page.locator('.tt-btn', { hasText: label })).toBeVisible()
  }
})

test('op-types tab (migrated from /settings): create a type', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/structure`)

  await page.locator('.tt-btn', { hasText: 'Типи операцій' }).click()
  await page.locator('.btn-add').click()
  const name = `UI Операція ${Date.now()}`
  await page.locator('.modal .fi').first().fill(name)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: name })).toBeVisible()
})

test('requisites tab (migrated from /settings): save unit details persist', async ({ page }) => {
  await uiLogin(page)
  await page.goto(`${URL}/structure`)

  await page.locator('.tt-btn', { hasText: 'Реквізити' }).click()
  const edrpou = `${Date.now()}`.slice(-8)
  // Requisites form order: name, short_name, edrpou, location.
  // Спершу дочекатись, поки форма підтягне збережені значення — інакше введене
  // перетирається відповіддю, що прийшла після заповнення.
  await expect(page.locator('.req-form .fi').first()).toBeVisible()
  await page.waitForLoadState('networkidle')
  await page.locator('.req-form .fi').nth(2).fill(edrpou)
  await page.locator('.req-form .btn-pri').click()
  await expect(page.locator('.req-ok')).toBeVisible()

  await page.reload()
  await page.locator('.tt-btn', { hasText: 'Реквізити' }).click()
  await expect(page.locator('.req-form .fi').nth(2)).toHaveValue(edrpou)
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

test('creating a group via the Групи tab', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  await api.post('/api/settings/persons', {
    data: { last_name: `Комгр${S}`, first_name: 'Петро', callsign: `Тур${S}` } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/structure`)

  // Need a unit first
  await page.locator('.tt-btn', { hasText: 'Підрозділи' }).click()
  await page.locator('.btn-add').click()
  const unitName = `UI Гр-рота ${Date.now()}`
  await page.locator('.modal .fi').first().fill(unitName)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: unitName })).toBeVisible()

  // Create a group in it
  await page.locator('.tt-btn', { hasText: 'Групи' }).click()
  await page.locator('.btn-add').click()
  const groupName = `Група ${Date.now()}`
  await page.locator('.modal .fi').first().fill(groupName)
  // select the unit (second .fi is the unit <select>)
  await page.locator('.modal select').first().selectOption({ label: unitName })
  // командир — пошуковий пікер: шукаємо за позивним, підпис із ПІБ+позивним
  await page.locator('.modal .ac-field input').fill(`Тур${S}`)
  await page.locator('.ac-dropdown .ac-item', { hasText: `Комгр${S} Петро (Тур${S})` }).first().click()
  await page.locator('.btn-pri').click()
  const row = page.locator('tbody tr', { hasText: groupName }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText(`Комгр${S}`)
})

// Позивний видно в списку Особи окремою колонкою (у ПІБ він показувався лише
// тоді, коли прізвища/імені немає взагалі).
test('persons tab shows the callsign of a named person', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  await api.post('/api/settings/persons', {
    data: { last_name: `Позивний${S}`, first_name: 'Іван', callsign: `Сокіл${S}` } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Особи' }).click()
  const row = page.locator('tbody tr', { hasText: `Позивний${S}` }).first()
  await expect(row).toContainText(`Сокіл${S}`)
})
