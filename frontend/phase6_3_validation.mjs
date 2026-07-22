import { spawn, spawnSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'

const frontendDir = path.dirname(fileURLToPath(import.meta.url))
const projectDir = path.dirname(frontendDir)
const storage = new Map([['wue_access_token', 'phase6-3-token']])
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, String(value)),
  removeItem: (key) => storage.delete(key),
}
globalThis.window = new EventTarget()

function assert(condition, message) {
  if (!condition) throw new Error(message)
}

function run(command, args, cwd = frontendDir) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    shell: process.platform === 'win32',
  })
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed:\n${result.stdout}\n${result.stderr}`)
  }
  return `${result.stdout}${result.stderr}`
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const response = await fetch(url)
      if (response.ok) return
    } catch {
      // Vite may still be starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Production build did not succeed.')
console.log('NPM_BUILD_OK=True')

const routeSource = await readFile(path.join(frontendDir, 'src/routes/AppRoutes.jsx'), 'utf8')
const listSource = await readFile(path.join(frontendDir, 'src/pages/Estimates.jsx'), 'utf8')
const createSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const detailSource = await readFile(path.join(frontendDir, 'src/pages/EstimateDetail.jsx'), 'utf8')
const serviceSource = await readFile(path.join(frontendDir, 'src/services/estimateService.js'), 'utf8')

assert(serviceSource.includes("apiClient.get('/estimates'"), 'Estimate list endpoint is incorrect.')
assert(serviceSource.includes('apiClient.get(`/estimates/${id}`)'), 'Estimate detail endpoint is incorrect.')
assert(serviceSource.includes("apiClient.post('/estimates'"), 'Estimate create endpoint is incorrect.')
assert(!serviceSource.includes('delete'), 'Delete behavior was added without backend support.')
assert(routeSource.includes('path="estimates/new"') && routeSource.includes('path="estimates/:id"'), 'Estimate routes are missing.')
const protectedBlock = routeSource.slice(routeSource.indexOf('<Route element={<ProtectedRoute />}>'))
assert(protectedBlock.includes('path="estimates"') && protectedBlock.includes('path="estimates/new"') && protectedBlock.includes('path="estimates/:id"'), 'Estimate routes are not protected.')
assert(listSource.includes('Loading estimates…') && listSource.includes('spinner-border'), 'Loading state is missing.')
assert(listSource.includes('No estimates yet') && listSource.includes('estimates.length === 0'), 'Empty state is missing.')
assert(listSource.includes('onClick={loadEstimates}') && listSource.includes('Retry'), 'Retry refresh is missing.')
assert(createSource.includes('user_id: user.id') && createSource.includes('input_method'), 'Required create fields are missing.')
assert(detailSource.includes("['ID', estimate.id]") && detailSource.includes("['Updated at'"), 'Detail page does not display every response field.')

const { default: apiClient } = await import('./src/api/client.js')
const { createEstimate, getEstimate, getEstimates } = await import('./src/services/estimateService.js')
const originalAdapter = apiClient.defaults.adapter
const requests = []
const createdRecord = {
  id: 501,
  user_id: 9,
  username: 'validator',
  selected_furniture_type_id: 2,
  selected_furniture_type_name: 'Chair',
  recognized_furniture_type_id: null,
  recognized_furniture_type_name: null,
  image_path: null,
  input_method: 'predefined',
  recognition_confidence: null,
  status: 'draft',
  created_at: '2026-07-23T00:00:00Z',
  updated_at: '2026-07-23T00:00:00Z',
}
apiClient.defaults.adapter = async (config) => {
  requests.push({ method: config.method, url: config.url, params: config.params, data: config.data })
  let data
  if (config.method === 'post' && config.url === '/estimates') data = createdRecord
  else if (config.method === 'get' && config.url === '/estimates/501') data = createdRecord
  else if (config.method === 'get' && config.url === '/estimates') data = [createdRecord]
  else throw new Error(`Unexpected estimate request: ${config.method} ${config.url}`)
  return { data, status: config.method === 'post' ? 201 : 200, statusText: 'OK', headers: {}, config }
}

const createPayload = {
  user_id: 9,
  input_method: 'predefined',
  selected_furniture_type_id: 2,
  recognized_furniture_type_id: null,
  image_path: null,
  recognition_confidence: null,
}
const created = await createEstimate(createPayload)
assert(created.id === 501, 'Successful create did not return the estimate.')
const detail = await getEstimate(created.id)
assert(detail.id === created.id, 'Created estimate detail did not load.')
const refreshed = await getEstimates({ user_id: 9, limit: 200 })
assert(refreshed.length === 1 && refreshed[0].id === created.id, 'List did not refresh with the created estimate.')
assert(JSON.parse(requests[0].data).user_id === 9 && JSON.parse(requests[0].data).input_method === 'predefined', 'Create payload does not match OpenAPI.')
assert(requests[2].params.user_id === 9, 'List refresh did not filter by the authenticated user.')
apiClient.defaults.adapter = originalAdapter
console.log('SUCCESSFUL_CREATE_OK=True')
console.log('REFRESH_OK=True')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
try {
  const { AuthContext } = await viteSsr.ssrLoadModule('/src/context/AuthContext.jsx')
  const { default: Estimates } = await viteSsr.ssrLoadModule('/src/pages/Estimates.jsx')
  const { default: EstimateCreate } = await viteSsr.ssrLoadModule('/src/pages/EstimateCreate.jsx')
  const { default: EstimateDetail } = await viteSsr.ssrLoadModule('/src/pages/EstimateDetail.jsx')
  const authValue = {
    accessToken: 'phase6-3-token',
    user: { id: 9, username: 'validator' },
    loading: false,
    isAuthenticated: true,
    login: async () => {}, register: async () => {}, logout: () => {}, restoreSession: async () => {},
  }
  const renderPage = (Page, entry) => renderToString(
    React.createElement(
      MemoryRouter,
      { initialEntries: [entry] },
      React.createElement(AuthContext.Provider, { value: authValue }, React.createElement(Page)),
    ),
  )
  const listHtml = renderPage(Estimates, '/estimates')
  const createHtml = renderPage(EstimateCreate, '/estimates/new')
  const detailHtml = renderPage(EstimateDetail, '/estimates/501')
  assert(listHtml.includes('Loading estimates'), 'Estimates page did not render its initial loading state.')
  assert(createHtml.includes('Create estimate') && createHtml.includes('Input method'), 'Create page did not render.')
  assert(detailHtml.includes('spinner-border'), 'Detail page did not render its initial loading state.')
  console.log('ESTIMATE_LIST_RENDER_OK=True')
  console.log('ESTIMATE_CREATE_RENDER_OK=True')
  console.log('ESTIMATE_DETAIL_RENDER_OK=True')
} finally {
  await viteSsr.close()
}

const backendStatus = run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim()
assert(backendStatus === '', `Backend changed during Phase 6.3:\n${backendStatus}`)
const migrationStatus = run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim()
assert(migrationStatus === '', `A migration changed during Phase 6.3:\n${migrationStatus}`)
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')

let viteErrors = ''
const viteProcess = spawn(
  process.execPath,
  ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'],
  { cwd: frontendDir, stdio: ['ignore', 'ignore', 'pipe'] },
)
viteProcess.stderr.on('data', (chunk) => { viteErrors += chunk.toString() })
try {
  await waitForServer('http://127.0.0.1:5173/estimates')
  for (const route of ['/estimates', '/estimates/new', '/estimates/501']) {
    const response = await fetch(`http://127.0.0.1:5173${route}`)
    const body = await response.text()
    assert(response.status === 200 && body.includes('<div id="root"></div>'), `${route} was not served.`)
  }
} finally {
  viteProcess.kill()
  await new Promise((resolve) => viteProcess.once('exit', resolve))
}
assert(!viteErrors.trim(), `Vite reported errors:\n${viteErrors}`)

let portStillOpen = false
try {
  await fetch('http://127.0.0.1:5173/', { signal: AbortSignal.timeout(500) })
  portStillOpen = true
} catch {
  // Expected after stopping the owned server.
}
assert(!portStillOpen, 'Port 5173 still has a listener.')

console.log('ESTIMATE_LIST_OK=True')
console.log('ESTIMATE_CREATE_OK=True')
console.log('ESTIMATE_DETAIL_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('EMPTY_STATE_OK=True')
console.log('PROTECTED_ROUTES_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('PHASE6_3_VALIDATION_OK=True')
