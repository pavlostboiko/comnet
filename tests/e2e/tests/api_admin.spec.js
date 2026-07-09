/**
 * /api/admin endpoints — wipe-inventory + bulk import (items, movements).
 *
 * Builds a tiny in-memory XLSX with sheetjs-equivalent? — we don't have a
 * sheetjs dep. Instead the import endpoints are stress-tested against an
 * absent file (form validation) and the wipe endpoint is checked end-to-end
 * with a real seeded item/document/movement triplet.
 *
 * NB: a richer fixture-based import test belongs in pytest where openpyxl
 * is available; here we just guard the endpoint surface area.
 */
const { test, expect, request: pwRequest } = require('@playwright/test')
const { API, loginApi, getToken } = require('./helpers/login')
const { postJson, seedNakladnaContext, bestEffortDelete } = require('./helpers/seed')

test.describe('Admin API', () => {
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

  test('wipe-inventory removes items+documents+movements; persons survive', async () => {
    // ❗ Destructive — wipes the entire dev DB inventory. Other parallel API
    // tests would see their seeded rows vanish mid-test. Run with
    // RUN_WIPE_TEST=1 set on the playwright service (CI / dedicated cron).
    test.skip(!process.env.RUN_WIPE_TEST, 'set RUN_WIPE_TEST=1 to enable')

    // Seed: a person, an item, a signed doc (which creates a movement)
    const seed = await seedNakladnaContext(api, 'wipe')
    const doc = await postJson(api, '/api/documents', {
      operation: 'переміщення', form: 'накладна',
      doc_date: '2026-06-23',
      op_type_id: seed.opType.id,
      service_id: seed.service.id,
      sender_id: seed.sender.id,
      receiver_id: seed.receiver.id,
      fin_id: seed.fin.id,
      items: [{ item_id: seed.item.id, quantity: 1, qty_received: 1 }],
    })
    await api.post(`/api/documents/${doc.id}/sign`)

    // Sanity: dictionaries we expect to survive
    const personsBefore = await api.get('/api/settings/persons').then(r => r.json())
    const opTypesBefore = await api.get('/api/settings/op-types').then(r => r.json())
    expect(personsBefore.length).toBeGreaterThan(0)
    expect(opTypesBefore.length).toBeGreaterThan(0)

    const resp = await api.post('/api/admin/wipe-inventory')
    expect(resp.ok()).toBe(true)
    const body = await resp.json()
    expect(body.deleted).toHaveProperty('items')
    expect(body.deleted.items).toBeGreaterThanOrEqual(1)
    expect(body.deleted.movements).toBeGreaterThanOrEqual(1)
    expect(body.deleted.documents).toBeGreaterThanOrEqual(1)

    // Items / documents / movements gone
    const items     = await api.get('/api/items').then(r => r.json())
    const docs      = await api.get('/api/documents').then(r => r.json())
    const movements = await api.get('/api/movements').then(r => r.json())
    expect(items.length).toBe(0)
    expect(docs.length).toBe(0)
    expect(movements.length).toBe(0)

    // Dictionaries still here
    const personsAfter  = await api.get('/api/settings/persons').then(r => r.json())
    const opTypesAfter  = await api.get('/api/settings/op-types').then(r => r.json())
    expect(personsAfter.length).toBe(personsBefore.length)
    expect(opTypesAfter.length).toBe(opTypesBefore.length)

    // Cleanup pushed entries already gone — seed.cleanup tries to delete them
    // but bestEffortDelete swallows 404, so it's safe.
    cleanup.push(...seed.cleanup)
  })

  test('non-admin gets 403 on wipe-inventory', async ({ request }) => {
    // Create an operator-role user and login as them
    const username = `op-wipe-${Date.now()}`
    const password = 'op-pw'
    const op = await postJson(api, '/api/users', {
      username, password, role: 'operator', is_active: true,
    })
    cleanup.push(`/api/users/${op.id}`)

    const opToken = await getToken(request, { user: username, pass: password })
    const opApi = await pwRequest.newContext({
      baseURL: API,
      extraHTTPHeaders: { Authorization: `Bearer ${opToken}` },
    })
    try {
      const resp = await opApi.post('/api/admin/wipe-inventory')
      expect(resp.status()).toBe(403)
    } finally {
      await opApi.dispose()
    }
  })

  test('import/items without file returns 422', async () => {
    const resp = await api.post('/api/admin/import/items', { multipart: {} })
    expect([400, 422]).toContain(resp.status())
  })

  test('import/movements without file returns 422', async () => {
    const resp = await api.post('/api/admin/import/movements', { multipart: {} })
    expect([400, 422]).toContain(resp.status())
  })

  test('merge-nonserial-duplicates: preview + apply combines cards', async () => {
    const tag = `mg-${Date.now()}`

    // Seed 3 non-serial cards with the same merge key (name, price, category, unit)
    const a = await postJson(api, '/api/items', {
      number: `${tag}-01`, name: `Socks ${tag}`, unit_of_measure: 'шт',
      price: 10, quantity: 5, category: '1', is_official: false,
      notes: 'from batch A',
    })
    const b = await postJson(api, '/api/items', {
      number: `${tag}-02`, name: `Socks ${tag}`, unit_of_measure: 'шт',
      price: 10, quantity: 3, category: '1', is_official: false,
      notes: 'from batch B',
    })
    const c = await postJson(api, '/api/items', {
      number: `${tag}-03`, name: `Socks ${tag}`, unit_of_measure: 'шт',
      price: 10, quantity: 2, category: '1', is_official: false,
    })
    // A different card that shouldn't match (different price)
    const d = await postJson(api, '/api/items', {
      number: `${tag}-04`, name: `Socks ${tag}`, unit_of_measure: 'шт',
      price: 99, quantity: 1, category: '1', is_official: false,
    })
    cleanup.push(`/api/items/${a.id}`, `/api/items/${b.id}`, `/api/items/${c.id}`, `/api/items/${d.id}`)

    // Preview should find one group of 3 → 2 cards to remove (winner stays)
    const preview = await api.get('/api/admin/merge-nonserial-duplicates/preview')
      .then(r => r.json())
    const ourGroup = preview.groups.find(g => g.winner_number === `${tag}-01`)
    expect(ourGroup).toBeTruthy()
    expect(ourGroup.cards_count).toBe(3)
    expect(ourGroup.loser_numbers).toEqual([`${tag}-02`, `${tag}-03`])

    // Apply
    const result = await api.post('/api/admin/merge-nonserial-duplicates').then(r => r.json())
    expect(result.merged_groups).toBeGreaterThanOrEqual(1)
    expect(result.removed_cards).toBeGreaterThanOrEqual(2)

    // Winner survives with summed quantity + merged notes
    const winner = await api.get(`/api/items/${a.id}`).then(r => r.json())
    expect(Number(winner.quantity)).toBe(10)   // 5 + 3 + 2
    expect(winner.notes).toContain('from batch A')
    expect(winner.notes).toContain('from batch B')

    // Losers gone
    const bResp = await api.get(`/api/items/${b.id}`)
    expect(bResp.status()).toBe(404)
    const cResp = await api.get(`/api/items/${c.id}`)
    expect(cResp.status()).toBe(404)

    // Different-price card untouched
    const other = await api.get(`/api/items/${d.id}`).then(r => r.json())
    expect(Number(other.quantity)).toBe(1)

    // Cleanup already-removed pushed entries — bestEffort swallows 404s
  })
})
