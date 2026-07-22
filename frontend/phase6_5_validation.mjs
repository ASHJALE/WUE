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
const storage = new Map([['wue_access_token', 'phase6-5-token']])
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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/quotationService.js'), 'utf8')
const listSource = await readFile(path.join(frontendDir, 'src/pages/Quotations.jsx'), 'utf8')
const createSource = await readFile(path.join(frontendDir, 'src/pages/QuotationCreate.jsx'), 'utf8')
const detailSource = await readFile(path.join(frontendDir, 'src/pages/QuotationDetail.jsx'), 'utf8')
const routeSource = await readFile(path.join(frontendDir, 'src/routes/AppRoutes.jsx'), 'utf8')
const bomSource = await readFile(path.join(frontendDir, 'src/pages/BomPreview.jsx'), 'utf8')

for (const snippet of [
  "apiClient.get('/quotations'", 'apiClient.get(`/quotations/${id}`)',
  'apiClient.post(`/estimates/${estimateId}/quotation`',
  'apiClient.post(`/quotations/${id}/approve`', 'apiClient.post(`/quotations/${id}/reject`',
  'apiClient.post(`/quotations/${id}/complete`', 'apiClient.get(`/quotations/${id}/pdf`',
]) assert(serviceSource.includes(snippet), `Quotation service is missing ${snippet}.`)
assert(serviceSource.includes("responseType: 'blob'"), 'PDF request does not use blob response.')
assert(serviceSource.includes('URL.revokeObjectURL(objectUrl)'), 'PDF object URL is not revoked.')
assert(listSource.includes('Loading quotations…') && listSource.includes('No quotations yet') && listSource.includes('onClick={loadQuotations}'), 'List states are incomplete.')
assert(createSource.includes('labor_cost') && createSource.includes('logistics_cost') && createSource.includes('profit_margin_percentage'), 'Generation fields do not match OpenAPI.')
assert(createSource.includes('navigate(`/quotations/${created.id}`'), 'Generation does not redirect to detail.')
assert(detailSource.includes("quotation.status === 'draft'") && detailSource.includes("quotation.status === 'approved'"), 'Workflow visibility rules are missing.')
assert(detailSource.includes('window.confirm') && detailSource.includes('await loadQuotation()'), 'Confirmation or detail refresh is missing.')
assert(detailSource.includes('getApiErrorMessage'), 'Backend transition error handling is missing.')
assert(!detailSource.includes('parseFloat') && !detailSource.includes('material_total +'), 'Frontend recalculates quotation totals.')
assert(bomSource.includes('to={`/quotations/new?estimate_id=${preview.estimate_id}`}'), 'BOM handoff is incorrect.')
const protectedBlock = routeSource.slice(routeSource.indexOf('<Route element={<ProtectedRoute />}>'))
for (const route of ['quotations', 'quotations/new', 'quotations/:id']) assert(protectedBlock.includes(`path="${route}"`), `${route} is not protected.`)

for (const field of [
  'quotation_number', 'estimate_id', 'user_id', 'username', 'furniture_type_id',
  'furniture_type_name', 'material_total', 'labor_cost', 'logistics_cost',
  'subtotal_before_profit', 'profit_percentage', 'profit_amount', 'grand_total',
  'currency_code', 'status', 'valid_until', 'notes', 'created_at', 'updated_at',
  'material_id', 'furniture_material_id', 'material_name_snapshot', 'unit_snapshot',
  'quantity', 'unit_price_snapshot', 'line_total', 'is_alternative',
]) assert(detailSource.includes(field), `Quotation detail omits ${field}.`)

