const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { URL, API, uiLogin, getToken } = require('./helpers/login')

// Звіти → «Видане на особу»: pick a person, see what they hold.
test('Reports «Видане на особу» shows a person’s holdings', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const svc = await j('/api/settings/services', { name: `RpSvc ${ts}` })
  const unit = await j('/api/structure/units', { name: `RpРота ${ts}` })
  const person = await j('/api/settings/persons', { last_name: `Боєць${ts}`, first_name: 'Іван', callsign: `Сокіл${ts}`, unit_id: unit.id })
  const whs = await api.get('/api/structure/warehouses').then(r => r.json())
  const svcWh = whs.find(w => w.service_id === svc.id)
  const unitWh = whs.find(w => w.unit_id === unit.id)
  const nom = await j('/api/nomenclature', { name: `Річ ${ts}`, service_id: svc.id, unit_of_measure: 'шт' })
  await j('/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
  await j('/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 5 })
  await j('/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 2, is_official: true, issued_date: '2026-07-03' })

  await uiLogin(page)
  await page.goto(`${URL}/reports`)
  await expect(page.locator('.tile-title')).toContainText('Звіти')
  // Пошуковий пікер замість <select>; підпис — «Прізвище Ім'я (Позивний)»
  await expect(page.locator('.sel-row select')).toHaveCount(0)
  await page.locator('.sel-row .ac-field input').fill(`Сокіл${ts}`)
  const opt = page.locator('.ac-dropdown .ac-item', { hasText: `Боєць${ts} Іван (Сокіл${ts})` }).first()
  await expect(opt).toBeVisible()
  await opt.click()
  await expect(page.locator('tbody tr', { hasText: `Річ ${ts}` })).toBeVisible()

  await api.delete(`/api/settings/persons/${person.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.delete(`/api/settings/services/${svc.id}`).catch(() => {})
  await api.dispose()
})

// «Видане на групу»: командир одразу в групі; група без бійців — явна підказка.
test('Reports «Видане на групу»: commander is listed, empty group explains itself', async ({ page, request }) => {
  const token = await getToken(request)
  const api = await pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  const j = (p, b) => api.post(p, { data: b }).then(r => r.json())
  const ts = Date.now()
  const unit = await j('/api/structure/units', { name: `GrРота ${ts}` })
  const boss = await j('/api/settings/persons', { last_name: `Комгр${ts}`, first_name: 'Петро', unit_id: unit.id })
  const grp = await j('/api/structure/groups', { name: `Гр-к ${ts}`, unit_id: unit.id, commander_id: boss.id })
  const empty = await j('/api/structure/groups', { name: `Гр-порожня ${ts}`, unit_id: unit.id })

  await uiLogin(page)
  await page.goto(`${URL}/reports`)
  await page.locator('.tabs button', { hasText: 'Видане на групу' }).click()

  await page.locator('.sel-row select.fi').selectOption({ label: `Гр-к ${ts}` })
  const member = page.locator('.g-member', { hasText: `Комгр${ts}` })
  await expect(member).toBeVisible()
  await expect(member.locator('.chip-cmd')).toHaveText('командир')

  await page.locator('.sel-row select.fi').selectOption({ label: `Гр-порожня ${ts}` })
  await expect(page.locator('.g-none')).toContainText('немає бійців')

  await api.delete(`/api/structure/groups/${grp.id}`).catch(() => {})
  await api.delete(`/api/structure/groups/${empty.id}`).catch(() => {})
  await api.delete(`/api/settings/persons/${boss.id}`).catch(() => {})
  await api.delete(`/api/structure/units/${unit.id}`).catch(() => {})
  await api.dispose()
})
