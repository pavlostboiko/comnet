/**
 * /api/items/{id}/history — merged chronological ledger.
 *
 * Covers:
 *  - Journal-on-PUT for serial items: assigning a recipient creates a split;
 *    reassigning closes the previous and opens a new one; clearing closes it.
 *  - History endpoint merges movements + split events and sorts by date DESC.
 *  - returned_by is captured on split-return via /api/items/{id}/splits/{sid}/return.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Item history & serial journaling', () => {
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

  async function makeSerialItem() {
    const tag = `hs-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const item = await postJson(api, '/api/items', {
      number: `H-${tag}`, name: `Serial ${tag}`,
      unit_of_measure: 'шт', price: 100, quantity: 1,
      serial_number: `SN-${tag}`, is_official: false,
    })
    cleanup.push(`/api/items/${item.id}`)
    return item
  }
  async function makeRecipient(prefix) {
    const r = await postJson(api, '/api/recipients', { callsign: `${prefix}-${Date.now()}-${Math.floor(Math.random() * 9999)}` })
    cleanup.push(`/api/recipients/${r.id}`)
    return r
  }

  test('PUT serial item.issued_to_recipient_id opens a split; reassign closes previous and opens new; clear closes it', async () => {
    const item = await makeSerialItem()
    const rA = await makeRecipient('holder-A')
    const rB = await makeRecipient('holder-B')

    // Assign to A → 1 active split
    let resp = await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: rA.id } })
    expect(resp.status()).toBe(200)
    let splitsResp = await api.get(`/api/items/${item.id}/splits`)
    let splits = await splitsResp.json()
    expect(splits.filter(s => s.is_active)).toHaveLength(1)
    expect(splits[0].recipient_id).toBe(rA.id)

    // Reassign to B → previous closed, new active
    resp = await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: rB.id } })
    expect(resp.status()).toBe(200)
    splits = await (await api.get(`/api/items/${item.id}/splits`)).json()
    const active = splits.filter(s => s.is_active)
    const closed = splits.filter(s => !s.is_active)
    expect(active).toHaveLength(1)
    expect(closed).toHaveLength(1)
    expect(active[0].recipient_id).toBe(rB.id)
    expect(closed[0].recipient_id).toBe(rA.id)
    expect(closed[0].returned_at).not.toBeNull()

    // Clear → both closed
    resp = await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: null } })
    expect(resp.status()).toBe(200)
    splits = await (await api.get(`/api/items/${item.id}/splits`)).json()
    expect(splits.filter(s => s.is_active)).toHaveLength(0)
    expect(splits).toHaveLength(2)
  })

  test('GET /api/items/{id}/history merges split events sorted DESC by date', async () => {
    const item = await makeSerialItem()
    const rA = await makeRecipient('h-A')
    const rB = await makeRecipient('h-B')

    // Two assignments → 3 events (issued A, returned A, issued B)
    await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: rA.id } })
    await api.put(`/api/items/${item.id}`, { data: { issued_to_recipient_id: rB.id } })

    const resp = await api.get(`/api/items/${item.id}/history`)
    expect(resp.status()).toBe(200)
    const history = await resp.json()
    // At minimum: A issued, A returned, B issued
    const kinds = history.map(e => e.kind)
    expect(kinds.filter(k => k === 'issued').length).toBeGreaterThanOrEqual(2)
    expect(kinds).toContain('returned')

    // Every event has a date, kind, and source
    for (const e of history) {
      expect(e.date).toBeTruthy()
      expect(['issued', 'returned', 'in', 'out']).toContain(e.kind)
      expect(['split', 'movement']).toContain(e.source)
    }

    // DESC sort: successive dates non-increasing
    for (let i = 1; i < history.length; i++) {
      expect(history[i - 1].date >= history[i].date).toBeTruthy()
    }
  })

  test('admin XLSX import creates an «issued» history event for serial items with «Видано»', async () => {
    // Read the pre-built fixture. Row: IMP-HIST-001 / SN-IMPHIST-001 / issued to «IMP-HIST-RCPT».
    const fixture = fs.readFileSync(path.join(__dirname, 'fixtures/import_items_serial.xlsx'))

    const impResp = await api.post('/api/admin/import/items', {
      multipart: {
        file: {
          name: 'import_items_serial.xlsx',
          mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
          buffer: fixture,
        },
      },
    })
    if (impResp.status() === 409) {
      // Fixture may already be present from a previous run — wipe and retry
      await api.post('/api/admin/wipe-inventory')
      // The wipe drops items; re-import
    }
    expect([200, 201]).toContain(impResp.status())

    // The imported item's card number is stable; look it up
    const items = await (await api.get('/api/items')).json()
    const imported = items.find(i => i.number === 'IMP-HIST-001')
    expect(imported).toBeTruthy()
    cleanup.push(`/api/items/${imported.id}`)

    // History must include an «issued» event for the recipient
    const history = await (await api.get(`/api/items/${imported.id}/history`)).json()
    const issued = history.find(e => e.kind === 'issued')
    expect(issued).toBeTruthy()
    expect(issued.recipient).toBe('IMP-HIST-RCPT')

    // Also clean up the auto-created recipient
    const rcpts = await (await api.get('/api/recipients')).json()
    const r = rcpts.find(rc => rc.callsign === 'IMP-HIST-RCPT')
    if (r) cleanup.push(`/api/recipients/${r.id}`)
  })

  test('splits.return_split writes returned_by (surfaces via /history actor)', async () => {
    // Non-serial item to exercise the standard splits UI path
    const tag = `hs-nb-${Date.now()}`
    const item = await postJson(api, '/api/items', {
      number: `HNB-${tag}`, name: `NB ${tag}`,
      unit_of_measure: 'шт', price: 50, quantity: 5, is_official: false,
    })
    cleanup.push(`/api/items/${item.id}`)
    const r = await makeRecipient('h-nb')

    const s = await postJson(api, `/api/items/${item.id}/splits`, { recipient_id: r.id, qty: 2 })
    const ret = await api.post(`/api/items/${item.id}/splits/${s.id}/return`, {})
    expect(ret.status()).toBe(200)

    const history = await (await api.get(`/api/items/${item.id}/history`)).json()
    const returnedEvent = history.find(e => e.kind === 'returned' && e.source === 'split')
    expect(returnedEvent).toBeTruthy()
    // actor should be populated (the admin who called the API)
    expect(returnedEvent.actor).toBeTruthy()
  })
})