const quotation = {
  id: 71, quotation_number: 'WUE-VALIDATION-71', estimate_id: 42, user_id: 9,
  username: 'validator', furniture_type_id: 3, furniture_type_name: 'Chair',
  material_total: '100.00', labor_cost: '20.00', logistics_cost: '5.00',
  subtotal_before_profit: '125.00', profit_percentage: '10.00', profit_amount: '12.50',
  grand_total: '137.50', currency_code: 'PHP', status: 'draft', valid_until: null,
  notes: null, created_at: '2026-07-23T00:00:00Z', updated_at: '2026-07-23T00:00:00Z',
  items: [{ id: 1, material_id: 2, furniture_material_id: 3,
    material_name_snapshot: 'Mahogany', unit_snapshot: 'board foot', quantity: '2.000',
    unit_price_snapshot: '50.00', line_total: '100.00', is_alternative: false,
    created_at: '2026-07-23T00:00:00Z' }],
}

const { default: apiClient } = await import('./src/api/client.js')
const quotationService = await import('./src/services/quotationService.js')
const originalAdapter = apiClient.defaults.adapter
const requests = []
apiClient.defaults.adapter = async (config) => {
  requests.push({ method: config.method, url: config.url, data: config.data, params: config.params })
  if (config.url.endsWith('/invalid')) return Promise.reject({ response: { status: 400, data: { detail: 'Invalid transition.' } }, config })
  let data = quotation
  if (config.url === '/quotations') data = [quotation]
  if (config.url.endsWith('/approve')) data = { ...quotation, status: 'approved' }
  if (config.url.endsWith('/reject')) data = { ...quotation, status: 'rejected' }
  if (config.url.endsWith('/complete')) data = { ...quotation, status: 'completed' }
  return { data, status: config.method === 'post' ? 200 : 200, statusText: 'OK', headers: {}, config }
}

assert((await quotationService.getQuotations({ user_id: 9 }))[0].id === 71, 'Quotation list failed.')
assert((await quotationService.getQuotation(71)).id === 71, 'Quotation detail failed.')
const generation = { labor_cost: '20.00', logistics_cost: '5.00', profit_margin_percentage: '10.00' }
assert((await quotationService.generateQuotation(42, generation)).id === 71, 'Quotation generation failed.')
assert((await quotationService.approveQuotation(71)).status === 'approved', 'Approve action failed.')
assert((await quotationService.rejectQuotation(71)).status === 'rejected', 'Reject action failed.')
assert((await quotationService.completeQuotation(71)).status === 'completed', 'Complete action failed.')
const generationRequest = requests.find((request) => request.url === '/estimates/42/quotation')
assert(JSON.stringify(JSON.parse(generationRequest.data)) === JSON.stringify(generation), 'Generation payload differs from OpenAPI.')
assert(requests.some((request) => request.url === '/quotations/71/approve'), 'Approve path is incorrect.')
assert(requests.some((request) => request.url === '/quotations/71/reject'), 'Reject path is incorrect.')
assert(requests.some((request) => request.url === '/quotations/71/complete'), 'Complete path is incorrect.')

let invalidHandled = false
try { await apiClient.post('/quotations/71/invalid') } catch (error) { invalidHandled = error.response?.status === 400 }
assert(invalidHandled, 'Invalid transition errors are not preserved for the UI.')
console.log('QUOTATION_GENERATION_OK=True')
console.log('WORKFLOW_APPROVE_OK=True')
console.log('WORKFLOW_REJECT_OK=True')
console.log('WORKFLOW_COMPLETE_OK=True')
console.log('INVALID_TRANSITION_HANDLING_OK=True')

