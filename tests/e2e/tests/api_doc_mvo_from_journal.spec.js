/**
 * Task 2a: document signatories (Здав/Прийняв/Фін) are resolved from the МВО
 * journal at doc_date and snapshotted on sign — no sender/receiver/fin FK.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { closeActiveFin } = require('./helpers/mvo')

test('signed document snapshots signatories from the МВО journal by date', async ({ request }) => {
  const api = await loginApi(request)
  try {
    await closeActiveFin(api)   // ensure our fin is the active one at doc_date
    const S = Date.now()
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkUnit = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      const wh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
      return wh
    }
    const whA = await mkUnit('A'), whB = await mkUnit('B')
    const mkPerson = (ln) => api.post('/api/settings/persons', { data: { last_name: ln, first_name: 'Ів', position: `посада ${ln}` } }).then(r => r.json())
    const pA = await mkPerson(`Здавач${S}`)
    const pB = await mkPerson(`Приймач${S}`)
    const pF = await mkPerson(`Фінансист${S}`)

    // МВО journal: A→whA, B→whB, F→global fin, all active from before doc_date
    await api.post('/api/structure/mvo', { data: { warehouse_id: whA.id, person_id: pA.id, from_date: '2026-01-01' } })
    await api.post('/api/structure/mvo', { data: { warehouse_id: whB.id, person_id: pB.id, from_date: '2026-01-01' } })
    await api.post('/api/structure/mvo', { data: { kind: 'fin', person_id: pF.id, from_date: '2026-01-01' } })

    // Stock at A, transfer A→B (undocumented)
    await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, quantity: 5, date: '2026-07-01' } })
    const mv = await api.post('/api/custody/movements', { data: {
      type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id, nomenclature_id: nom.id, quantity: 2, date: '2026-07-10' } }).then(r => r.json())

    // Document over the transfer, then sign (snapshots signatories from journal)
    const doc = await api.post('/api/custody/documents', { data: {
      operation: 'transfer', form: 'накладна', doc_number: `NK-${S}`, doc_date: '2026-07-10', movement_ids: [mv.id] } }).then(r => r.json())
    const signed = await api.post(`/api/custody/documents/${doc.id}/sign`).then(r => r.json())

    const snap = signed.extra_data
    expect(snap.snap_sender_name).toContain(`Здавач${S}`.toUpperCase())
    expect(snap.snap_recv_name).toContain(`Приймач${S}`.toUpperCase())
    expect(snap.snap_fin_name).toContain(`Фінансист${S}`.toUpperCase())
    // FK fields are gone
    expect(signed.sender_id).toBeUndefined()
  } finally {
    await api.dispose()
  }
})
