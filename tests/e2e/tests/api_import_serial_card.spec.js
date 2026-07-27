/**
 * Regression: a SERIALIZED card whose Переміщення row has only a card number
 * (Поле 12) and no serial in column P must still place the instance (matched
 * by card), NOT create a phantom non-serial movement. Otherwise the catalog
 * shows a quantity but «Де знаходиться» is empty.
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

test('serialized card placed by card-only movement row (no serial column)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Catalog: serialized item АнтенаSC with card SCARD-1 (unplaced)
    const it = await up(api, '/api/admin/v2/import/items', 'import_v2_serialcard_items.xlsx').then(r => r.json())
    expect(it.rows).toBe(1)

    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const nom = noms.find(n => n.name === 'АнтенаSC')
    expect(nom).toBeTruthy()
    expect(nom.is_serialized).toBe(true)
    let insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts).toHaveLength(1)
    expect(insts[0].card_number).toBe('SCARD-1')

    // Movement row has the card but NO serial in column P → must match by card
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_serialcard_mv.xlsx').then(r => r.json())
    expect(mv.movements).toBe(1)
    expect(mv.instances_created).toBe(0)        // matched existing instance, not created

    // Instance is now placed (this is what «Де знаходиться» reads)
    insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts).toHaveLength(1)
    expect(insts[0].current_warehouse_id).not.toBeNull()

    // The movement is a SERIAL movement (instance_id set), not a phantom non-serial one
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    const forNom = movements.filter(m => m.nomenclature_id === nom.id)
    expect(forNom.every(m => m.instance_id != null)).toBe(true)   // no instance_id=null phantom
    expect(forNom.some(m => m.instance_id === insts[0].id)).toBe(true)

    // «Де знаходиться» popup: serial instance shows up, total matches
    const where = await api.get(`/api/custody/where?nomenclature_id=${nom.id}`).then(r => r.json())
    expect(where.is_serialized).toBe(true)
    expect(where.serial.length).toBeGreaterThanOrEqual(1)
    expect(where.serial.some(s => s.serial_no === 'SERSC-1')).toBe(true)

    const totals = await api.get('/api/custody/totals').then(r => r.json())
    expect(Number(totals[String(nom.id)])).toBeGreaterThanOrEqual(1)
  } finally {
    await api.dispose()
  }
})
