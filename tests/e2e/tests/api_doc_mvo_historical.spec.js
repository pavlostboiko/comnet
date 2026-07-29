/**
 * Keystone: a document's signatory resolves to the HISTORICAL МВО active at
 * doc_date — a doc dated while pHist was МВО shows pHist even after pCur takes
 * over. This is the whole point (old documents stay stable via the journal).
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

test('signatory resolves to the historical МВО at doc_date, not the current one', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkWh = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      return (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
    }
    const whA = await mkWh('A'), whB = await mkWh('B')
    const pHist = await api.post('/api/settings/persons', { data: { last_name: `Історичний${S}` } }).then(r => r.json())
    const pCur = await api.post('/api/settings/persons', { data: { last_name: `Поточний${S}` } }).then(r => r.json())

    // whB МВО history: pHist [Jan–May], pCur [Jun–active]
    await api.post('/api/structure/mvo', { data: { warehouse_id: whB.id, person_id: pHist.id, from_date: '2026-01-01', to_date: '2026-05-31' } })
    await api.post('/api/structure/mvo', { data: { warehouse_id: whB.id, person_id: pCur.id, from_date: '2026-06-01' } })

    // Transfer dated 2026-03-10 (inside pHist's period)
    await api.post('/api/custody/movements', { data: { type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, quantity: 5, date: '2026-03-01' } })
    const mv = await api.post('/api/custody/movements', { data: { type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id, nomenclature_id: nom.id, quantity: 2, date: '2026-03-10' } }).then(r => r.json())
    const doc = await api.post('/api/custody/documents', { data: { operation: 'transfer', form: 'накладна', doc_number: `NK-${S}`, doc_date: '2026-03-10', movement_ids: [mv.id] } }).then(r => r.json())
    const signed = await api.post(`/api/custody/documents/${doc.id}/sign`).then(r => r.json())

    // Прийняв = the МВО active on 2026-03-10 → pHist, NOT pCur
    expect(signed.extra_data.snap_recv_name).toContain(`Історичний${S}`.toUpperCase())
    expect(signed.extra_data.snap_recv_name).not.toContain(`Поточний${S}`.toUpperCase())
  } finally {
    await api.dispose()
  }
})
