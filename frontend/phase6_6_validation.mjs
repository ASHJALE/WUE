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
const storage = new Map([['wue_access_token', 'phase6-6-token']])
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
  const result = spawnSync(command, args, { cwd, encoding: 'utf8', shell: process.platform === 'win32' })
  if (result.status !== 0) throw new Error(`${command} failed:\n${result.stdout}\n${result.stderr}`)
  return `${result.stdout}${result.stderr}`
}

async function waitForServer(url) {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try { if ((await fetch(url)).ok) return } catch { /* Vite may still be starting. */ }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  throw new Error(`Timed out waiting for ${url}`)
}

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Production build did not succeed.')
console.log('NPM_BUILD_OK=True')

const serviceSource = await readFile(path.join(frontendDir, 'src/services/dashboardService.js'), 'utf8')
const dashboardSource = await readFile(path.join(frontendDir, 'src/pages/Dashboard.jsx'), 'utf8')
const chartSource = await readFile(path.join(frontendDir, 'src/components/DashboardCharts.jsx'), 'utf8')
const routeSource = await readFile(path.join(frontendDir, 'src/routes/AppRoutes.jsx'), 'utf8')

assert(serviceSource.includes('fetchCurrentUser()'), 'Dashboard does not load the current user.')
assert(serviceSource.includes('fetchAll(getEstimates, user.id)') && serviceSource.includes('fetchAll(getQuotations, user.id)'), 'Dashboard list aggregation is missing.')
assert(serviceSource.includes('Math.round(Number(quotation.material_total) * 100)'), 'Material value is not derived in cents.')
assert(serviceSource.includes('.slice(0, 5)'), 'Recent activity is not limited to five.')
for (const label of ['Total Estimates', 'Draft Quotations', 'Approved Quotations', 'Completed Quotations', 'Rejected Quotations', 'Estimated Material Value']) {
  assert(dashboardSource.includes(label), `Summary card ${label} is missing.`)
}
assert(dashboardSource.includes('Recent Estimates') && dashboardSource.includes('Recent Quotations'), 'Recent activity sections are missing.')
assert(dashboardSource.includes('placeholder-glow'), 'Skeleton loading is missing.')
assert(dashboardSource.includes('No dashboard activity yet'), 'Empty state is missing.')
assert(dashboardSource.includes('onClick={loadDashboard}') && dashboardSource.includes('Retry'), 'Retry behavior is missing.')
assert(chartSource.includes("type: 'doughnut'") && chartSource.includes("type: 'bar'"), 'Required charts are missing.')
assert(chartSource.includes('Create a quotation to view status analytics') && chartSource.includes('Create an estimate to view timeline analytics'), 'Chart placeholders are missing.')
const protectedBlock = routeSource.slice(routeSource.indexOf('<Route element={<ProtectedRoute />}>'))
assert(protectedBlock.includes('path="dashboard"'), 'Dashboard route is not protected.')

const estimates = [
  { id: 1, selected_furniture_type_name: 'Chair', recognized_furniture_type_name: null, status: 'draft', created_at: '2026-07-20T10:00:00Z' },
  { id: 2, selected_furniture_type_name: 'Bed', recognized_furniture_type_name: null, status: 'processed', created_at: '2026-07-22T10:00:00Z' },
  { id: 3, selected_furniture_type_name: 'Sofa', recognized_furniture_type_name: null, status: 'quoted', created_at: '2026-07-22T12:00:00Z' },
  { id: 4, selected_furniture_type_name: 'Table', recognized_furniture_type_name: null, status: 'draft', created_at: '2026-07-23T10:00:00Z' },
  { id: 5, selected_furniture_type_name: 'Lamp', recognized_furniture_type_name: null, status: 'processing', created_at: '2026-07-24T10:00:00Z' },
  { id: 6, selected_furniture_type_name: 'Chair', recognized_furniture_type_name: null, status: 'draft', created_at: '2026-07-25T10:00:00Z' },
]
const quotations = [
  { id: 11, furniture_type_name: 'Chair', status: 'draft', material_total: '10.10', created_at: '2026-07-20T10:00:00Z' },
  { id: 12, furniture_type_name: 'Bed', status: 'approved', material_total: '20.20', created_at: '2026-07-21T10:00:00Z' },
  { id: 13, furniture_type_name: 'Sofa', status: 'completed', material_total: '30.30', created_at: '2026-07-22T10:00:00Z' },
  { id: 14, furniture_type_name: 'Table', status: 'rejected', material_total: '40.40', created_at: '2026-07-23T10:00:00Z' },
  { id: 15, furniture_type_name: 'Lamp', status: 'draft', material_total: '50.50', created_at: '2026-07-24T10:00:00Z' },
  { id: 16, furniture_type_name: 'Chair', status: 'approved', material_total: '60.60', created_at: '2026-07-25T10:00:00Z' },
]

