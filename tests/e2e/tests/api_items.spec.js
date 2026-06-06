/**
 * Integration tests for the `issued_to_recipient_id` field on items.
 * Recipients are a separate, single-field (callsign) table — distinct
 * from persons (chiefs). See migration 008.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Items API · issued_to_recipient', () => {
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

  test('create + read + update + null-out issued_to_recipient_id', async () => {
    const tag = `${Date.now()}`

    const recipient = await postJson(api, '/api/recipients', { callsign: `Лис-${tag}` })
    cleanup.push(`/api/recipients/${recipient.id}`)

    const item = await postJson(api, '/api/items', {
      number: `T-${tag}`,
      name: `Test volunteer ${tag}`,
      unit_of_measure: 'шт',
      price: 100, quantity: 1, is_official: false,
      issued_to_recipient_id: recipient.id,
    })
    cleanup.push(`/api/items/${item.id}`)

    expect(item.issued_to_recipient_id).toBe(recipient.id)
    expect(item.issued_to_name).toBe(`Лис-${tag}`)

    const fetched = await api.get(`/api/items/${item.id}`).then(r => r.json())
    expect(fetched.issued_to_recipient_id).toBe(recipient.id)
    expect(fetched.issued_to_name).toBe(`Лис-${tag}`)

    const list = await api.get('/api/items').then(r => r.json())
    const listed = list.find(i => i.id === item.id)
    expect(listed.issued_to_recipient_id).toBe(recipient.id)
    expect(listed.issued_to_name).toBe(`Лис-${tag}`)

    const updated = await api.put(`/api/items/${item.id}`, { data: {
      issued_to_recipient_id: null,
    }}).then(r => r.json())
    expect(updated.issued_to_recipient_id).toBeNull()
    expect(updated.issued_to_name).toBeNull()
  })

  test('deleting the recipient SET NULLs items.issued_to_recipient_id', async () => {
    const tag = `${Date.now()}`
    const recipient = await postJson(api, '/api/recipients', { callsign: `Del-${tag}` })

    const item = await postJson(api, '/api/items', {
      number: `D-${tag}`,
      name: `Test deletion ${tag}`,
      unit_of_measure: 'шт', price: 1, quantity: 1, is_official: false,
      issued_to_recipient_id: recipient.id,
    })
    cleanup.push(`/api/items/${item.id}`)

    expect(item.issued_to_recipient_id).toBe(recipient.id)

    const delResp = await api.delete(`/api/recipients/${recipient.id}`)
    expect([204, 200]).toContain(delResp.status())

    const fetched = await api.get(`/api/items/${item.id}`).then(r => r.json())
    expect(fetched.issued_to_recipient_id).toBeNull()
    expect(fetched.issued_to_name).toBeNull()
  })
})
