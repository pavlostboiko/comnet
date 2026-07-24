const { test, expect } = require('@playwright/test')
const { URL, uiLogin } = require('./helpers/login')

// Full issuance loop through the UI: setup dictionaries → stock into a unit
// warehouse → issue to a person → verify «Видано особам» and that the custody
// balance is unchanged (issuance does not move custody).
test('issue non-serial to a person; custody balance unchanged', async ({ page }) => {
  test.slow()
  await uiLogin(page)
  const ts = Date.now()
  const svc = `AsgSvc ${ts}`
  const unit = `AsgРота ${ts}`
  const nom = `Бушлат ${ts}`
  const soldier = `Боєць${ts}`

  // ── Довідники ──
  await page.goto(`${URL}/structure`)
  // service
  await page.locator('.tt-btn', { hasText: 'Служби' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(svc)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: svc })).toBeVisible()
  // unit
  await page.locator('.tt-btn', { hasText: 'Підрозділи' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(unit)
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: unit })).toBeVisible()
  // nomenclature (non-serial, service svc) on the Майно page
  await page.goto(`${URL}/catalog`)
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()
  await page.locator('.modal .fi').first().fill(nom)
  await page.locator('.modal select').first().selectOption({ label: svc })
  await page.locator('.btn-pri', { hasText: 'Зберегти' }).click()
  await expect(page.locator('td.td-name', { hasText: nom })).toBeVisible()
  // person in the unit — back to Довідники → Особи
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Особи' }).click()
  await page.locator('.btn-add').click()
  await page.locator('.modal .fi').first().fill(soldier)         // last_name
  await page.locator('.modal select').first().selectOption({ label: unit })  // unit
  await page.locator('.btn-pri').click()
  await expect(page.locator('td.td-name', { hasText: soldier })).toBeVisible()

  // ── Stock: receipt to service warehouse, then transfer to unit warehouse ──
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-select').selectOption({ label: `Склад ${svc}` })
  // receipt 10
  await page.locator('.btn-add', { hasText: '+ Рух' }).click()
  await page.locator('.modal select').nth(0).selectOption('receipt')
  await page.locator('.modal select').nth(1).selectOption({ label: `${nom} (несерійне)` })
  await page.locator('.modal input[type="number"]').fill('10')
  await page.locator('.btn-pri', { hasText: 'Провести' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)
  // transfer 10 → unit warehouse
  await page.locator('.btn-add', { hasText: '+ Рух' }).click()
  await page.locator('.modal select').nth(0).selectOption('transfer')
  await page.locator('.modal select').nth(1).selectOption({ label: `${nom} (несерійне)` })
  await page.locator('.modal select').nth(2).selectOption({ label: `Склад ${unit}` })
  await page.locator('.modal input[type="number"]').fill('10')
  await page.locator('.btn-pri', { hasText: 'Провести' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)

  // ── Switch to the unit warehouse; balance should be 10 ──
  await page.locator('.wh-select').selectOption({ label: `Склад ${unit}` })
  const balRow = page.locator('tbody tr', { hasText: nom }).first()
  await expect(balRow.locator('.td-num').first()).toContainText('10')

  // ── Issue 3 to the soldier ──
  await balRow.locator('.btn-issue').click()
  await page.locator('.modal select').first().selectOption({ label: soldier })
  await page.locator('.modal input[type="number"]').fill('3')
  await page.locator('.btn-pri', { hasText: 'Видати' }).click()
  await expect(page.locator('.overlay.open')).toHaveCount(0)

  // «Видано особам» shows the soldier; custody balance still 10
  const issuedRow = page.locator('tbody tr', { hasText: soldier }).first()
  await expect(issuedRow).toBeVisible()
  await expect(issuedRow).toContainText('3')
  const balRow2 = page.locator('tbody tr', { hasText: nom }).first()
  await expect(balRow2.locator('.td-num').first()).toContainText('10')  // unchanged
})
