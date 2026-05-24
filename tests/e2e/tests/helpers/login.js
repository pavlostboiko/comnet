/**
 * Shared login + API-context helpers for Playwright tests.
 *
 *   const { uiLogin, loginApi } = require('./helpers/login')
 *   await uiLogin(page)              // browser-side: navigate, fill, click
 *   const api = await loginApi(request)  // API-only: returns auth-headers context
 */
const { request: pwRequest } = require('@playwright/test')

const URL  = process.env.APP_URL  || 'http://frontend'
const API  = process.env.API_URL  || 'http://backend:8000'
const USER = process.env.TEST_USER || 'admin'
const PASS = process.env.TEST_PASS || 'admin123'

async function uiLogin(page, { user = USER, pass = PASS } = {}) {
  await page.goto(`${URL}/login`)
  await page.fill('input[id="f-username"]', user)
  await page.fill('input[id="f-password"]', pass)
  await page.click('button.btn-login')
  await page.waitForURL(/\/items/)
}

async function getToken(requestContext, { user = USER, pass = PASS } = {}) {
  // OAuth2PasswordRequestForm expects form-encoded body
  const resp = await requestContext.post(`${API}/api/auth/login`, {
    form: { username: user, password: pass },
  })
  if (!resp.ok()) {
    throw new Error(`Login failed: ${resp.status()} ${await resp.text()}`)
  }
  const { access_token } = await resp.json()
  return access_token
}

async function loginApi(requestContext, opts = {}) {
  const token = await getToken(requestContext, opts)
  return await pwRequest.newContext({
    baseURL: API,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  })
}

module.exports = { URL, API, USER, PASS, uiLogin, getToken, loginApi }
