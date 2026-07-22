/**
 * v2 two-axis ACL — service (vertical) × mvo (horizontal) × admin.
 *
 * service бачить майно своєї служби в усіх складах; mvo — свій склад усіх служб.
 * Cross-write заборонено (403).
 */
const { test, expect, request: pwRequest } = require('@playwright/test')
const { loginApi } = require('./helpers/login')
const { postJson, bestEffortDelete } = require('./helpers/seed')

const API = process.env.API_URL || 'http://backend:8000'

test.describe('v2 ACL', () => {
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

  async function apiAs(request, username, password) {
    const login = await request.post(`${API}/api/auth/login`, { form: { username, password } })
    const token = (await login.json()).access_token
    return pwRequest.newContext({ baseURL: API, extraHTTPHeaders: { Authorization: `Bearer ${token}` } })
  }

  test('service sees only own-service balances; mvo only own warehouse; cross-write 403', async ({ request }) => {
    const tag = `acl-${Date.now()}-${Math.floor(Math.random() * 9999)}`

    // Two services with stock, one unit, its warehouse
    const svcA = await postJson(api, '/api/settings/services', { name: `СлужбаA ${tag}` })
    const svcB = await postJson(api, '/api/settings/services', { name: `СлужбаB ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`,
                 `/api/settings/services/${svcA.id}`, `/api/settings/services/${svcB.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const whA = whs.find(w => w.service_id === svcA.id)
    const unitWh = whs.find(w => w.unit_id === unit.id)

    const nomA = await postJson(api, '/api/nomenclature', { name: `A-нн ${tag}`, service_id: svcA.id, unit_of_measure: 'шт' })
    const nomB = await postJson(api, '/api/nomenclature', { name: `B-нн ${tag}`, service_id: svcB.id, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nomA.id}`, `/api/nomenclature/${nomB.id}`)

    // Put both services' stock into the unit warehouse (receipt to unit directly for test)
    for (const nom of [nomA, nomB]) {
      await postJson(api, '/api/custody/movements', {
        date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: unitWh.id, quantity: 5,
      })
    }

    // Users: service-A worker, mvo of the unit
    const svcUser = await postJson(api, '/api/users', {
      username: `svcA-${tag}`, password: 'pw-strong', role: 'service', service_id: svcA.id,
    })
    const mvoUser = await postJson(api, '/api/users', {
      username: `mvo-${tag}`, password: 'pw-strong', role: 'mvo', unit_id: unit.id, warehouse_id: unitWh.id,
    })
    cleanup.push(`/api/users/${svcUser.id}`, `/api/users/${mvoUser.id}`)

    // Service-A worker: balances at unit warehouse show ONLY service A's line
    const svcApi = await apiAs(request, `svcA-${tag}`, 'pw-strong')
    try {
      const bal = await svcApi.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
      expect(bal.find(b => b.nomenclature_id === nomA.id)).toBeTruthy()
      expect(bal.find(b => b.nomenclature_id === nomB.id)).toBeFalsy()

      // Service-A cannot create nomenclature for service B → 403
      const bad = await svcApi.post('/api/nomenclature', {
        data: { name: `sneaky ${tag}`, service_id: svcB.id, unit_of_measure: 'шт' },
      })
      expect(bad.status()).toBe(403)
    } finally {
      await svcApi.dispose()
    }

    // MVO: can read own warehouse, sees BOTH services' lines there
    const mvoApi = await apiAs(request, `mvo-${tag}`, 'pw-strong')
    try {
      const bal = await mvoApi.get(`/api/custody/balances?warehouse_id=${unitWh.id}`).then(r => r.json())
      expect(bal.find(b => b.nomenclature_id === nomA.id)).toBeTruthy()
      expect(bal.find(b => b.nomenclature_id === nomB.id)).toBeTruthy()

      // MVO reading a DIFFERENT warehouse (service A's) → 403
      const forbidden = await mvoApi.get(`/api/custody/balances?warehouse_id=${whA.id}`)
      expect(forbidden.status()).toBe(403)

      // MVO cannot create a movement OUT of a warehouse that isn't theirs → 403
      const badMove = await mvoApi.post('/api/custody/movements', {
        data: { date: '2026-07-02', type: 'transfer', nomenclature_id: nomA.id,
                from_warehouse_id: whA.id, to_warehouse_id: unitWh.id, quantity: 1 },
      })
      expect(badMove.status()).toBe(403)
    } finally {
      await mvoApi.dispose()
    }
  })

  test('service role cannot issue assignments (mvo-only action)', async ({ request }) => {
    const tag = `acl2-${Date.now()}-${Math.floor(Math.random() * 9999)}`
    const svc = await postJson(api, '/api/settings/services', { name: `Служба ${tag}` })
    const unit = await postJson(api, '/api/structure/units', { name: `Рота ${tag}` })
    cleanup.push(`/api/structure/units/${unit.id}`, `/api/settings/services/${svc.id}`)
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const unitWh = whs.find(w => w.unit_id === unit.id)
    const nom = await postJson(api, '/api/nomenclature', { name: `нн ${tag}`, service_id: svc.id, unit_of_measure: 'шт' })
    cleanup.push(`/api/nomenclature/${nom.id}`)
    await postJson(api, '/api/custody/movements', {
      date: '2026-07-01', type: 'receipt', nomenclature_id: nom.id, to_warehouse_id: unitWh.id, quantity: 5,
    })
    const person = await postJson(api, '/api/settings/persons', { first_name: 'Б', last_name: `Ц-${tag}`, unit_id: unit.id })
    cleanup.push(`/api/settings/persons/${person.id}`)
    const svcUser = await postJson(api, '/api/users', {
      username: `svc2-${tag}`, password: 'pw-strong', role: 'service', service_id: svc.id,
    })
    cleanup.push(`/api/users/${svcUser.id}`)

    const svcApi = await apiAs(request, `svc2-${tag}`, 'pw-strong')
    try {
      const resp = await svcApi.post('/api/assignments', {
        data: { warehouse_id: unitWh.id, person_id: person.id, nomenclature_id: nom.id, quantity: 1 },
      })
      expect(resp.status()).toBe(403)
    } finally {
      await svcApi.dispose()
    }
  })
})
