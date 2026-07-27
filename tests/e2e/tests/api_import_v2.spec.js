/**
 * v2 Items import — POST /api/admin/v2/import/items.
 *
 * Items = CATALOG only: nomenclature + serial instances. No custody placement,
 * no assignments (that's the Переміщення import + видача step). Fixture uses
 * disjoint names; assertions are existence-based so parallel re-runs are safe.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

function importFixture(api) {
  return api.post('/api/admin/v2/import/items', {
    multipart: {
      file: { name: 'import_v2_items.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        buffer: fs.readFileSync(path.join(__dirname, 'fixtures/import_v2_items.xlsx')) },
    },
  })
}

test('v2 items import = catalog only (nomenclature + serial instances, no custody)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const resp = await importFixture(api)
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.rows).toBe(3)
    // no movements/assignments fields — catalog import doesn't place anything
    expect(body.movements).toBeUndefined()
    expect(body.assignments).toBeUndefined()

    // Nomenclature exists for all three rows
    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const bushlat = noms.find(n => n.name === 'БушлатA')
    const ak = noms.find(n => n.name === 'АК-A')
    expect(bushlat).toBeTruthy()
    expect(ak).toBeTruthy()
    expect(ak.is_serialized).toBe(true)
    expect(bushlat.is_serialized).toBe(false)

    // Serial instance created but NOT placed on any warehouse
    const insts = await api.get(`/api/nomenclature/${ak.id}/instances`).then(r => r.json())
    const imp = insts.find(i => i.serial_no === 'AK-IMP-A')
    expect(imp).toBeTruthy()
    expect(imp.current_warehouse_id).toBeNull()
  } finally {
    await api.dispose()
  }
})

test('re-import does not duplicate nomenclature (find-or-create)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    await importFixture(api)
    const n1 = (await api.get('/api/nomenclature').then(r => r.json())).filter(n => n.name === 'БушлатA').length
    await importFixture(api)
    const n2 = (await api.get('/api/nomenclature').then(r => r.json())).filter(n => n.name === 'БушлатA').length
    expect(n2).toBe(n1)  // no duplicate
  } finally {
    await api.dispose()
  }
})
