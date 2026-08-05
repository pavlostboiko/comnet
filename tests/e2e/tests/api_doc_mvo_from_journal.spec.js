/**
 * Task 2a: document signatories (Здав/Прийняв/Фін) are resolved from the МВО
 * journal at doc_date and snapshotted on sign — no sender/receiver/fin FK.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { finWindow } = require('./helpers/mvo')

test('signed document snapshots signatories from the МВО journal by date', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const S = Date.now() + Math.floor(Math.random() * 1e6)
    // Власне вікно дат: фін-підписант цього тесту діє лише в ньому, тож інші
    // тести з їхнім «діючим» фіном сюди не дотягуються.
    const W = finWindow(S)
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Річ${S}`, service_id: svc.id, is_serialized: false, unit_of_measure: 'шт' } }).then(r => r.json())
    const mkUnit = async (n) => {
      const u = await api.post('/api/structure/units', { data: { name: `${S}-${n}` } }).then(r => r.json())
      const wh = (await api.get('/api/structure/warehouses').then(r => r.json())).find(w => w.unit_id === u.id)
      return wh
    }
    const whA = await mkUnit('A'), whB = await mkUnit('B')
    const mkPerson = (ln) => api.post('/api/settings/persons', { data: { last_name: ln, first_name: 'Ів' } }).then(r => r.json())
    const pA = await mkPerson(`Здавач${S}`)
    const pB = await mkPerson(`Приймач${S}`)
    const pF = await mkPerson(`Фінансист${S}`)

    // МВО journal: A→whA, B→whB, F→global fin, all active from before doc_date.
    // Посада/звання живуть на записі МВО (не на особі) → мають потрапити у snap.
    await api.post('/api/structure/mvo', { data: { warehouse_id: whA.id, person_id: pA.id, position: `посада ${S}A`, from_date: W.from, to_date: W.to } })
    await api.post('/api/structure/mvo', { data: { warehouse_id: whB.id, person_id: pB.id, position: `посада ${S}B`, rank: `звання ${S}B`, from_date: W.from, to_date: W.to } })
    await api.post('/api/structure/mvo', { data: { kind: 'fin', person_id: pF.id, position: `посада ${S}F`, from_date: W.from, to_date: W.to } })

    // Stock at A, transfer A→B (undocumented)
    await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id, quantity: 5, date: W.from } })
    const mv = await api.post('/api/custody/movements', { data: {
      type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id, nomenclature_id: nom.id, quantity: 2, date: W.doc } }).then(r => r.json())

    // Document over the transfer, then sign (snapshots signatories from journal)
    const doc = await api.post('/api/custody/documents', { data: {
      operation: 'transfer', form: 'накладна', doc_number: `NK-${S}`, doc_date: W.doc, movement_ids: [mv.id] } }).then(r => r.json())
    const signed = await api.post(`/api/custody/documents/${doc.id}/sign`).then(r => r.json())

    const snap = signed.extra_data
    expect(snap.snap_sender_name).toContain(`Здавач${S}`.toUpperCase())
    expect(snap.snap_recv_name).toContain(`Приймач${S}`.toUpperCase())
    expect(snap.snap_fin_name).toContain(`Фінансист${S}`.toUpperCase())
    // Посада/звання snapped from the МВО journal entry (task 8)
    expect(snap.snap_sender_post).toBe(`посада ${S}A`)
    expect(snap.snap_recv_post).toBe(`посада ${S}B`)
    expect(snap.snap_recv_rank).toBe(`звання ${S}B`)
    expect(snap.snap_fin_post).toBe(`посада ${S}F`)
    // FK fields are gone
    expect(signed.sender_id).toBeUndefined()
  } finally {
    await api.dispose()
  }
})
