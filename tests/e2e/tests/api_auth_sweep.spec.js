/**
 * Безпека: жоден API-маршрут не відповідає без токена.
 *
 * Проходить по OpenAPI-схемі й б'є КОЖЕН маршрут без заголовка Authorization —
 * очікує 401/403. ACL-скоупи писались руками по роутерах, тож цей тест ловить
 * забутий `Depends(get_current_user)` у новому ендпоінті назавжди.
 */
const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { API, loginApi } = require('./helpers/login')

// Публічні за призначенням: логін і health-check.
const PUBLIC = [
  ['post', '/api/auth/login'],
  ['get', '/api/health'],
]

// Тільки для admin — не-адмін має отримати 403 (перевіряємо окремо нижче).
const ADMIN_ONLY = [
  ['get', '/api/users'],
  ['get', '/api/audit'],
  ['post', '/api/structure/units'],
  ['post', '/api/structure/mvo'],
  ['post', '/api/structure/storage-points'],
]

const isPublic = (m, p) => PUBLIC.some(([pm, pp]) => pm === m && pp === p)
// {id} → 1: до звернення в БД справа не доходить, авторизація відсікає раніше.
const concrete = (p) => p.replace(/\{[^}]+\}/g, '1')

test('every API route rejects an unauthenticated request', async ({ request }) => {
  const api = await loginApi(request)
  const spec = await api.get('/openapi.json').then(r => r.json())
  await api.dispose()

  const anon = await pwRequest.newContext({ baseURL: API })
  const leaks = []
  let checked = 0
  try {
    for (const [path, methods] of Object.entries(spec.paths)) {
      if (!path.startsWith('/api/')) continue
      for (const method of Object.keys(methods)) {
        if (!['get', 'post', 'put', 'delete', 'patch'].includes(method)) continue
        if (isPublic(method, path)) continue
        checked += 1
        const resp = await anon[method](concrete(path), { failOnStatusCode: false })
        if (![401, 403].includes(resp.status())) {
          leaks.push(`${method.toUpperCase()} ${path} → ${resp.status()}`)
        }
      }
    }
    expect(leaks, `маршрути без перевірки токена:\n${leaks.join('\n')}`).toEqual([])
    expect(checked, 'схема не зчиталась — тест пройшов би вхолосту').toBeGreaterThan(40)
  } finally {
    await anon.dispose()
  }
})

test('admin-only routes reject a service-role user', async ({ request }) => {
  const admin = await loginApi(request)
  const S = Date.now()
  const svc = await admin.post('/api/settings/services', { data: { name: `SweepSvc ${S}` } }).then(r => r.json())
  const username = `sweep-${S}`
  await admin.post('/api/users', { data: {
    username, password: 'test1234', role: 'service', service_id: svc.id } })
  await admin.dispose()

  const user = await loginApi(request, { user: username, pass: 'test1234' })
  try {
    for (const [method, path] of ADMIN_ONLY) {
      const resp = await user[method](path, { data: {}, failOnStatusCode: false })
      expect(resp.status(), `${method.toUpperCase()} ${path} має бути 403 для service-юзера`).toBe(403)
    }
  } finally {
    await user.dispose()
  }
})
