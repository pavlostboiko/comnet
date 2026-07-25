/**
 * v2 custody documents: group already-posted movements into a накладна,
 * sign → XLSX, unsign (movements stay). /api/custody/documents.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

async function deleteDocs(api, ids) {
  for (const id of ids) {
    try { await api.post(`/api/custody/documents/${id}/unsign`) } catch (_e) { /* draft */ }
    try { await api.delete(`/api/custody/documents/${id}`) } catch (_e) { /* swallow */ }
  }
}

test('group movements → document, sign → xlsx, unsign keeps ledger', async ({ request }) => {
  const api = await loginApi(request)
  const cleanup = []
  const docIds = []
  try {
    const tag = `cdoc-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `CDocSvc ${tag}`, chief_name: 'Ч', chief_position: 'Начальник' })
    const unit1 = await postJson(api, '/api/structure/units', { name: `CDocРота1 ${tag}` })
    const unit2 = await postJson(api, '/api/structure/units', { name: `CDocРота2 ${tag}` })
    cleanup.push(`/api/structure/units/${unit1.id}`, `/api/structure/units/${unit2.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const svcWh = whs.find(w => w.service_id === svc.id)
    const u1Wh = whs.find(w => w.unit_id === unit1.id)
    const u2Wh = whs.find(w => w.unit_id === unit2.id)

    // 3 non-serial noms, each received 10 into the service warehouse
    const noms = []
    for (let k = 0; k < 3; k++) {
      const n = await postJson(api, '/api/nomenclature', { name: `CPos${k} ${tag}`, service_id: svc.id, unit_of_measure: 'шт', price: 100 })
      cleanup.push(`/api/nomenclature/${n.id}`)
      await postJson(api, '/api/custody/movements', { date: '2026-07-01', type: 'receipt', nomenclature_id: n.id, to_warehouse_id: svcWh.id, quantity: 10 })
      noms.push(n)
    }

    // 4 transfer movements without a document: 3× svcWh→u1, 1× svcWh→u2
    const mkMove = (nomId, toWh) => postJson(api, '/api/custody/movements',
      { date: '2026-07-05', type: 'transfer', nomenclature_id: nomId, from_warehouse_id: svcWh.id, to_warehouse_id: toWh, quantity: 2 })
    const mvA = await mkMove(noms[0].id, u1Wh.id)   // A→B
    const mvB = await mkMove(noms[1].id, u1Wh.id)   // A→B
    const mvC = await mkMove(noms[2].id, u2Wh.id)   // A→C
    const mvD = await mkMove(noms[0].id, u1Wh.id)   // A→B (extra ungrouped)
    expect(mvA.document_id).toBeNull()

    // Create document from the two A→B movements → auto number, draft
    const doc = await postJson(api, '/api/custody/documents', {
      operation: 'transfer', form: 'накладна', doc_date: '2026-07-05',
      movement_ids: [mvA.id, mvB.id],
    })
    docIds.push(doc.id)
    expect(doc.status).toBe('draft')
    expect(doc.doc_number).toMatch(/^НК-2026-\d+$/)
    expect(doc.items_count).toBe(2)

    // Movements are now linked; the others stay free
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    const byId = Object.fromEntries(movements.map(m => [m.id, m]))
    expect(byId[mvA.id].document_id).toBe(doc.id)
    expect(byId[mvB.id].document_id).toBe(doc.id)
    expect(byId[mvC.id].document_id).toBeNull()

    // Different directions in one document → 400
    const mixed = await api.post('/api/custody/documents', {
      data: { operation: 'transfer', form: 'накладна', doc_date: '2026-07-05', movement_ids: [mvC.id, mvD.id] },
    })
    expect(mixed.status()).toBe(400)

    // A movement already in another document → 400
    const dup = await api.post('/api/custody/documents', {
      data: { operation: 'transfer', form: 'накладна', doc_date: '2026-07-05', movement_ids: [mvA.id] },
    })
    expect(dup.status()).toBe(400)

    // Empty selection → 400
    const empty = await api.post('/api/custody/documents', {
      data: { operation: 'transfer', form: 'накладна', doc_date: '2026-07-05', movement_ids: [] },
    })
    expect(empty.status()).toBe(400)

    // XLSX before sign still works (snap written on create); sign then export
    const signed = await postJson(api, `/api/custody/documents/${doc.id}/sign`, {})
    expect(signed.status).toBe('signed')
    const xlsx = await api.get(`/api/custody/documents/${doc.id}/export/xlsx`)
    expect(xlsx.status()).toBe(200)
    expect(xlsx.headers()['content-type']).toContain('spreadsheetml')
    expect((await xlsx.body()).length).toBeGreaterThan(1000)

    // Signed document cannot be edited
    const editSigned = await api.put(`/api/custody/documents/${doc.id}`, {
      data: { operation: 'transfer', form: 'накладна', doc_date: '2026-07-05', movement_ids: [mvA.id, mvB.id] },
    })
    expect(editSigned.status()).toBe(400)

    // Unsign → back to draft; movements + balance UNCHANGED (ledger untouched)
    const balBefore = await api.get(`/api/custody/balances?warehouse_id=${u1Wh.id}`).then(r => r.json())
    const nom0Before = balBefore.find(b => b.nomenclature_id === noms[0].id)?.quantity
    const un = await postJson(api, `/api/custody/documents/${doc.id}/unsign`, {})
    expect(un.status).toBe('draft')
    const stillLinked = await api.get('/api/custody/movements').then(r => r.json())
    expect(stillLinked.find(m => m.id === mvA.id).document_id).toBe(doc.id)
    const balAfter = await api.get(`/api/custody/balances?warehouse_id=${u1Wh.id}`).then(r => r.json())
    expect(balAfter.find(b => b.nomenclature_id === noms[0].id)?.quantity).toBe(nom0Before)

    // Second document → auto number increments within the same year
    const doc2 = await postJson(api, '/api/custody/documents', {
      operation: 'transfer', form: 'накладна', doc_date: '2026-07-05', movement_ids: [mvC.id],
    })
    docIds.push(doc2.id)
    expect(doc2.doc_number).toMatch(/^НК-2026-\d+$/)
    const seq = (s) => parseInt(s.split('-').pop(), 10)
    expect(seq(doc2.doc_number)).toBeGreaterThan(seq(doc.doc_number))
  } finally {
    await deleteDocs(api, docIds)
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  }
})
