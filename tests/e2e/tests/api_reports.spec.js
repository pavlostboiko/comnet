/** «Видане» report data: per-person holdings (enriched) + per-group holdings. */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('assignments by person (enriched) and by group', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `rep-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `RepSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `RepРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const grp = await postJson(api, '/api/structure/groups', { name: `Гр ${tag}`, unit_id: unit.id })
    const person = await postJson(api, '/api/settings/persons', { last_name: `Боєць${tag}`, unit_id: unit.id, group_id: grp.id })
    cleanup.push(`/api/settings/persons/${person.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const nom = await postJson(api, '/api/nomenclature', { name: `Річ ${tag}`, service_id: svc.id, unit_of_measure: 'шт', price: 10 })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    await postJson(api, '/api/custody/movements', { date: '2026-07-02', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 5 })
    await postJson(api, '/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 2, is_official: true, issued_date: '2026-07-03' })

    // by person — enriched with names
    const byPerson = await api.get(`/api/assignments?person_id=${person.id}&active=true`).then(r => r.json())
    expect(byPerson).toHaveLength(1)
    expect(byPerson[0].nomenclature_name).toBe(`Річ ${tag}`)
    expect(byPerson[0].warehouse_name).toBe(unitWh.name)
    expect(Number(byPerson[0].quantity)).toBe(2)

    // by group — member with items
    const byGroup = await api.get(`/api/assignments/group/${grp.id}`).then(r => r.json())
    expect(byGroup.total_items).toBe(1)
    const member = byGroup.members.find(m => m.person_id === person.id)
    expect(member.person_name).toContain(`Боєць${tag}`)
    expect(member.items[0].name).toBe(`Річ ${tag}`)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
