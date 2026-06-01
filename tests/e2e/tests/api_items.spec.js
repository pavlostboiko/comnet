/**
 * Integration tests for /api/items with the new `issued_to_person_id`
 * field. Covers the simple «issued to a person» pointer used for serial
 * items and volunteer items added directly via the items dictionary.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('Items API · issued_to', () => {
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

  test('create + read + update + null-out issued_to_person_id', async () => {
    const tag = `${Date.now()}`

    // Seed a person
    const person = await postJson(api, '/api/settings/persons', {
      first_name: 'Ivan', last_name: 'Issued', position: 'Холдер', unit: `U-${tag}`,
    })
    cleanup.push(`/api/settings/persons/${person.id}`)

    // Create item already issued to that person
    const item = await postJson(api, '/api/items', {
      number: `T-${tag}`,
      name: `Test volunteer ${tag}`,
      unit_of_measure: 'шт',
      price: 100, quantity: 1, is_official: false,
      issued_to_person_id: person.id,
    })
    cleanup.push(`/api/items/${item.id}`)

    expect(item.issued_to_person_id).toBe(person.id)
    expect(item.issued_to_name).toContain('Ivan')

    // Read endpoint also surfaces both
    const fetched = await api.get(`/api/items/${item.id}`).then(r => r.json())
    expect(fetched.issued_to_person_id).toBe(person.id)
    expect(fetched.issued_to_name).toContain('Ivan')

    // List endpoint also returns it (with the same person)
    const list = await api.get('/api/items').then(r => r.json())
    const listed = list.find(i => i.id === item.id)
    expect(listed.issued_to_person_id).toBe(person.id)
    expect(listed.issued_to_name).toContain('Ivan')

    // Null it out via PUT
    const updated = await api.put(`/api/items/${item.id}`, { data: {
      issued_to_person_id: null,
    }}).then(r => r.json())
    expect(updated.issued_to_person_id).toBeNull()
    expect(updated.issued_to_name).toBeNull()
  })

  test('deleting the person SET NULLs the FK on the item', async () => {
    const tag = `${Date.now()}`

    const person = await postJson(api, '/api/settings/persons', {
      first_name: 'Temp', last_name: 'Holder', unit: `U-${tag}`,
    })
    const item = await postJson(api, '/api/items', {
      number: `D-${tag}`,
      name: `Test deletion ${tag}`,
      unit_of_measure: 'шт', price: 1, quantity: 1, is_official: false,
      issued_to_person_id: person.id,
    })
    cleanup.push(`/api/items/${item.id}`)
    // NB: person deleted as part of the test (not via cleanup)

    expect(item.issued_to_person_id).toBe(person.id)

    // Delete the person
    const delResp = await api.delete(`/api/settings/persons/${person.id}`)
    expect([204, 200]).toContain(delResp.status())

    // Re-fetch item: FK is now NULL (ON DELETE SET NULL)
    const fetched = await api.get(`/api/items/${item.id}`).then(r => r.json())
    expect(fetched.issued_to_person_id).toBeNull()
    expect(fetched.issued_to_name).toBeNull()
  })
})
