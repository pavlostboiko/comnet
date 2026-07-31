/**
 * UI smoke: Довідники → Підписанти can create a global «Фінслужба (загальна)» entry
 * (Тип=Фінслужба hides the warehouse select) and it shows in the list.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')
const { closeActiveFin } = require('./helpers/mvo')

test('add a global fin МВО via Довідники → Підписанти', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  await closeActiveFin(api)   // global fin is a singleton — clear before creating
  await api.post('/api/settings/persons', { data: { last_name: `ФінUI${S}` } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Підписанти' }).click()
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()

  // Тип = Фінслужба → warehouse select disappears
  await page.locator('.modal select').first().selectOption({ label: 'Фінслужба (загальна)' })
  await expect(page.locator('.modal').getByText('Склад *')).toHaveCount(0)

  // Особа — пошуковий дропдаун (ItemAutocomplete)
  await page.locator('.ac-field input').fill(`ФінUI${S}`)
  await page.locator('.ac-dropdown .ac-item', { hasText: `ФінUI${S}` }).first().click()
  await page.locator('.btn-pri').click()

  // Row appears as «Фінслужба (загальна)»
  await expect(page.locator('tbody tr', { hasText: 'Фінслужба (загальна)' }).first()).toBeVisible()
})
