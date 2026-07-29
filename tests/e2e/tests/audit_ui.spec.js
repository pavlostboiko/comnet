/**
 * UI smoke: «Журнал змін» lists audit records, filters by entity, and expands a
 * row to show the field diff.
 */
const { test, expect } = require('@playwright/test')
const { URL, uiLogin, loginApi } = require('./helpers/login')

test('audit page lists records, filters and expands a diff', async ({ page, request }) => {
  // Seed a change → produces a Service «create» audit entry
  const api = await loginApi(request)
  const name = `AuditUI-${Date.now()}`
  await api.post('/api/settings/services', { data: { name } })
  await api.dispose()

  await uiLogin(page)
  await page.goto(`${URL}/audit`)
  await expect(page.locator('.tile-title')).toContainText('Журнал змін')

  // Filter to Служба + Створено (deterministic even with many audit rows)
  await page.locator('.filters select').first().selectOption({ label: 'Служба' })
  await page.locator('.filters select').nth(1).selectOption({ label: 'Створено' })
  const row = page.locator('tbody tr.row', { hasText: 'Служба' }).first()
  await expect(row).toBeVisible()
  await expect(row).toContainText('Створено')

  // Expand → diff detail appears with the name field
  await row.click()
  await expect(page.locator('.detail-row .diff-field').first()).toBeVisible()
})
