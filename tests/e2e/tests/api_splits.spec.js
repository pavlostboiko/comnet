/**
 * /api/items/{id}/splits — per-recipient issuance ledger.
 *
 * Covers: create reduces free, overissue rejected, return restores free,
 * delete active split also restores free (delete of returned keeps as is).
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Item splits API', () => {
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

  async function makeItem(qty = 10) {
    const tag = `sp-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const item = await postJson(api, '/api/items', {
      number: `S-${tag}`, name: `Test ${tag}`,
      unit_of_measure: 'шт', price: 10, quantity: qty, is_official: false,
    })
    cleanup.push(`/api/items/${item.id}`)
    return item
  }
  async function makeRecipient(name) {
    const r = await postJson(api, '/api/recipients', { callsign: `${name}-${Date.now()}` })
    cleanup.push(`/api/recipients/${r.id}`)
    return r
  }

  test('create split reduces free; overissue rejected', async () => {
    const item = await makeItem(10)
    const rA   = await makeRecipient('A')

    const s1 = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: rA.id, qty: 4, notes: 'first',
    })
    expect(Number(s1.qty)).toBe(4)
    expect(s1.is_active).toBe(true)

    // Try to overissue (4 + 7 > 10)
    const overResp = await api.post(`/api/items/${item.id}/splits`, { data: {
      recipient_id: rA.id, qty: 7,
    }})
    expect(overResp.status()).toBe(400)

    // But 4 + 6 = 10 exactly is fine
    const s2 = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: rA.id, qty: 6,
    })
    expect(Number(s2.qty)).toBe(6)

    // One more of any qty should fail (0 free)
    const nogoResp = await api.post(`/api/items/${item.id}/splits`, { data: {
      recipient_id: rA.id, qty: 1,
    }})
    expect(nogoResp.status()).toBe(400)
  })

  test('return restores free; delete of active split also restores', async () => {
    const item = await makeItem(5)
    const r    = await makeRecipient('R')

    const s = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: r.id, qty: 5,
    })
    // Free = 0, can't add more
    let resp = await api.post(`/api/items/${item.id}/splits`, { data: {
      recipient_id: r.id, qty: 1,
    }})
    expect(resp.status()).toBe(400)

    // Return the split
    const returned = await api.post(`/api/items/${item.id}/splits/${s.id}/return`, { data: {} })
      .then(r => r.json())
    expect(returned.is_active).toBe(false)
    expect(returned.returned_at).toBeTruthy()

    // Free = 5 again, can add
    const s2 = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: r.id, qty: 5,
    })
    expect(s2.is_active).toBe(true)

    // Delete the active one → free again
    resp = await api.delete(`/api/items/${item.id}/splits/${s2.id}`)
    expect(resp.status()).toBe(204)

    const listAfter = await api.get(`/api/items/${item.id}/splits`).then(r => r.json())
    expect(listAfter.filter(x => x.is_active).length).toBe(0)
  })

  test('cannot return an already-returned split', async () => {
    const item = await makeItem(1)
    const r    = await makeRecipient('X')
    const s = await postJson(api, `/api/items/${item.id}/splits`, {
      recipient_id: r.id, qty: 1,
    })
    await api.post(`/api/items/${item.id}/splits/${s.id}/return`)
    const dupe = await api.post(`/api/items/${item.id}/splits/${s.id}/return`)
    expect(dupe.status()).toBe(400)
  })
})
