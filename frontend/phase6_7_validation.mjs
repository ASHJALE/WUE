import { spawn, spawnSync } from 'node:child_process'
import { existsSync } from 'node:fs'
import { readFile, readdir } from 'node:fs/promises'
import net from 'node:net'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const projectDir = path.dirname(frontendDir)

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function run(command, args, cwd = frontendDir) {
  const result = spawnSync(command, args, { cwd, encoding: 'utf8', shell: process.platform === 'win32' })
  if (result.status !== 0) throw new Error(`${command} failed:\n${result.stdout}\n${result.stderr}`)
  return `${result.stdout}${result.stderr}`
}

async function source(relativePath) {
  return readFile(path.join(frontendDir, relativePath), 'utf8')
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try { if ((await fetch(url)).ok) return } catch { /* Vite may still be starting. */ }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

async function isPortOpen(port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host: '127.0.0.1', port })
    socket.setTimeout(500)
    socket.once('connect', () => { socket.destroy(); resolve(true) })
    socket.once('timeout', () => { socket.destroy(); resolve(false) })
    socket.once('error', () => resolve(false))
  })
}

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Production build did not succeed.')
assert(existsSync(path.join(frontendDir, 'dist/index.html')), 'Production index was not created.')
console.log('NPM_BUILD_OK=True')

const feedback = await source('src/components/AppFeedback.jsx')
const styles = await source('src/styles/app.css')
const routes = await source('src/routes/AppRoutes.jsx')
const layout = await source('src/layouts/MainLayout.jsx')
const navbar = await source('src/components/Navbar.jsx')
const titles = await source('src/components/RouteTitle.jsx')
const index = await source('index.html')
const errors = await source('src/services/apiErrors.js')
const client = await source('src/api/client.js')

for (const component of ['LoadingState', 'ErrorAlert', 'EmptyState']) {
  assert(feedback.includes(`function ${component}`), `${component} is missing.`)
}
assert(styles.includes('--wue-forest') && styles.includes('--wue-radius'), 'Shared theme tokens are missing.')
assert(styles.includes('@media (max-width: 575.98px)') && styles.includes('.table-responsive'), 'Responsive rules are missing.')
assert(styles.includes(':focus-visible') && styles.includes('prefers-reduced-motion'), 'Accessibility motion/focus styles are missing.')
assert(layout.includes('skip-link') && layout.includes('id="main-content"'), 'Skip navigation is missing.')
assert(navbar.includes('isActive ? \' active\'') && navbar.includes('aria-label="Main navigation"'), 'Active accessible navigation is missing.')
assert(routes.includes('lazy(() => import(') && routes.includes('<Suspense'), 'Route-level production code splitting is missing.')
assert(titles.includes('document.title') && index.includes('wue-mark.svg') && index.includes('theme-color'), 'Brand metadata is incomplete.')
for (const status of ['401:', '403:', '404:', 'status >= 500']) {
  assert(errors.includes(status), `Friendly HTTP handling for ${status} is missing.`)
}
assert(errors.includes("code === 'ECONNABORTED'") && client.includes('timeout: 15000'), 'Timeout handling is incomplete.')
console.log('STATIC_UX_AUDIT_OK=True')

const pageFiles = (await readdir(path.join(frontendDir, 'src/pages'))).filter((name) => name.endsWith('.jsx'))
const allPageSource = (await Promise.all(pageFiles.map((name) => source(`src/pages/${name}`)))).join('\n')
assert(allPageSource.includes('<LoadingState') && allPageSource.includes('<ErrorAlert') && allPageSource.includes('<EmptyState'), 'Shared feedback states are not adopted.')
assert(!allPageSource.includes('console.log('), 'Debug logging remains in a page.')
assert(!existsSync(path.join(frontendDir, 'src/components/PagePlaceholder.jsx')), 'Dead placeholder component remains.')
console.log('PRODUCTION_CLEANUP_OK=True')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { LoadingState, ErrorAlert, EmptyState } = await viteSsr.ssrLoadModule('/src/components/AppFeedback.jsx')
  const loadingHtml = renderToString(React.createElement(LoadingState, { cards: 2, label: 'Loading validation data' }))
  const errorHtml = renderToString(React.createElement(ErrorAlert, { message: 'Network unavailable', onRetry: () => {} }))
  const emptyHtml = renderToString(React.createElement(MemoryRouter, null, React.createElement(EmptyState, {
    title: 'No records', description: 'Create the first record.', action: React.createElement('a', { href: '/new' }, 'Create'),
  })))
  assert(loadingHtml.includes('aria-busy="true"') && loadingHtml.includes('placeholder-glow'), 'Loading skeleton is inaccessible or missing.')
  assert(errorHtml.includes('role="alert"') && errorHtml.includes('Try again'), 'Reusable error/retry state failed to render.')
  assert(emptyHtml.includes('No records') && emptyHtml.includes('Create'), 'Reusable actionable empty state failed to render.')
} finally { await viteSsr.close() }
console.log('FEEDBACK_RENDER_OK=True')

assert(run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim() === '', 'Backend changed.')
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'Migration changed.')
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')

assert(!(await isPortOpen(5173)), 'Port 5173 was already occupied before validation.')
let viteErrors = ''
const viteProcess = spawn(process.execPath, ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], {
  cwd: frontendDir, stdio: ['ignore', 'ignore', 'pipe'],
})
viteProcess.stderr.on('data', (chunk) => { viteErrors += chunk.toString() })
try {
  await waitForServer('http://127.0.0.1:5173/')
  for (const route of ['/', '/login', '/register', '/dashboard', '/estimates/1/bom', '/quotations/1']) {
    const response = await fetch(`http://127.0.0.1:5173${route}`)
    assert(response.status === 200 && (await response.text()).includes('<div id="root"></div>'), `${route} was not served.`)
  }
} finally {
  viteProcess.kill()
  await new Promise((resolve) => viteProcess.once('exit', resolve))
}
assert(!viteErrors.trim(), `Vite reported errors:\n${viteErrors}`)
await new Promise((resolve) => setTimeout(resolve, 300))
assert(!(await isPortOpen(5173)), 'Port 5173 still has a listener.')

console.log('UI_CONSISTENCY_OK=True')
console.log('RESPONSIVE_OK=True')
console.log('LOADING_UX_OK=True')
console.log('ERROR_HANDLING_OK=True')
console.log('EMPTY_STATES_OK=True')
console.log('ACCESSIBILITY_OK=True')
console.log('NAVIGATION_OK=True')
console.log('BRANDING_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('FINAL_PORT_5173_LISTENERS=0')
console.log('PHASE6_7_VALIDATION_OK=True')
