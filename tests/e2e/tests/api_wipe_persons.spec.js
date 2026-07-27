/**
 * «Очистити людей» (Імпорт) — wipes the persons list for a fresh re-import.
 *   - blocked while assignments still exist (clear inventory first);
 *   - keeps persons linked to a user login (МВО auto-scope would otherwise break);
 *   - deletes the rest and reports counts.
 *
 * ❗ Destructive — removes (almost) all persons. Gated behind RUN_WIPE_TEST so it
 * never clobbers other specs. Enable on the isolated stack:
 *   RUN_WIPE_TEST=1 (passed into the playwright container) + scripts/e2e.sh …
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

function up(api, url, fixture) {
  return api.post(url, {
    multipart: {
      file: { name: 'f.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        buffer: fs.readFileSync(path.join(__dirname, 'fixtures', fixture)) },
    },
  })
}

test('wipe-persons: guarded by assignments, keeps user-linked, deletes rest', async ({ request }) => {
  test.skip(!process.env.RUN_WIPE_TEST, 'set RUN_WIPE_TEST=1 to enable (destructive)')

  const api = await loginApi(request)
  try {
    // Seed assignments via the 3-step import (creates «Петренко» + 2 issuances)
    await up(api, '/api/admin/v2/import/items', 'import_v2_asg_items.xlsx')
    await up(api, '/api/admin/v2/import/movements', 'import_v2_asg_mv.xlsx')
    await up(api, '/api/admin/v2/import/assignments', 'import_v2_asg_items.xlsx')

    // Guard: assignments present → wipe-persons is blocked
    const blocked = await api.post('/api/admin/v2/wipe-persons')
    expect(blocked.status()).toBe(400)
    expect((await blocked.json()).detail).toContain('інвентар')

    // Clear inventory → assignments gone
    expect((await api.post('/api/admin/v2/wipe')).ok()).toBe(true)

    // A person linked to a user login (must survive) + a plain person (must go)
    const keep = await api.post('/api/settings/persons', { data: { last_name: 'ЗберегтиLinked' } }).then(r => r.json())
    await api.post('/api/users', { data: {
      username: `keep-${Date.now()}`, password: 'test1234', role: 'mvo', person_id: keep.id,
    } }).then(r => expect(r.ok()).toBe(true))
    const drop = await api.post('/api/settings/persons', { data: { last_name: 'ВидалитиPlain' } }).then(r => r.json())

    // Wipe persons
    const resp = await api.post('/api/admin/v2/wipe-persons')
    expect(resp.ok()).toBe(true)
    const body = await resp.json()
    expect(body.deleted_persons).toBeGreaterThanOrEqual(1)
    expect(body.kept_linked_to_users).toBeGreaterThanOrEqual(1)

    // Linked person survives; plain one and the imported «Петренко» are gone
    const persons = await api.get('/api/settings/persons').then(r => r.json())
    expect(persons.some(p => p.id === keep.id)).toBe(true)
    expect(persons.some(p => p.id === drop.id)).toBe(false)
    expect(persons.some(p => p.last_name === 'Петренко')).toBe(false)
  } finally {
    await api.dispose()
  }
})
