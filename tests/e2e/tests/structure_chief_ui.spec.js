/**
 * UI smoke: вкладку перейменовано на «Підписанти», і в ній можна завести
 * начальника служби (Тип=Начальник служби → вибір служби замість складу).
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('add a service chief via Довідники → Підписанти', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  const svc = await api.post('/api/settings/services', { data: { name: `ChiefUI${S}` } }).then(r => r.json())
  await api.post('/api/settings/persons', { data: { last_name: `НачUI${S}` } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/structure`)
  await page.locator('.tt-btn', { hasText: 'Підписанти' }).click()
  await page.locator('.btn-add', { hasText: '+ Додати' }).click()

  // Тип = Начальник служби → замість складу з'являється вибір служби
  await page.locator('.modal select').first().selectOption({ label: 'Начальник служби' })
  await expect(page.locator('.modal').getByText('Склад *')).toHaveCount(0)
  await page.locator('.modal').getByText('Служба *').waitFor()
  await page.locator('.modal select').nth(1).selectOption({ label: `ChiefUI${S}` })

  await page.locator('.ac-field input').fill(`НачUI${S}`)
  await page.locator('.ac-dropdown .ac-item', { hasText: `НачUI${S}` }).first().click()
  await page.locator('.btn-pri').click()

  await expect(page.locator('tbody tr', { hasText: `Начальник: ChiefUI${S}` }).first()).toBeVisible()
})
