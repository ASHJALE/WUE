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
const storage = new Map([['wue_access_token', 'phase6-4-token']])
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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/bomService.js'), 'utf8')
const pageSource = await readFile(path.join(frontendDir, 'src/pages/BomPreview.jsx'), 'utf8')
const cardSource = await readFile(path.join(frontendDir, 'src/components/BomItemCard.jsx'), 'utf8')
const detailSource = await readFile(path.join(frontendDir, 'src/pages/EstimateDetail.jsx'), 'utf8')
const routeSource = await readFile(path.join(frontendDir, 'src/routes/AppRoutes.jsx'), 'utf8')

assert(serviceSource.includes('apiClient.get(`/estimates/${estimateId}/bom-preview`)'), 'BOM endpoint is incorrect.')
assert(pageSource.includes('Loading BOM preview…') && pageSource.includes('spinner-border'), 'Loading state is missing.')
assert(pageSource.includes('No BOM items available') && pageSource.includes('preview.items.length === 0'), 'Empty state is missing.')
assert(pageSource.includes('onClick={loadPreview}') && pageSource.includes('Retry'), 'Retry behavior is missing.')
assert(pageSource.includes('preview.material_total') && pageSource.includes('preview.has_inventory_shortage') && pageSource.includes('preview.item_count'), 'Backend totals are not displayed.')
assert(pageSource.includes('Create quotation') && pageSource.includes('estimate_id=${preview.estimate_id}'), 'Quotation handoff is missing.')
assert(detailSource.includes('to={`/estimates/${estimate.id}/bom`}') && detailSource.includes('Preview BOM'), 'Estimate detail BOM link is incorrect.')
const protectedBlock = routeSource.slice(routeSource.indexOf('<Route element={<ProtectedRoute />}>'))
assert(protectedBlock.includes('path="estimates/:id/bom"'), 'BOM route is not protected.')

for (const field of [
  'furniture_material_id', 'material_id', 'material_name', 'unit', 'base_quantity',
  'wastage_percentage', 'wastage_quantity', 'required_quantity',
  'current_unit_price', 'line_total', 'inventory_id', 'quantity_on_hand',
  'reorder_level', 'shortage_quantity', 'is_available',
  'alternative_material_id', 'alternative_material_name', 'alternative_unit',
  'alternative_current_unit_price', 'alternative_inventory_id',
  'alternative_quantity_on_hand', 'alternative_shortage_quantity',
  'alternative_is_available', 'estimated_alternative_line_total',
]) {
  assert(cardSource.includes(field), `BOM item field ${field} is not displayed.`)
}

const preview = {
  estimate_id: 42,
  furniture_type_id: 3,
  furniture_type_name: 'Chair',
  material_total: '125.50',
  has_inventory_shortage: false,
  item_count: 1,
  items: [{
    furniture_material_id: 17,
    material_id: 5,
    material_name: 'Mahogany',
    unit: 'board foot',
    base_quantity: '2.000',
    wastage_percentage: '10.00',
    wastage_quantity: '0.200',
    required_quantity: '2.200',
    current_unit_price: '50.00',
    line_total: '110.00',
    inventory: {
      inventory_id: 8,
      quantity_on_hand: '10.000',
      reorder_level: '2.000',
      shortage_quantity: '0.000',
      is_available: true,
    },
    direct_alternative: {
      alternative_material_id: 6,
      alternative_material_name: 'Pine',
      alternative_unit: 'board foot',
      alternative_current_unit_price: '30.00',
      alternative_inventory_id: 9,
      alternative_quantity_on_hand: '12.000',
      alternative_shortage_quantity: '0.000',
      alternative_is_available: true,
      estimated_alternative_line_total: '66.00',
    },
  }],
}

const { default: apiClient } = await import('./src/api/client.js')
const { getBomPreview } = await import('./src/services/bomService.js')
const originalAdapter = apiClient.defaults.adapter
let requestedUrl = null
apiClient.defaults.adapter = async (config) => {
  requestedUrl = config.url
  return { data: preview, status: 200, statusText: 'OK', headers: {}, config }
}
const loaded = await getBomPreview(42)
assert(requestedUrl === '/estimates/42/bom-preview', 'BOM service called the wrong endpoint.')
assert(loaded === preview && loaded.material_total === '125.50', 'BOM service altered the backend result.')
apiClient.defaults.adapter = originalAdapter
console.log('BOM_SERVICE_OK=True')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom' })
try {
  const { default: BomPreview } = await viteSsr.ssrLoadModule('/src/pages/BomPreview.jsx')
  const { default: BomItemCard } = await viteSsr.ssrLoadModule('/src/components/BomItemCard.jsx')
  const pageHtml = renderToString(
    React.createElement(MemoryRouter, { initialEntries: ['/estimates/42/bom'] }, React.createElement(BomPreview)),
  )
  const cardHtml = renderToString(React.createElement(BomItemCard, { item: preview.items[0] }))
  assert(pageHtml.includes('Loading BOM preview'), 'BOM preview page did not render.')
  for (const text of ['Mahogany', '2.200', '110.00', 'Quantity on hand', 'Pine', '66.00']) {
    assert(cardHtml.includes(text), `Rendered BOM card omitted ${text}.`)
  }
  console.log('BOM_PREVIEW_RENDER_OK=True')
  console.log('BOM_ITEM_CARD_RENDER_OK=True')
} finally {
  await viteSsr.close()
}

const backendStatus = run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim()
assert(backendStatus === '', `Backend changed during Phase 6.4:\n${backendStatus}`)
const migrationStatus = run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim()
assert(migrationStatus === '', `A migration changed during Phase 6.4:\n${migrationStatus}`)
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
  await waitForServer('http://127.0.0.1:5173/estimates/42/bom')
  const response = await fetch('http://127.0.0.1:5173/estimates/42/bom')
  const body = await response.text()
  assert(response.status === 200 && body.includes('<div id="root"></div>'), 'BOM route was not served.')
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

console.log('BOM_PREVIEW_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('EMPTY_STATE_OK=True')
console.log('RETRY_OK=True')
console.log('ESTIMATE_LINK_OK=True')
console.log('PROTECTED_ROUTE_OK=True')
console.log('TEMP_SERVER_CLEANUP_OK=True')
console.log('PHASE6_4_VALIDATION_OK=True')
