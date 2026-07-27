/**
 * Revoke an UNDOCUMENTED movement (Model A): deleting it removes the ledger row
 * and reverts placement, so the instance returns to the previous warehouse and
 * the event disappears from history. Guards:
 *   - only the LATEST movement of an instance may be revoked (no chain break);
 *   - a movement attached to a document cannot be revoked (detach/delete doc first).
 *
 * Fully self-contained (unique names via API) so it never collides with other
 * specs on a shared DB.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

const S = 'REVAPI'  // unique suffix for this spec

test('revoke undocumented movement reverts placement and history; guards hold', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const svc = await api.post('/api/settings/services', { data: { name: `Svc${S}` } }).then(r => r.json())
    const nom = await api.post('/api/nomenclature', { data: {
      name: `Антена${S}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт' } }).then(r => r.json())
    const inst = await api.post(`/api/nomenclature/${nom.id}/instances`, { data: {
      serial_no: `${S}-SER-1`, card_number: `${S}-1` } }).then(r => r.json())
    const uA = await api.post('/api/structure/units', { data: { name: `${S}-A` } }).then(r => r.json())
    const uB = await api.post('/api/structure/units', { data: { name: `${S}-B` } }).then(r => r.json())
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const whA = whs.find(w => w.unit_id === uA.id)
    const whB = whs.find(w => w.unit_id === uB.id)

    // Place at A (receipt), then transfer A→B — both undocumented
    const mv1 = await api.post('/api/custody/movements', { data: {
      type: 'receipt', to_warehouse_id: whA.id, nomenclature_id: nom.id,
      instance_id: inst.id, date: '2026-06-01' } }).then(r => r.json())
    const mv2 = await api.post('/api/custody/movements', { data: {
      type: 'transfer', from_warehouse_id: whA.id, to_warehouse_id: whB.id,
      nomenclature_id: nom.id, instance_id: inst.id, date: '2026-06-02' } }).then(r => r.json())

    const curWh = () => api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
      .then(list => list.find(i => i.id === inst.id).current_warehouse_id)
    expect(await curWh()).toBe(whB.id)

    // Guard: cannot revoke the receipt (not the latest movement of the instance)
    const notLatest = await api.delete(`/api/custody/movements/${mv1.id}`)
    expect(notLatest.status()).toBe(400)
    expect((await notLatest.json()).detail).toContain('останній')

    // Guard: a documented movement cannot be revoked
    const doc = await api.post('/api/custody/documents', { data: {
      operation: 'transfer', form: 'накладна', movement_ids: [mv2.id] } }).then(r => r.json())
    const inDoc = await api.delete(`/api/custody/movements/${mv2.id}`)
    expect(inDoc.status()).toBe(400)
    expect((await inDoc.json()).detail).toContain('документ')
    // Detach by deleting the draft document (movements survive, become без документа)
    expect((await api.delete(`/api/custody/documents/${doc.id}`)).ok()).toBe(true)

    // Revoke the (now undocumented) latest movement → instance back at A
    const ok = await api.delete(`/api/custody/movements/${mv2.id}`)
    expect(ok.ok()).toBe(true)
    expect(await curWh()).toBe(whA.id)

    // History no longer contains the reverted transfer
    const hist = await api.get(`/api/custody/history?nomenclature_id=${nom.id}&instance_id=${inst.id}`).then(r => r.json())
    expect(hist.events.some(e => e.to_warehouse === whB.name)).toBe(false)
    expect(hist.events.some(e => e.source_id === mv2.id && e.source === 'movement')).toBe(false)
  } finally {
    await api.dispose()
  }
})
