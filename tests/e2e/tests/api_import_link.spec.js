/**
 * Items «№» ↔ Переміщення «Поле 12» (card_number) linking.
 * Items creates a serial instance with card_number; the movements import
 * matches that instance by card number (no duplicate) and places it, storing
 * the накладна number on the movement.
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

test('card number links Items instance to a Переміщення movement', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Catalog: one serial with card CARD-LNK-1
    const it = await up(api, '/api/admin/v2/import/items', 'import_v2_link_items.xlsx').then(r => r.json())
    expect(it.rows).toBe(1)

    const noms = await api.get('/api/nomenclature').then(r => r.json())
    const nom = noms.find(n => n.name === 'РаціяLnk')
    expect(nom).toBeTruthy()
    let insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts).toHaveLength(1)
    expect(insts[0].card_number).toBe('CARD-LNK-1')
    expect(insts[0].current_warehouse_id).toBeNull()   // catalog places nothing

    // Movements: same card → must match the SAME instance (no new one)
    const mv = await up(api, '/api/admin/v2/import/movements', 'import_v2_link_mv.xlsx').then(r => r.json())
    expect(mv.movements).toBe(1)
    expect(mv.instances_created).toBe(0)               // matched by card, not created

    insts = await api.get(`/api/nomenclature/${nom.id}/instances`).then(r => r.json())
    expect(insts).toHaveLength(1)                        // still one instance
    expect(insts[0].current_warehouse_id).not.toBeNull()// now placed by the movement

    // Movement carries the накладна number + card number
    const movements = await api.get('/api/custody/movements').then(r => r.json())
    const ours = movements.find(m => m.instance_id === insts[0].id)
    expect(ours).toBeTruthy()
    expect(ours.doc_number).toBe('НАКЛ-777')
    expect(ours.card_number).toBe('CARD-LNK-1')
  } finally {
    await api.dispose()
  }
})
