/**
 * Unified item history: custody movements (warehouse↔warehouse) + assignments
 * (issued/returned to a person) merged chronologically. GET /custody/history.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('history merges movements and issue/return chronologically', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `hist-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `HSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `HРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const person = await postJson(api, '/api/settings/persons', { first_name: 'І', last_name: `Боєць${tag}`, unit_id: unit.id })
    cleanup.push(`/api/settings/persons/${person.id}`)
    const nom = await postJson(api, '/api/nomenclature', { name: `Річ ${tag}`, service_id: svc.id, unit_of_measure: 'шт', price: 100 })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    // receipt → svc, transfer → unit, issue → person, return
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    await postJson(api, '/api/custody/movements', { date: '2026-07-05', type: 'transfer', nomenclature_id: nom.id, from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id, quantity: 4 })
    const asg = await postJson(api, '/api/assignments', { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 2, is_official: true, issued_date: '2026-07-10' })
    await postJson(api, `/api/assignments/${asg.id}/return`, { returned_date: '2026-07-20' })

    const h = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    expect(h.name).toBe(`Річ ${tag}`)
    const kinds = h.events.map(e => e.kind === 'movement' ? e.type : e.kind)
    // newest first: return(07-20) · issued(07-10) · transfer(07-05) · receipt(07-01)
    expect(kinds).toEqual(['returned', 'issued', 'transfer', 'receipt'])

    const issued = h.events.find(e => e.kind === 'issued')
    expect(issued.person).toContain(`Боєць${tag}`)
    expect(Number(issued.qty)).toBe(2)
    const transfer = h.events.find(e => e.type === 'transfer')
    expect(transfer.from_warehouse).toBe(svcWh.name)
    expect(transfer.to_warehouse).toBe(unitWh.name)
    const returned = h.events.find(e => e.kind === 'returned')
    expect(returned.date).toBe('2026-07-20')
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
