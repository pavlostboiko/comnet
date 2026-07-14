/**
 * Balances API — /api/residues/by-unit summary + detail.
 *
 * We can't create movements directly through the public API, so we drive
 * this end-to-end: seed an item + a signed переміщення document → the
 * sign endpoint creates a movement to the receiver unit → balance shows
 * up in the residues report. That covers the real path a user follows.
 */
const { test, expect, request: pwRequest } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, seedNakladnaContext, bestEffortDelete } = require('./helpers/seed')

const API = process.env.API_URL || 'http://backend:8000'

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

  test('by-unit detail: current_holders lists callsigns holding the card', async () => {
    const seed = await seedNakladnaContext(api, 'hld')
    await api.put(`/api/items/${seed.item.id}`, { data: { quantity: 5 } })
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-07-11',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 5, qty_received: 5 }],
    })
    cleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)
    await api.post(`/api/documents/${doc.id}/sign`)

    const rcpt = await postJson(api, '/api/recipients', { callsign: `Hold-${seed.tag}` })
    cleanup.push(`/api/recipients/${rcpt.id}`)
    await postJson(api, `/api/items/${seed.item.id}/splits`, {
      recipient_id: rcpt.id, qty: 2,
    })

    const detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(seed.receiver.unit)}`)
      .then(r => r.json())
    const ours = detail.items.find(x => x.item_card_num === seed.item.number)
    expect(ours.current_holders).toContain(`Hold-${seed.tag}`)
  })

  test('backfill-splits: creates ledger entries for items missing them', async () => {
    // Simulate the pre-fix state: item with issued_to_recipient_id but no ItemSplit.
    // POST /items with issued_to_recipient_id set — the hook fires now, but we
    // then delete the split it just created to reproduce a legacy-import row.
    const rcpt = await postJson(api, '/api/recipients', { callsign: `Bfil-${Date.now()}-${Math.floor(Math.random() * 9999)}` })
    const tag = `bfil-${Date.now()}`
    const item = await postJson(api, '/api/items', {
      number: `BF-${tag}`, name: `Backfill ${tag}`,
      unit_of_measure: 'шт', price: 1, quantity: 2, is_official: false,
      issued_to_recipient_id: rcpt.id,
    })
    cleanup.push(`/api/items/${item.id}`, `/api/recipients/${rcpt.id}`)

    // Drop the auto-created split to mimic legacy data
    const splits = await api.get(`/api/items/${item.id}/splits`).then(r => r.json())
    for (const s of splits) {
      await api.delete(`/api/items/${item.id}/splits/${s.id}`)
    }
    const empty = await api.get(`/api/items/${item.id}/splits`).then(r => r.json())
    expect(empty.length).toBe(0)

    // Backfill
    const resp = await api.post('/api/admin/backfill-splits')
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.created).toBeGreaterThanOrEqual(1)

    const after = await api.get(`/api/items/${item.id}/splits`).then(r => r.json())
    expect(after.some(s => s.is_active && s.recipient_id === rcpt.id)).toBe(true)

    // Rerun is a no-op (idempotent)
    const rerun = await api.post('/api/admin/backfill-splits').then(r => r.json())
    // We already scanned; nothing new for this specific item
    const stillOne = await api.get(`/api/items/${item.id}/splits`).then(r => r.json())
    expect(stillOne.filter(s => s.is_active).length).toBe(1)
  })

  test('return of an imported orphan item by МВО places it in her subdivision', async ({ request }) => {
    // Reproduces + verifies fix for: import Item with «Видано» → item has an
    // active split but no movement. Before the fix, «Повернути» closed the
    // split and the card vanished from every residues surface. With the fix,
    // returning as МВО (person_unit set) synthesizes a movement into her
    // subdivision so the card stays visible in /residues/by-unit/{her unit}.
    const tag = `retorph-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const unit = `MVO-Unit-${tag}`

    // Seed persons/users: an МВО operator linked to a person with a unit
    const person = await postJson(api, '/api/settings/persons', {
      first_name: 'Mvo', last_name: `T-${tag}`, position: 'МВО', unit,
    })
    const mvoUser = await postJson(api, '/api/users', {
      username: `mvo-${tag}`, password: 'mvo-pw-strong',
      role: 'operator', is_active: true, person_id: person.id,
    })
    cleanup.push(`/api/users/${mvoUser.id}`, `/api/settings/persons/${person.id}`)

    // Seed the imported-orphan item
    const rcpt = await postJson(api, '/api/recipients', { callsign: `RO-${tag}` })
    const item = await postJson(api, '/api/items', {
      number: `RO-${tag}`, name: `Ret-orphan ${tag}`,
      unit_of_measure: 'шт', price: 10, quantity: 3, is_official: false,
      issued_to_recipient_id: rcpt.id,
    })
    cleanup.push(`/api/items/${item.id}`, `/api/recipients/${rcpt.id}`)

    // Baseline: item is currently on the recipient, and NOT in any /by-unit
    // detail (no movement placed it anywhere).
    const beforeUnits = await api.get('/api/residues/by-unit').then(r => r.json())
    for (const u of beforeUnits) {
      const d = await api.get(`/api/residues/by-unit/${encodeURIComponent(u.unit)}`).then(r => r.json())
      expect(d.items.find(x => x.item_card_num === `RO-${tag}`)).toBeFalsy()
    }

    // Log in as МВО and return the item via PUT null
    const mvoLogin = await request.post(`${API}/api/auth/login`, {
      form: { username: `mvo-${tag}`, password: 'mvo-pw-strong' },
    })
    const mvoToken = (await mvoLogin.json()).access_token
    const mvoApi = await pwRequest.newContext({
      baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${mvoToken}` },
    })
    try {
      const putResp = await mvoApi.put(`/api/items/${item.id}`, {
        data: { issued_to_recipient_id: null },
      })
      expect(putResp.status()).toBe(200)
    } finally {
      await mvoApi.dispose()
    }

    // Recipient no longer holds it
    const afterList = await api.get('/api/residues/by-recipient').then(r => r.json())
    expect(afterList.find(r => r.recipient_id === rcpt.id)).toBeFalsy()

    // МВО's unit now has the card (via synthetic movement)
    const detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(unit)}`).then(r => r.json())
    const placed = detail.items.find(x => x.item_card_num === `RO-${tag}`)
    expect(placed).toBeTruthy()
    expect(Number(placed.qty)).toBe(3)  // full item.quantity landed
  })

  test('return of a movement-placed item does NOT double-count residues', async ({ request }) => {
    // Sanity: for items placed via a real movement, return does not
    // synthesize an extra movement — otherwise we'd inflate residues.
    const seed = await seedNakladnaContext(api, 'retmv')
    await api.put(`/api/items/${seed.item.id}`, { data: { quantity: 5 } })
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-07-14',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 5, qty_received: 5 }],
    })
    cleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)
    await api.post(`/api/documents/${doc.id}/sign`)

    // Set up an МВО linked to the receiver's unit
    const mvoTag = `mv-${seed.tag}`
    const mvoUser = await postJson(api, '/api/users', {
      username: `mvo-${mvoTag}`, password: 'mvo-pw-strong',
      role: 'operator', is_active: true, person_id: seed.receiver.id,
    })
    cleanup.push(`/api/users/${mvoUser.id}`)

    // Issue + return a split as МВО
    const rcpt = await postJson(api, '/api/recipients', { callsign: `RM-${mvoTag}` })
    cleanup.push(`/api/recipients/${rcpt.id}`)
    const split = await postJson(api, `/api/items/${seed.item.id}/splits`, {
      recipient_id: rcpt.id, qty: 2,
    })

    // Log in as МВО, do the return
    const mvoLogin = await request.post(`${API}/api/auth/login`, {
      form: { username: `mvo-${mvoTag}`, password: 'mvo-pw-strong' },
    })
    const mvoApi = await pwRequest.newContext({
      baseURL: API,
      extraHTTPHeaders: { Authorization: `Bearer ${(await mvoLogin.json()).access_token}` },
    })
    try {
      const rr = await mvoApi.post(`/api/items/${seed.item.id}/splits/${split.id}/return`)
      expect(rr.status()).toBe(200)
    } finally {
      await mvoApi.dispose()
    }

    // Residue in receiver's unit stays at 5 — no synthetic double-count
    const detail = await api.get(`/api/residues/by-unit/${encodeURIComponent(seed.receiver.unit)}`).then(r => r.json())
    const row = detail.items.find(x => x.item_card_num === seed.item.number)
    expect(row).toBeTruthy()
    expect(Number(row.qty)).toBe(5)
  })

  test('by-recipient detail: current_unit reflects the subdivision where the item lives', async () => {
    const seed = await seedNakladnaContext(api, 'loc')
    // Make sure the seeded item has a quantity to issue from
    await api.put(`/api/items/${seed.item.id}`, { data: { quantity: 3 } })

    // Seed + sign a переміщення so the item ends up in seed.receiver.unit
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-07-10',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 3, qty_received: 3 }],
    })
    cleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)
    await api.post(`/api/documents/${doc.id}/sign`)

    // Issue 1 unit to a recipient
    const rcpt = await postJson(api, '/api/recipients', { callsign: `Loc-${seed.tag}` })
    cleanup.push(`/api/recipients/${rcpt.id}`)
    await postJson(api, `/api/items/${seed.item.id}/splits`, {
      recipient_id: rcpt.id, qty: 1,
    })

    const detail = await api.get(`/api/residues/by-recipient/${rcpt.id}`).then(r => r.json())
    expect(detail.splits.length).toBe(1)
    expect(detail.splits[0].current_unit).toBe(seed.receiver.unit)
  })

  test('serial return: PUT items with null recipient closes active split + removes from by-recipient', async () => {
    const tag = `sret-${Date.now()}`
    const rcpt = await postJson(api, '/api/recipients', { callsign: `Sret-${tag}` })
    const item = await postJson(api, '/api/items', {
      number: `SR-${tag}`, name: `Return-serial ${tag}`,
      serial_number: `SN-${tag}`, unit_of_measure: 'шт',
      price: 50, quantity: 1, is_official: false,
      issued_to_recipient_id: rcpt.id,
    })
    cleanup.push(`/api/items/${item.id}`, `/api/recipients/${rcpt.id}`)

    // Recipient has the item now
    const before = await api.get(`/api/residues/by-recipient/${rcpt.id}`).then(r => r.json())
    expect(before.serial_items.length).toBe(1)

    // Return via PUT null
    await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: null } })

    // Recipient no longer holds it
    const afterList = await api.get('/api/residues/by-recipient').then(r => r.json())
    expect(afterList.find(r => r.recipient_id === rcpt.id)).toBeFalsy()

    // History records both events
    const history = await api.get(`/api/items/${item.id}/history`).then(r => r.json())
    expect(history.some(e => e.kind === 'issued')).toBeTruthy()
    expect(history.some(e => e.kind === 'returned')).toBeTruthy()
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
