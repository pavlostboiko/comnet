/**
 * Balances API — /api/residues/by-unit summary + detail.
 *
 * We can't create movements directly through the public API, so we drive
 * this end-to-end: seed an item + a signed переміщення document → the
 * sign endpoint creates a movement to the receiver unit → balance shows
 * up in the residues report. That covers the real path a user follows.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, seedNakladnaContext, bestEffortDelete } = require('./helpers/seed')

test.describe('Residues API · by-unit', () => {
  let api
  let cleanup

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    cleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, cleanup)
    await api.dispose()
  })

  test('signed nakladna creates a balance in the receiver unit', async () => {
    const seed = await seedNakladnaContext(api, 'res')
    const uniqUnit = seed.receiver.unit  // seed guarantees unique callsign / unit

    // Baseline: this unit may or may not exist in /by-unit, remember the
    // «before» count and total for our card.
    const beforeList = await api.get('/api/residues/by-unit').then(r => r.json())
    const beforeEntry = beforeList.find(x => x.unit === uniqUnit)

    // Create + sign a переміщення of 5 items
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-07-09',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 5, qty_received: 5 }],
    })
    cleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)
    await api.post(`/api/documents/${doc.id}/sign`)

    // /by-unit should now include the receiver's unit
    const afterList = await api.get('/api/residues/by-unit').then(r => r.json())
    const afterEntry = afterList.find(x => x.unit === uniqUnit)
    expect(afterEntry).toBeTruthy()
    // At least one more item than before (freshly seeded card wasn't there)
    const beforeCount = beforeEntry?.items_count ?? 0
    expect(afterEntry.items_count).toBeGreaterThanOrEqual(beforeCount + 1)

    // Detail contains our specific card
    const detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(uniqUnit)}`)
      .then(r => r.json())
    const ours = detail.items.find(x => x.item_card_num === seed.item.number)
    expect(ours).toBeTruthy()
    expect(Number(ours.qty)).toBe(5)
    expect(ours.name).toContain(seed.tag)
  })

  test('unsign removes the balance from the residues report', async () => {
    const seed = await seedNakladnaContext(api, 'resu')
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-07-09',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 3, qty_received: 3 }],
    })
    cleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)
    await api.post(`/api/documents/${doc.id}/sign`)

    // Present after sign
    let detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(seed.receiver.unit)}`)
      .then(r => r.json())
    expect(detail.items.find(x => x.item_card_num === seed.item.number)).toBeTruthy()

    // Unsign — movement is deleted, balance drops
    await api.post(`/api/documents/${doc.id}/unsign`)
    detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(seed.receiver.unit)}`)
      .then(r => r.json())
    expect(detail.items.find(x => x.item_card_num === seed.item.number)).toBeFalsy()
  })
})
