/**
 * Захисні межі: підбір пароля стримується, а імпорт не приймає «важкі» файли.
 */
const { test, expect } = require('@playwright/test')
const { request: pwRequest } = require('@playwright/test')
const { API, loginApi } = require('./helpers/login')

test('login throttles repeated failures per username', async ({ request }) => {
  const admin = await loginApi(request)
  const S = Date.now()
  const username = `brute-${S}`
  await admin.post('/api/users', { data: { username, password: 'correct-horse', role: 'service' } })
  await admin.dispose()

  const anon = await pwRequest.newContext({ baseURL: API })
  try {
    const badLogin = () => anon.post('/api/auth/login', {
      form: { username, password: 'wrong' }, failOnStatusCode: false })

    for (let i = 0; i < 10; i++) expect((await badLogin()).status()).toBe(401)
    expect((await badLogin()).status()).toBe(429)        // 11-та — стоп

    // Інший користувач не постраждав (лічильник — на пару логін+IP)
    const other = await anon.post('/api/auth/login', {
      form: { username: 'admin', password: 'admin123' }, failOnStatusCode: false })
    expect(other.status()).toBe(200)
  } finally {
    await anon.dispose()
  }
})

test('import rejects a non-xlsx and an oversized upload', async ({ request }) => {
  const api = await loginApi(request)
  try {
    const send = (buffer, name = 'f.xlsx') => api.post('/api/admin/v2/import/items', {
      multipart: { file: { name, mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer } },
      failOnStatusCode: false,
    })

    const notZip = await send(Buffer.from('це не xlsx, а звичайний текст'))
    expect(notZip.status()).toBe(400)
    expect(await notZip.text()).toContain('XLSX')

    const huge = await send(Buffer.alloc(16 * 1024 * 1024, 1))   // > 15 МБ
    expect(huge.status()).toBe(400)
    expect(await huge.text()).toContain('МБ')
  } finally {
    await api.dispose()
  }
})
