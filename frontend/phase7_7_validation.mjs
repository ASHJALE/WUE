import { spawnSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/costCalculationService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("post('/costs/calculate'") && serviceSource.includes('profit_margin_percent: profitMarginPercent'), 'Cost request is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("'Calculate Cost'"), 'Calculate Cost button is missing.')
assert(estimateSource.includes('disabled={!quantityEstimates || calculatingCost}'), 'Calculate button disabled state is incorrect.')
assert(estimateSource.includes('if (!quantityEstimates || calculatingCost) return'), 'Duplicate cost request guard is missing.')
assert(estimateSource.includes('Calculating cost…') && estimateSource.includes('spinner-border'), 'Calculating state is missing.')
for (const id of ['labor-hours', 'hourly-rate', 'profit-margin-percent']) {
  assert(estimateSource.includes(`id="${id}"`), `Cost input ${id} is missing.`)
}
assert(estimateSource.includes('profitMargin < 0 || profitMargin > 100'), 'Profit margin validation is missing.')
for (const field of ['item.component', 'item.material', 'item.estimated_quantity', 'item.unit', 'item.unit_price', 'item.subtotal']) {
  assert(estimateSource.includes(field), `Itemized cost field ${field} is missing.`)
}
for (const field of ['total_material_cost', 'labor.labor_cost', 'profit_amount', 'final_estimated_cost']) {
  assert(estimateSource.includes(`costResult.${field}`), `Cost summary field ${field} is missing.`)
}
assert(estimateSource.includes("new Intl.NumberFormat('en-PH'") && estimateSource.includes("currency: 'PHP'"), 'PHP currency formatter is missing.')
assert(estimateSource.includes('No overhead cost is included.'), 'No-overhead notice is missing.')
assert(estimateSource.includes('Material prices are configurable preliminary values'), 'Preliminary-price notice is missing.')

const inputStart = estimateSource.indexOf('function handleCostInputChange')
const inputBlock = estimateSource.slice(inputStart, estimateSource.indexOf('\n  }', inputStart) + 4)
assert(inputBlock.includes('clearCostResult()'), 'Cost input changes do not clear the result.')
const quantityResetStart = estimateSource.indexOf('function clearQuantityEstimate')
const quantityResetBlock = estimateSource.slice(quantityResetStart, estimateSource.indexOf('\n  }', quantityResetStart) + 4)
assert(quantityResetBlock.includes('clearCostResult()'), 'Upstream quantity resets do not clear cost.')
assert(estimateSource.includes('costRequestId.current += 1'), 'Stale cost response invalidation is missing.')

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('costResult') && !payloadBlock.includes('costInputs'), 'Cost data leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase77-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { calculatePreliminaryCost } = await viteSsr.ssrLoadModule('/src/services/costCalculationService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { furniture_type: 'chair', currency: 'PHP', components: [], status: 'calculated' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const components = [{ component: 'Frame', material: 'Mahogany', category: 'Solid Wood', estimated_quantity: 2.35, unit: 'board_foot', calculation_basis: 'Template Estimate', confidence: 'Preliminary' }]
  const labor = { hours: 8, hourly_rate: 150 }
  const result = await calculatePreliminaryCost('chair', components, labor, 20)
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/costs/calculate' && captured.method === 'post', 'Cost endpoint request is wrong.')
  const payload = JSON.parse(captured.data)
  assert(payload.furniture_type === 'chair' && JSON.stringify(payload.components) === JSON.stringify(components), 'Cost component payload is wrong.')
  assert(JSON.stringify(payload.labor) === JSON.stringify(labor) && payload.profit_margin_percent === 20, 'Labor or profit payload is wrong.')
  assert(captured.headers.Authorization === 'Bearer phase77-token', 'Bearer token was not attached.')
  assert(result.status === 'calculated' && result.currency === 'PHP', 'Cost response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('CALCULATE_BUTTON_OK=True')
console.log('BUTTON_DISABLED_BEFORE_QUANTITIES_OK=True')
console.log('LABOR_INPUTS_OK=True')
console.log('PROFIT_MARGIN_VALIDATION_OK=True')
console.log('AUTH_REQUEST_OK=True')
console.log('CALCULATING_STATE_OK=True')
console.log('DUPLICATE_REQUEST_PREVENTION_OK=True')
console.log('ITEMIZED_COST_DISPLAY_OK=True')
console.log('PHP_FORMATTING_OK=True')
console.log('MATERIAL_TOTAL_DISPLAY_OK=True')
console.log('LABOR_TOTAL_DISPLAY_OK=True')
console.log('PROFIT_DISPLAY_OK=True')
console.log('FINAL_TOTAL_DISPLAY_OK=True')
console.log('NO_OVERHEAD_NOTICE_OK=True')
console.log('PRELIMINARY_PRICE_NOTICE_OK=True')
console.log('RESET_ON_COST_INPUT_CHANGE_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_7_FRONTEND_VALIDATION_OK=True')
