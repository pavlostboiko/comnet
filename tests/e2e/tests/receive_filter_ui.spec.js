/**
 * UI smoke: «Прийняти майно» nomenclature picker is filtered by form —
 * «Без документа (НДМ)» shows only НДМ cards; «Накладна» shows only облік.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('receive picker filters nomenclature by form (облік vs НДМ)', async ({ page, request }) => {
  const api = await loginApi(request)
  const S = Date.now()
  const svcName = `SvcRF-${S}`
  const svc = await api.post('/api/settings/services', { data: { name: svcName } }).then(r => r.json())
  const offName = `Облік-${S}`
  const ndmName = `НДМ-${S}`
  await api.post('/api/nomenclature', { data: { name: offName, service_id: svc.id, is_serialized: false, is_official: true, unit_of_measure: 'шт' } })
  await api.post('/api/nomenclature', { data: { name: ndmName, service_id: svc.id, is_serialized: false, is_official: false, unit_of_measure: 'шт' } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/stock`)
  await page.locator('.wh-btn', { hasText: `Склад ${svcName}` }).click()
  await page.locator('button', { hasText: 'Прийняти майно' }).click()

  const nomInput = page.locator('.recv-row .row-nom input').first()

  // Default form = Накладна → only облік card in the picker (both names contain S)
  await nomInput.fill(String(S))
  await expect(page.locator('.ac-dropdown .ac-item', { hasText: offName })).toBeVisible()
  await expect(page.locator('.ac-dropdown .ac-item', { hasText: ndmName })).toHaveCount(0)

  // Switch to «Без документа» → only НДМ card
  await page.locator('.modal .doc-top select').first().selectOption({ label: 'Без документа (НДМ)' })
  await nomInput.fill(String(S))
  await expect(page.locator('.ac-dropdown .ac-item', { hasText: ndmName })).toBeVisible()
  await expect(page.locator('.ac-dropdown .ac-item', { hasText: offName })).toHaveCount(0)
})
