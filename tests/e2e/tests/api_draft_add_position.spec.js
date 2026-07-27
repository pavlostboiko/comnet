/**
 * A DRAFT custody document can gain positions: PUT with an extra undocumented
 * movement of the SAME direction attaches it; a movement of a DIFFERENT
 * direction is rejected. Self-contained (unique names) to avoid collisions.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

const S = 'ADDPOS'

test('draft document: add same-direction movement; reject different direction', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkUnit = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      const whs = await api.get('/api/structure/warehouses').then(r => r.json())
      return whs.find(w => w.unit_id === u.id)
    }
    const A = await mkUnit('A'), B = await mkUnit('B'), C = await mkUnit('C')
    const mv = (data) => api.post('/api/custody/movements', { data }).then(r => r.json())

    await mv({ type: 'receipt', to_warehouse_id: A.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' })
    const t1 = await mv({ type: 'transfer', from_warehouse_id: A.id, to_warehouse_id: B.id, nomenclature_id: nom.id, quantity: 2, date: '2026-07-02' })
    const t2 = await mv({ type: 'transfer', from_warehouse_id: A.id, to_warehouse_id: B.id, nomenclature_id: nom.id, quantity: 1, date: '2026-07-03' })
    const t3 = await mv({ type: 'transfer', from_warehouse_id: A.id, to_warehouse_id: C.id, nomenclature_id: nom.id, quantity: 1, date: '2026-07-04' })

    // Draft from a single A→B movement
    const doc = await api.post('/api/custody/documents', { data: {
      operation: 'transfer', form: 'накладна', movement_ids: [t1.id] } }).then(r => r.json())
    expect(doc.lines).toHaveLength(1)

    // Add the second A→B movement → now two positions, t2 attached
    const upd = { operation: 'transfer', form: 'накладна', movement_ids: [t1.id, t2.id] }
    const grown = await api.put(`/api/custody/documents/${doc.id}`, { data: upd }).then(r => r.json())
    expect(grown.lines).toHaveLength(2)
    expect(grown.lines.map(l => l.id).sort()).toEqual([t1.id, t2.id].sort())
    const t2m = (await api.get('/api/custody/movements').then(r => r.json())).find(m => m.id === t2.id)
    expect(t2m.document_id).toBe(doc.id)

    // Adding a movement of a different direction (A→C) is rejected
    const bad = await api.put(`/api/custody/documents/${doc.id}`, { data: {
      operation: 'transfer', form: 'накладна', movement_ids: [t1.id, t3.id] } })
    expect(bad.status()).toBe(400)
    expect((await bad.json()).detail).toContain('напрямк')
  } finally {
    await api.dispose()
  }
})