let clicked = false
let appended = false
let removed = false
let revoked = null
const anchor = {
  style: {},
  click: () => { clicked = true },
  remove: () => { removed = true },
  href: '',
  download: '',
}
globalThis.document = {
  createElement: (tag) => { assert(tag === 'a', 'PDF download created an unsafe element.'); return anchor },
  body: { appendChild: (element) => { appended = element === anchor } },
}
const originalCreateObjectURL = URL.createObjectURL
const originalRevokeObjectURL = URL.revokeObjectURL
URL.createObjectURL = () => 'blob:phase6-5-validation'
URL.revokeObjectURL = (value) => { revoked = value }
apiClient.defaults.adapter = async (config) => ({
  data: new Blob(['%PDF-validation'], { type: 'application/pdf' }), status: 200, statusText: 'OK',
  headers: { 'content-disposition': 'inline; filename="WUE-VALIDATION-71.pdf"' }, config,
})
const filename = await quotationService.downloadQuotationPdf(71)
assert(filename === 'WUE-VALIDATION-71.pdf' && anchor.download === filename, 'PDF filename handling failed.')
assert(clicked && appended && removed && revoked === 'blob:phase6-5-validation', 'PDF download cleanup failed.')
URL.createObjectURL = originalCreateObjectURL
URL.revokeObjectURL = originalRevokeObjectURL
delete globalThis.document
apiClient.defaults.adapter = originalAdapter
console.log('PDF_DOWNLOAD_OK=True')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
try {
  const { AuthContext } = await viteSsr.ssrLoadModule('/src/context/AuthContext.jsx')
  const { default: Quotations } = await viteSsr.ssrLoadModule('/src/pages/Quotations.jsx')
  const { default: QuotationCreate } = await viteSsr.ssrLoadModule('/src/pages/QuotationCreate.jsx')
  const { default: QuotationDetail } = await viteSsr.ssrLoadModule('/src/pages/QuotationDetail.jsx')
  const authValue = { accessToken: 'token', user: { id: 9, username: 'validator' }, loading: false,
    isAuthenticated: true, login: async () => {}, register: async () => {}, logout: () => {}, restoreSession: async () => {} }
  const renderPage = (Page, entry) => renderToString(React.createElement(MemoryRouter, { initialEntries: [entry] }, React.createElement(AuthContext.Provider, { value: authValue }, React.createElement(Page))))
  assert(renderPage(Quotations, '/quotations').includes('Loading quotations'), 'Quotation list did not render.')
  const createHtml = renderPage(QuotationCreate, '/quotations/new?estimate_id=42')
  assert(createHtml.includes('Create quotation') && createHtml.includes('Labor cost'), 'Quotation create did not render.')
  assert(renderPage(QuotationDetail, '/quotations/71').includes('spinner-border'), 'Quotation detail did not render.')
  console.log('QUOTATION_LIST_RENDER_OK=True')
  console.log('QUOTATION_CREATE_RENDER_OK=True')
  console.log('QUOTATION_DETAIL_RENDER_OK=True')
} finally { await viteSsr.close() }

assert(run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim() === '', 'Backend changed.')
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'Migration changed.')
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')

let viteErrors = ''
const viteProcess = spawn(process.execPath, ['./node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', '5173', '--strictPort'], { cwd: frontendDir, stdio: ['ignore', 'ignore', 'pipe'] })
viteProcess.stderr.on('data', (chunk) => { viteErrors += chunk.toString() })
try {
  await waitForServer('http://127.0.0.1:5173/quotations')
  for (const route of ['/quotations', '/quotations/new?estimate_id=42', '/quotations/71']) {
    const response = await fetch(`http://127.0.0.1:5173${route}`)
    assert(response.status === 200 && (await response.text()).includes('<div id="root"></div>'), `${route} was not served.`)
  }
} finally {
  viteProcess.kill()
  await new Promise((resolve) => viteProcess.once('exit', resolve))
}
assert(!viteErrors.trim(), `Vite reported errors:\n${viteErrors}`)
let portStillOpen = false
try { await fetch('http://127.0.0.1:5173/', { signal: AbortSignal.timeout(500) }); portStillOpen = true } catch { /* Expected. */ }
assert(!portStillOpen, 'Port 5173 still has a listener.')

console.log('QUOTATION_SERVICE_OK=True')
console.log('QUOTATION_LIST_OK=True')
console.log('QUOTATION_CREATE_OK=True')
console.log('QUOTATION_DETAIL_OK=True')
console.log('DETAIL_REFRESH_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('EMPTY_STATE_OK=True')
console.log('RETRY_OK=True')
console.log('BOM_HANDOFF_OK=True')
console.log('PROTECTED_ROUTES_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('FINAL_PORT_5173_LISTENERS=0')
console.log('PHASE6_5_VALIDATION_OK=True')
