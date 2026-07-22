/**
 * v2 nomenclature API — типи майна + серійні екземпляри.
 *
 * Covers Phase 2: nomenclature CRUD, instances only for is_serialized,
 * serial_no uniqueness, guard against demoting serialized-with-instances.
 */
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

test.describe('v2 nomenclature API', () => {
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

  async function makeService(tag) {
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    cleanup.push(`/api/settings/services/${svc.id}`)
    return svc
  }

  test('nomenclature requires a valid service', async () => {
    const resp = await api.post('/api/nomenclature', {
      data: { name: 'Бушлат', service_id: 999999, is_serialized: false },
    })
    expect(resp.status()).toBe(400)
  })

  test('non-serial nomenclature rejects instances', async () => {
    const tag = `n-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await makeService(tag)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `Бушлат ${tag}`, service_id: svc.id, is_serialized: false,
      unit_of_measure: 'шт', price: 500,
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    const resp = await api.post(`/api/nomenclature/${nom.id}/instances`, {
      data: { serial_no: `SN-${tag}` },
    })
    expect(resp.status()).toBe(400)
  })

  test('serial nomenclature: add instances, serial_no unique, is_official carried', async () => {
    const tag = `s-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await makeService(tag)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `АК-74 ${tag}`, service_id: svc.id, is_serialized: true, unit_of_measure: 'шт',
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)

    const i1 = await postJson(api, `/api/nomenclature/${nom.id}/instances`, {
      serial_no: `AK-${tag}-1`, is_official: true,
    })
    expect(i1.is_official).toBe(true)
    const i2 = await postJson(api, `/api/nomenclature/${nom.id}/instances`, {
      serial_no: `AK-${tag}-2`, is_official: false,   // волонтерський екземпляр
    })
    expect(i2.is_official).toBe(false)

    // Duplicate serial → 409
    const dup = await api.post(`/api/nomenclature/${nom.id}/instances`, {
      data: { serial_no: `AK-${tag}-1` },
    })
    expect(dup.status()).toBe(409)

    const list = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(list).toHaveLength(2)
  })

  test('cannot demote serialized nomenclature that has instances', async () => {
    const tag = `d-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await makeService(tag)
    const nom = await postJson(api, '/api/nomenclature', {
      name: `Рація ${tag}`, service_id: svc.id, is_serialized: true,
    })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    await postJson(api, `/api/nomenclature/${nom.id}/instances`, { serial_no: `R-${tag}` })

    const resp = await api.put(`/api/nomenclature/${nom.id}`, {
      data: { is_serialized: false },
    })
    expect(resp.status()).toBe(400)
  })
})
