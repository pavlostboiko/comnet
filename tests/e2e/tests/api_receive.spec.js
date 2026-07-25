/**
 * v2 receipt document: приймання ззовні одразу документом (акт/накладна) на склад,
 * з можливістю створити номенклатуру на льоту. POST /api/custody/documents/receive.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test('receive external → document + movements; inline nomenclature; dup serial 400', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  const docIds = []
  try {
    const tag = `recv-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `RecvSvc ${tag}`, chief_name: 'Ч', chief_position: 'Нач' })
    cleanup.push(`/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)

    // existing non-serial card, marked ндм (is_official=false) — to prove is_official comes from the card
    const existing = await postJson(api, '/api/nomenclature', {
      name: `Наявна ${tag}`, service_id: svc.id, unit_of_measure: 'шт', price: 50, is_official: false,
    })
    cleanup.push(`/api/nomenclature/${existing.id}`)

    const resp = await api.post('/api/custody/documents/receive', {
      data: {
        to_warehouse_id: svcWh.id, form: 'акт', counterparty: `Постачальник ${tag}`, doc_date: '2026-07-10',
        items: [
          { nomenclature_id: existing.id, quantity: 7 },
          { new_nomenclature: { name: `Нова-нс ${tag}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: false }, quantity: 4 },
          { new_nomenclature: { name: `Нова-сер ${tag}`, service_id: svc.id, unit_of_measure: 'шт', is_serialized: true }, serial_no: `SER-${tag}`, card_number: `CARD-${tag}` },
        ],
      },
    })
    expect(resp.status()).toBe(201)
    const doc = await resp.json()
    docIds.push(doc.id)
    expect(doc.operation).toBe('receipt')
    expect(doc.form).toBe('акт')
    expect(doc.counterparty).toBe(`Постачальник ${tag}`)
    expect(doc.doc_number).toMatch(/^НК-2026-\d+$/)
    expect(doc.items_count).toBe(3)

    // Balances rose on the service warehouse
    const bal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    const existLine = bal.find(b => b.nomenclature_id === existing.id)
    expect(Number(existLine.qty)).toBe(7)
    expect(existLine.is_official).toBe(false)              // from the card, not the payload

    // New nomenclatures were created in the catalog
    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const newNs = noms.find(n => n.name === `Нова-нс ${tag}`)
    const newSer = noms.find(n => n.name === `Нова-сер ${tag}`)
    expect(newNs).toBeTruthy()
    expect(newSer?.is_serialized).toBe(true)
    cleanup.push(`/api/nomenclature/${newNs.id}`, `/api/nomenclature/${newSer.id}`)
    expect(Number(bal.find(b => b.nomenclature_id === newNs.id).qty)).toBe(4)

    // The serial instance is placed at the warehouse
    const serial = await api.get(`/api/custody/serial?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(serial.some(s => s.serial_no === `SER-${tag}`)).toBe(true)

    // Duplicate serial → 400 (whole receipt rejected)
    const dup = await api.post('/api/custody/documents/receive', {
      data: {
        to_warehouse_id: svcWh.id, form: 'накладна', doc_date: '2026-07-11',
        items: [{ nomenclature_id: newSer.id, serial_no: `SER-${tag}` }],
      },
    })
    expect(dup.status()).toBe(400)

    // Empty items → 400
    const empty = await api.post('/api/custody/documents/receive', {
      data: { to_warehouse_id: svcWh.id, form: 'накладна', doc_date: '2026-07-11', items: [] },
    })
    expect(empty.status()).toBe(400)
  } finally {
    for (const id of docIds) {
      try { await api.post(`/api/custody/documents/${id}/unsign`) } catch (_e) { /* draft */ }
      try { await api.delete(`/api/custody/documents/${id}`) } catch (_e) { /* swallow */ }
    }
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
