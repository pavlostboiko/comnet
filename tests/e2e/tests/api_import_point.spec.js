/**
 * Імпорт видач читає колонку «Точка»: значення застосовується незалежно від
 * того, що в «Де» — і для виданого особі, і для того, що лежить на складі.
 * Точки, яких ще немає, створюються для складу цього рядка.
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

test('assignments import applies the «Точка» column', async ({ request }) => {
  const api = await loginApi(request)
  try {
    expect((await up(api, '/api/admin/v2/import/items', 'import_v2_point_items.xlsx')).status()).toBe(200)
    expect((await up(api, '/api/admin/v2/import/movements', 'import_v2_point_mv.xlsx')).status()).toBe(200)
    await api.post('/api/settings/persons', { data: { last_name: 'Точкенко' } })

    const res = await up(api, '/api/admin/v2/import/assignments', 'import_v2_point_items.xlsx')
    expect(res.status()).toBe(200)
    const body = await res.json()
    expect(body.points_created).toBe(2)        // «Намет 1» + «Бокс 2» на складі роти
    expect(body.points_set).toBe(4)            // усі рядки з точкою, крім «Рукавиці»
    expect(body.assignments).toBe(3)           // три рядки з прізвищем

    const units = await api.get('/api/structure/units').then(r => r.json())
    const rota = units.find(u => u.name === 'РотаPT')
    const whs = await api.get('/api/structure/warehouses').then(r => r.json())
    const rotaWh = whs.find(w => w.unit_id === rota.id)

    // Точки заведені саме для складу підрозділу
    const points = await api.get(`/api/structure/storage-points?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(points.map(p => p.name).sort()).toEqual(['Бокс 2', 'Намет 1'])
    const byName = Object.fromEntries(points.map(p => [p.name, p.id]))

    // Серійне: точка на екземплярі — і у виданого, і в того, що на складі
    const serial = await api.get(`/api/custody/serial?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(serial.find(s => s.serial_no === 'SER-PT-1').storage_point).toBe('Намет 1')
    expect(serial.find(s => s.serial_no === 'SER-PT-2').storage_point).toBe('Бокс 2')

    // Несерійне видане: точка на самій видачі; без «Точки» — порожньо
    const asg = await api.get(`/api/assignments?warehouse_id=${rotaWh.id}`).then(r => r.json())
    const kaska = asg.find(a => a.nomenclature_name === 'КаскаPT')
    expect(kaska.storage_point).toBe('Намет 1')
    expect(asg.find(a => a.nomenclature_name === 'РукавицяPT').storage_point_id).toBeNull()

    // Несерійне на складі: мітка (картка, склад)
    const bal = await api.get(`/api/custody/balances?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(bal.find(b => b.name === 'БушлатPT').storage_point).toBe('Бокс 2')

    // Зміни точок потрапили в загальну історію
    const feed = await api.get(`/api/custody/feed?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(feed.events.filter(e => e.kind === 'point')).toHaveLength(4)

    // Реімпорт: нових точок у довіднику не зʼявляється, наявні не переставляються.
    // (`points_set` > 0 на реімпорті — бо імпорт видач сам по собі не ідемпотентний
    // для несерійного: створює ДУБЛЬ видачі, і новій видачі теж ставиться точка.)
    const again = await up(api, '/api/admin/v2/import/assignments', 'import_v2_point_items.xlsx').then(r => r.json())
    expect(again.points_created).toBe(0)
    const pointsAfter = await api.get(`/api/structure/storage-points?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(pointsAfter.map(p => p.id).sort()).toEqual(points.map(p => p.id).sort())
    const serialAfter = await api.get(`/api/custody/serial?warehouse_id=${rotaWh.id}`).then(r => r.json())
    expect(serialAfter.find(s => s.serial_no === 'SER-PT-2').storage_point_id).toBe(byName['Бокс 2'])
  } finally {
    await api.dispose()
  }
})
