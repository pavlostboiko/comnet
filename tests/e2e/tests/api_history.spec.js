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

test('same-date transfer-with-issue: issue sorts above the transfer', async ({ request }) => {
  // Regression: a transfer and its issue happen on the SAME date, both without a
  // doc_number → they tie on date + doc_sort_key. The tie must break on
  // `created_at` (issue recorded after the transfer), NOT on cross-table id.
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `hsd-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `SDSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `SDРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const person = await postJson(api, '/api/settings/persons', { first_name: 'І', last_name: `Боєць${tag}`, unit_id: unit.id })
    cleanup.push(`/api/settings/persons/${person.id}`)
    const nom = await postJson(api, '/api/nomenclature', { name: `Річ ${tag}`, service_id: svc.id, unit_of_measure: 'шт', price: 50 })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    // receipt (earlier) → svc; then transfer→unit WITH issue to person, same date, no doc
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    await postJson(api, '/api/custody/document', {
      date: '2026-07-05', from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id,
      items: [{ nomenclature_id: nom.id, quantity: 3, assign_person_id: person.id }],
    })

    const h = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    const kinds = h.events.map(e => e.kind === 'movement' ? e.type : e.kind)
    // newest first: issued (recorded after transfer, same date) · transfer · receipt
    expect(kinds).toEqual(['issued', 'transfer', 'receipt'])
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})

test('history scoped to a single serial instance', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `hins-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `HISvc ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const nom = await postJson(api, '/api/nomenclature', { name: `Рація ${tag}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    const i1 = await postJson(api, `/api/nomenclature/${nom.id}/instances`, { serial_no: `A-${tag}` })
    const i2 = await postJson(api, `/api/nomenclature/${nom.id}/instances`, { serial_no: `B-${tag}` })
    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, instance_id: i1.id, to_warehouse_id: svcWh.id })
    await postJson(api, '/api/custody/movements', { date: '2026-07-02', type: 'receipt', nomenclature_id: nom.id, instance_id: i2.id, to_warehouse_id: svcWh.id })

    // whole-card history has both; instance-scoped has only i1
    const all = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    expect(all.events.length).toBe(2)
    const one = await api.get(`/api/custody/history?nomenclature_id=${nom.id}&instance_id=${i1.id}`).then(r => r.json())
    expect(one.events.length).toBe(1)
    expect(one.events[0].serial_no).toBe(`A-${tag}`)
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})

test('same-date issue sorts above a DOCUMENTED transfer', async ({ request }) => {
  // Регресія: рух із номером накладної вигравав у видачі по doc_sort_key і
  // ставав над нею, хоча видача того ж дня сталася пізніше.
  const api = await loginApi(request)
  const cleanup = []
  try {
    const tag = `hdoc-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `HDSvc ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `HDРота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const person = await postJson(api, '/api/settings/persons',
      { first_name: 'І', last_name: `Боєць${tag}`, unit_id: unit.id })
    cleanup.push(`/api/settings/persons/${person.id}`)
    const nom = await postJson(api, '/api/nomenclature',
      { name: `Річ ${tag}`, service_id: svc.id, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt',
      nomenclature_id: nom.id, to_warehouse_id: svcWh.id, quantity: 10 })
    // Переміщення НАКЛАДНОЮ (є номер) + видача тією ж датою
    await postJson(api, '/api/custody/document', {
      date: '2026-07-05', from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id,
      doc_number: '596/250/2/7',
      items: [{ nomenclature_id: nom.id, quantity: 3 }],
    })
    await postJson(api, '/api/assignments', { warehouse_id: unitWh.id, person_id: person.id,
      nomenclature_id: nom.id, quantity: 2, issued_date: '2026-07-05' })

    const h = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    const kinds = h.events.map(e => e.kind === 'movement' ? e.type : e.kind)
    expect(kinds).toEqual(['issued', 'transfer', 'receipt'])

    // Дві накладні того ж дня далі впорядковані номером (задача 10 не зламана)
    await postJson(api, '/api/custody/document', {
      date: '2026-07-05', from_warehouse_id: svcWh.id, to_warehouse_id: unitWh.id,
      doc_number: '596/250/2/10',
      items: [{ nomenclature_id: nom.id, quantity: 1 }],
    })
    const h2 = await api.get(`/api/custody/history?nomenclature_id=${nom.id}`).then(r => r.json())
    const docs = h2.events.filter(e => e.kind === 'movement' && e.type === 'transfer').map(e => e.doc_number)
    expect(docs).toEqual(['596/250/2/10', '596/250/2/7'])
    expect(h2.events[0].kind).toBe('issued')     // видача все одно зверху
  } finally {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
