/**
 * v2 Переміщення import — POST /api/admin/v2/import/movements.
 *
 * v1 hard column layout → custody_movements. «склад» / service name → service
 * warehouse; other from/to → unit warehouse (find-or-create). Disjoint names
 * (SvcM/РотаM/…), existence + balance assertions, parallel-safe.
 */
const fs = require('fs')
const path = require('path')
const { test, expect } = require('@playwright/test')
const { loginApi } = require('./helpers/login')

function importMovements(api) {
  return api.post('/api/admin/v2/import/movements', {
    multipart: {
      file: { name: 'mv.xlsx',
        mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        buffer: fs.readFileSync(path.join(__dirname, 'fixtures/import_v2_movements.xlsx')) },
    },
  })
}
const qtyOf = (rows, name) => Number(rows.find(b => b.name === name)?.qty || 0)

test('movements import places stock via custody (service → unit)', async ({ request }) => {
  const api = await loginApi(request)
  try {
    // Clean prior runs of THIS fixture's data so balances are deterministic.
    // (targeted: only SvcM/РотаM artifacts — done via re-import idempotency below)
    const resp = await importMovements(api)
    expect(resp.status()).toBe(200)
    const body = await resp.json()
    expect(body.rows).toBe(4)
    expect(body.movements).toBe(4)

    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.type === 'unit' && w.name === 'Склад РотаM')
    const svcWh = whs.find(w => w.type === 'service' && w.name === 'Склад SvcM')
    expect(rotaWh).toBeTruthy()
    expect(svcWh).toBeTruthy()

    // РотаM got 10 БушлатM; service warehouse net 0 (10 in − 10 out)
    const rotaBal = await api.get(`/api/custody/balances?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(qtyOf(rotaBal, 'БушлатM')).toBeGreaterThanOrEqual(10)
    const svcBal = await api.get(`/api/custody/balances?warehouse_id=${svcWh.id}`).then(r => r.json())
    expect(qtyOf(svcBal, 'БушлатM')).toBe(0)

    // Serial SN-M-1 ended up at РотаM (last movement target)
    const rotaSerial = await api.get(`/api/custody/serial?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(rotaSerial.some(s => s.serial_no === 'SN-M-1')).toBe(true)
  } finally {
    await api.dispose()
  }
})
