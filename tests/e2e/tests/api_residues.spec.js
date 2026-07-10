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

  test('by-recipient: split creates entry; return removes it', async () => {
    const tag = `rr-${Date.now()}`
    // Seed an item + a recipient
    const item = await postJson(api, '/api/items', {
      number: `RC-${tag}`, name: `Res-rc ${tag}`, unit_of_measure: 'шт',
      price: 100, quantity: 5, is_official: false,
    })
    const rcpt = await postJson(api, '/api/recipients', { callsign: `Rec-${tag}` })
    cleanup.push(`/api/items/${item.id}`, `/api/recipients/${rcpt.id}`)

    // Baseline
    const before = await api.get('/api/residues/by-recipient').then(r => r.json())
    expect(before.find(r => r.recipient_id === rcpt.id)).toBeFalsy()

    // Issue 3 units to the recipient
    const split = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: rcpt.id, qty: 3, notes: 'first drop',
    })

    // Master list now includes recipient
    const after = await api.get('/api/residues/by-recipient').then(r => r.json())
    const ours = after.find(r => r.recipient_id === rcpt.id)
    expect(ours).toBeTruthy()
    expect(ours.splits_count).toBe(1)
    expect(Number(ours.total_qty)).toBe(3)

    // Detail shows the split row
    const detail = await api.get(`/api/residues/by-recipient/${rcpt.id}`).then(r => r.json())
    expect(detail.callsign).toBe(`Rec-${tag}`)
    expect(detail.splits.length).toBe(1)
    expect(detail.splits[0].item_number).toBe(`RC-${tag}`)

    // Return the split → recipient disappears from the list
    await api.post(`/api/items/${item.id}/splits/${split.id}/return`)
    const afterReturn = await api.get('/api/residues/by-recipient').then(r => r.json())
    expect(afterReturn.find(r => r.recipient_id === rcpt.id)).toBeFalsy()
  })

  test('by-recipient: serial item assignment surfaces without a split', async () => {
    const tag = `rs-${Date.now()}`
    const rcpt = await postJson(api, '/api/recipients', { callsign: `Ser-${tag}` })
    const item = await postJson(api, '/api/items', {
      number: `SR-${tag}`, name: `Res-serial ${tag}`,
      serial_number: `SN-${tag}`, unit_of_measure: 'шт',
      price: 50, quantity: 1, is_official: false,
      issued_to_recipient_id: rcpt.id,
    })
    cleanup.push(`/api/items/${item.id}`, `/api/recipients/${rcpt.id}`)

    const detail = await api.get(`/api/residues/by-recipient/${rcpt.id}`).then(r => r.json())
    expect(detail.serial_items.length).toBe(1)
    expect(detail.serial_items[0].item_number).toBe(`SR-${tag}`)
    expect(detail.serial_items[0].serial_number).toBe(`SN-${tag}`)
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
