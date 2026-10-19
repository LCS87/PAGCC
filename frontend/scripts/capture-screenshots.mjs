/**
 * Captura screenshots reais da aplicação para a documentação.
 *
 * Requisitos:
 *   - API em http://127.0.0.1:8000 e frontend em http://127.0.0.1:5173 (ou APP_URL)
 *   - Edge/Chrome instalado, ou BROWSER_PATH apontando para o executável
 *   - `npm install` no frontend (playwright-core não baixa navegador)
 *
 * Uso: npm run screenshots
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from 'playwright-core'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..')
const output = path.join(root, 'docs', 'screenshots')
const baseUrl = process.env.APP_URL ?? 'http://127.0.0.1:5173'

const candidates = [
  process.env.BROWSER_PATH,
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  '/usr/bin/google-chrome',
  '/usr/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
].filter(Boolean)

const executablePath = candidates.find((candidate) => fs.existsSync(candidate))
if (!executablePath) {
  console.error('Navegador não encontrado. Defina BROWSER_PATH.')
  process.exit(1)
}

fs.mkdirSync(output, { recursive: true })

const browser = await chromium.launch({ executablePath, headless: true })
const context = await browser.newContext({
  viewport: { width: 1440, height: 940 },
  deviceScaleFactor: 1.5,
  locale: 'pt-BR',
  timezoneId: 'America/Fortaleza',
})
const page = await context.newPage()
const errors = []
page.on('pageerror', (error) => errors.push(`pageerror: ${error.message}`))
page.on('console', (message) => {
  if (message.type() === 'error') errors.push(`console: ${message.text()}`)
})

async function shot(name) {
  await page.waitForTimeout(1200)
  await page.screenshot({ path: path.join(output, name), fullPage: false })
  console.log(`ok ${name}`)
}

async function goto(pathname) {
  await page.goto(`${baseUrl}${pathname}`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(800)
}

// 1. Login
await goto('/login')
await shot('00-login.png')

// 2. Autenticação
await page.fill('input[type="email"]', 'gestor@clinicavida.example')
await page.fill('input[type="password"]', 'Clinic@2026')
await page.click('button[type="submit"]')
await page.waitForURL(`${baseUrl}/`, { timeout: 20000 })
await page.waitForTimeout(2500)

// 3. Dashboard (tema claro)
await shot('01-dashboard.png')

// 4. Tema escuro
await page.click('button[aria-label="Ativar tema escuro"]')
await page.waitForTimeout(800)
await shot('02-dashboard-dark.png')
await page.click('button[aria-label="Ativar tema claro"]')

// 5. Agenda
await goto('/agenda')
await shot('03-agenda.png')

// 6. Analytics
await goto('/analytics')
await shot('04-analytics.png')

// 7. Qualidade
await goto('/qualidade')
await shot('05-qualidade.png')

// 8. Profissional
await goto('/profissionais/1')
await shot('06-profissional.png')

// 9. Administração
await goto('/admin')
await shot('07-admin.png')

// 10. Mobile
await page.setViewportSize({ width: 390, height: 844 })
await goto('/')
await shot('08-mobile.png')

await browser.close()

if (errors.length) {
  console.error('\nErros de navegador encontrados:')
  for (const error of errors) console.error(`- ${error}`)
  process.exit(1)
}
console.log('\nScreenshots gerados em docs/screenshots.')
