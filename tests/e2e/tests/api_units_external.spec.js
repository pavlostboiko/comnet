/** units.is_external — create/read/update. */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson } = require('./helpers/seed')

test('unit is_external create + update', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const tag = `ext-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const u = await postJson(api, '/api/structure/units', { name: `Зовн ${tag}`, is_external: true })
    expect(u.is_external).toBe(true)

    const list = await api.get('/api/structure/units').then(r => r.json())
    expect(list.find(x => x.id === u.id).is_external).toBe(true)

    const upd = await api.put(`/api/structure/units/${u.id}`, { data: { is_external: false } }).then(r => r.json())
    expect(upd.is_external).toBe(false)

    await api.delete(`/api/structure/units/${u.id}`).catch(() => {})
  } finally { await api.dispose() }
})
