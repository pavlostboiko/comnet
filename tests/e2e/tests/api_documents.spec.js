/**
 * Integration tests for the documents API. Pure HTTP — no browser.
 * These cover the four critical guarantees of the snapshot architecture
 * so a refactor of `documents.py` can't regress them silently.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, seedNakladnaContext, bestEffortDelete } = require('./helpers/seed')

test.describe('Documents API', () => {
  let api
  let extraCleanup    // doc/movement paths created inside a single test

  test.beforeEach(async ({ request }) => {
    api = await loginApi(request)
    extraCleanup = []
  })

  test.afterEach(async () => {
    await bestEffortDelete(api, extraCleanup)
    await api.dispose()
  })

  // ── TZ §8: sign creates movements; unsign removes them ────────────────
  test('sign creates movements; unsign removes them', async () => {
    const seed = await seedNakladnaContext(api, 'sign')

    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-23',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [
        { item_id: seed.item.id, quantity: 2, qty_received: 2 },
        { item_id: seed.item.id, quantity: 1, qty_received: 1 },
      ],
    })
    extraCleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)

    const matchDoc = m => m.doc_number === doc.doc_number
    const movsBefore = await api.get('/api/movements').then(r => r.json())
    expect(movsBefore.filter(matchDoc).length).toBe(0)

    const signed = await api.post(`/api/documents/${doc.id}/sign`).then(r => r.json())
    expect(signed.status).toBe('signed')
    expect(signed.signed_at).toBeTruthy()

    const movsAfter = await api.get('/api/movements').then(r => r.json())
    expect(movsAfter.filter(matchDoc).length).toBe(2)

    const unsigned = await api.post(`/api/documents/${doc.id}/unsign`).then(r => r.json())
    expect(unsigned.status).toBe('draft')

    const movsFinal = await api.get('/api/movements').then(r => r.json())
    expect(movsFinal.filter(matchDoc).length).toBe(0)
  })

  // ── TZ §8.4-§8.5: snapshot invariance ─────────────────────────────────
  test('signed doc snap immune to person edits (TZ §8.4)', async () => {
    const seed = await seedNakladnaContext(api, 'snap')

    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-23',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 1, qty_received: 1 }],
    })
    extraCleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)

    // Sign so snapshot is locked
    await api.post(`/api/documents/${doc.id}/sign`)

    // Capture the snap BEFORE mutating — we assert against this baseline
    const before = await api.get(`/api/documents/${doc.id}`).then(r => r.json())
    expect(before.extra_data.snap_sender_post).toBe('Sender pos original')
    expect(before.extra_data.snap_sender_name).toContain('Sender')
    expect(before.extra_data.snap_sender_name).toContain('ORIGINAL')

    // Mutate the underlying person. DO NOT re-PUT the doc — that would
    // re-snap; the invariance is that mere directory edits never propagate
    // to an already-signed document.
    await api.put(`/api/settings/persons/${seed.sender.id}`, { data: {
      first_name: 'Changed',
      last_name: 'Different',
      position: 'New position',
    }})

    // Item too — price changes must not retroactively rewrite line snap
    await api.put(`/api/items/${seed.item.id}`, { data: {
      number: seed.item.number,
      name: 'Item RENAMED',
      price: 999.99,
    }})

    const after = await api.get(`/api/documents/${doc.id}`).then(r => r.json())
    expect(after.extra_data.snap_sender_post).toBe(before.extra_data.snap_sender_post)
    expect(after.extra_data.snap_sender_name).toBe(before.extra_data.snap_sender_name)
    expect(after.items[0].item_name).toBe(before.items[0].item_name)
    expect(Number(after.items[0].price)).toBe(Number(before.items[0].price))
  })

  // ── Auto-numbering: MAX(N)+1 by op_type.number_prefix ─────────────────
  test('auto-numbering generates sequential by prefix', async () => {
    const prefix = `AUTO-${Date.now()}-`
    const opType = await postJson(api, '/api/settings/op-types', {
      name: `auto-${Date.now()}`,
      number_prefix: prefix,
    })
    const otCleanup = `/api/settings/op-types/${opType.id}`

    const mkAuto = () => postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-23',
      op_type_id: opType.id,
      items: [],
    })

    const d1 = await mkAuto(); extraCleanup.push(`/api/documents/${d1.id}`)
    const d2 = await mkAuto(); extraCleanup.push(`/api/documents/${d2.id}`)
    const d3 = await mkAuto(); extraCleanup.push(`/api/documents/${d3.id}`)

    expect(d1.doc_number).toBe(`${prefix}1`)
    expect(d2.doc_number).toBe(`${prefix}2`)
    expect(d3.doc_number).toBe(`${prefix}3`)

    // Explicit number is NOT overridden
    const explicit = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-23',
      op_type_id: opType.id,
      doc_number: `${prefix}99`,
      items: [],
    })
    extraCleanup.push(`/api/documents/${explicit.id}`)
    expect(explicit.doc_number).toBe(`${prefix}99`)

    // Next auto picks up MAX+1 = 100
    const next = await mkAuto()
    extraCleanup.push(`/api/documents/${next.id}`)
    expect(next.doc_number).toBe(`${prefix}100`)

    extraCleanup.push(otCleanup)
  })

  // ── XLSX export: returns binary, no 500/400 ──────────────────────────
  test('export-xlsx returns 200 with spreadsheet body', async () => {
    // Snap requires unit_settings.name to be non-empty (else _has_snap → 400).
    // On a fresh DB without unit settings configured we skip rather than mutate.
    const unit = await api.get('/api/settings/unit').then(r => r.json())
    test.skip(!unit || !unit.name, 'unit_settings.name not configured')

    const seed = await seedNakladnaContext(api, 'xlsx')

    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-23',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 1, qty_received: 1 }],
    })
    extraCleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)

    const resp = await api.get(`/api/documents/${doc.id}/export/xlsx`)
    expect(resp.status()).toBe(200)
    expect(resp.headers()['content-type']).toContain('spreadsheetml')
    const body = await resp.body()
    expect(body.length).toBeGreaterThan(1000)
    // Excel files start with PK (ZIP magic)
    expect(body[0]).toBe(0x50)
    expect(body[1]).toBe(0x4b)
  })

  // ── Receipt + Накладна: «Звідки» is a free-text supplier (no sender FK) ──
  test('надходження + накладна snaps free-text from_unit when no sender_id', async () => {
    const seed = await seedNakladnaContext(api, 'recv')

    const doc = await postJson(api, '/api/documents', {
      operation: 'надходження', form: 'накладна',
      doc_date: '2026-05-25',
      from_unit: 'ТОВ Постачальник',          // free text instead of sender_id
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 1, qty_received: 1 }],
    })
    extraCleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)

    expect(doc.sender_id).toBeNull()
    expect(doc.from_unit).toBe('ТОВ Постачальник')
    expect(doc.extra_data.snap_sender_subdiv).toBe('ТОВ Постачальник')
    expect(doc.extra_data.snap_sender_post).toBe('')
    expect(doc.extra_data.snap_sender_name).toBe('')
  })

  // ── Illegal combo: переміщення + акт rejected with 400 ───────────────
  test('illegal combo: переміщення + акт returns 422', async () => {
    const resp = await api.post('/api/documents', { data: {
      operation: 'переміщення', form: 'акт',
      doc_date: '2026-05-25',
      items: [],
    }})
    // Pydantic validator → 422 Unprocessable Entity
    expect(resp.status()).toBe(422)
  })

  // ── After unsign, the draft must keep its items + lose its movements
  // ── (regression for 7b7f04c). The new-flow path keeps document_items
  // ── untouched; the legacy import-script path (no document_items, rows
  // ── only in movements) is hydrated before delete — that branch is
  // ── exercised only by code review here because there's no API to drop
  // ── document_items while keeping a doc signed.
  test('unsign leaves items intact and wipes movements', async () => {
    const seed = await seedNakladnaContext(api, 'unhyd')

    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-05-26',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [
        { item_id: seed.item.id, quantity: 3, qty_received: 3, notes: 'SN-A' },
        { item_id: seed.item.id, quantity: 2, qty_received: 2, notes: 'SN-B' },
      ],
    })
    extraCleanup.push(`/api/documents/${doc.id}`, ...seed.cleanup)

    await api.post(`/api/documents/${doc.id}/sign`)

    const unsigned = await api.post(`/api/documents/${doc.id}/unsign`).then(r => r.json())
    expect(unsigned.status).toBe('draft')
    expect(unsigned.items.length).toBe(2)

    const movs = await api.get('/api/movements').then(r => r.json())
    expect(movs.filter(m => m.doc_number === doc.doc_number).length).toBe(0)
  })
})
