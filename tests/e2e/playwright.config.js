const { defineConfig } = require('@playwright/test')

module.exports = defineConfig({
  testDir: './tests',
  timeout: 30_000,
  retries: 1,
  reporter: [['list'], ['html', { open: 'never', outputFolder: '/results' }]],
  use: {
    baseURL: 'http://frontend',
    headless: true,
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
})