const { default: apiClient } = await import('./src/api/client.js')
const { getDashboardSummary } = await import('./src/services/dashboardService.js')
const originalAdapter = apiClient.defaults.adapter
const requests = []
apiClient.defaults.adapter = async (config) => {
  requests.push({ url: config.url, params: config.params })
  let data
  if (config.url === '/auth/me') data = { id: 9, username: 'validator', email: 'validator@example.test', full_name: 'Validation User', role: 'user' }
  else if (config.url === '/estimates') data = estimates
  else if (config.url === '/quotations') data = quotations
  else throw new Error(`Unexpected dashboard request: ${config.url}`)
  return { data, status: 200, statusText: 'OK', headers: {}, config }
}
const dashboard = await getDashboardSummary()
apiClient.defaults.adapter = originalAdapter
assert(dashboard.summary.totalEstimates === 6, 'Estimate count is incorrect.')
assert(JSON.stringify([dashboard.summary.draft, dashboard.summary.approved, dashboard.summary.completed, dashboard.summary.rejected]) === JSON.stringify([2, 2, 1, 1]), 'Quotation status counts are incorrect.')
assert(dashboard.summary.materialValue === 212.1, 'Material value is incorrect.')
assert(dashboard.recentEstimates.length === 5 && dashboard.recentEstimates[0].id === 6 && dashboard.recentEstimates.at(-1).id === 2, 'Recent estimates are not newest-first five.')
assert(dashboard.recentQuotations.length === 5 && dashboard.recentQuotations[0].id === 16 && dashboard.recentQuotations.at(-1).id === 12, 'Recent quotations are not newest-first five.')
assert(dashboard.estimateTimeline.find((point) => point.date === '2026-07-22').count === 2, 'Estimate timeline grouping is incorrect.')
assert(requests.find((request) => request.url === '/estimates').params.user_id === 9, 'Estimates are not user-filtered.')
assert(requests.find((request) => request.url === '/quotations').params.user_id === 9, 'Quotations are not user-filtered.')
console.log('DASHBOARD_AGGREGATION_OK=True')

const viteSsr = await createServer({
  server: { middlewareMode: true },
  appType: 'custom',
  optimizeDeps: { noDiscovery: true, include: [] },
})
try {
  const { AuthContext } = await viteSsr.ssrLoadModule('/src/context/AuthContext.jsx')
  const { default: Dashboard } = await viteSsr.ssrLoadModule('/src/pages/Dashboard.jsx')
  const { default: DashboardCharts } = await viteSsr.ssrLoadModule('/src/components/DashboardCharts.jsx')
  const authValue = { accessToken: 'token', user: { id: 9, username: 'validator' }, loading: false,
    isAuthenticated: true, login: async () => {}, register: async () => {}, logout: () => {}, restoreSession: async () => {} }
  const dashboardHtml = renderToString(React.createElement(MemoryRouter, null, React.createElement(AuthContext.Provider, { value: authValue }, React.createElement(Dashboard))))
  assert(dashboardHtml.includes('placeholder-glow') && dashboardHtml.includes('New Estimate'), 'Dashboard loading state did not render.')
  const populatedCharts = renderToString(React.createElement(DashboardCharts, { quotations, statusCounts: dashboard.quotationStatusCounts, timeline: dashboard.estimateTimeline }))
  assert(populatedCharts.includes('canvas') && populatedCharts.includes('Quotation status doughnut chart') && populatedCharts.includes('Estimate creation timeline chart'), 'Populated charts did not render.')
  const emptyCharts = renderToString(React.createElement(DashboardCharts, { quotations: [], statusCounts: { draft: 0, approved: 0, completed: 0, rejected: 0 }, timeline: [] }))
  assert(emptyCharts.includes('Create a quotation') && emptyCharts.includes('Create an estimate'), 'Chart placeholders did not render.')
  console.log('DASHBOARD_RENDER_OK=True')
  console.log('CHARTS_RENDER_OK=True')
} finally { await viteSsr.close() }

assert(run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim() === '', 'Backend changed.')
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'Migration changed.')
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')

let viteErrors = ''
const viteProcess = spawn(process.execPath, ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], { cwd: frontendDir, stdio: ['ignore', 'ignore', 'pipe'] })
viteProcess.stderr.on('data', (chunk) => { viteErrors += chunk.toString() })
try {
  await waitForServer('http://127.0.0.1:5173/dashboard')
  const response = await fetch('http://127.0.0.1:5173/dashboard')
  assert(response.status === 200 && (await response.text()).includes('<div id="root"></div>'), 'Dashboard route was not served.')
} finally {
  viteProcess.kill()
  await new Promise((resolve) => viteProcess.once('exit', resolve))
}
assert(!viteErrors.trim(), `Vite reported errors:\n${viteErrors}`)
let portStillOpen = false
try { await fetch('http://127.0.0.1:5173/', { signal: AbortSignal.timeout(500) }); portStillOpen = true } catch { /* Expected. */ }
assert(!portStillOpen, 'Port 5173 still has a listener.')

console.log('DASHBOARD_SUMMARY_OK=True')
console.log('RECENT_ACTIVITY_OK=True')
console.log('CHARTS_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('EMPTY_STATE_OK=True')
console.log('RETRY_OK=True')
console.log('PROTECTED_ROUTE_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('FINAL_PORT_5173_LISTENERS=0')
console.log('PHASE6_6_VALIDATION_OK=True')
