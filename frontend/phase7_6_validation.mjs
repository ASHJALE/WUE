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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/quantityEstimationService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("post('/bom/estimate-quantities'") && serviceSource.includes('dimensions,') && serviceSource.includes('components,'), 'Quantity request is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("'Estimate Quantities'"), 'Estimate Quantities button is missing.')
assert(estimateSource.includes('disabled={!generatedBom || estimatingQuantities}'), 'Quantity button disabled state is incorrect.')
assert(estimateSource.includes('if (!generatedBom || estimatingQuantities) return'), 'Duplicate quantity request guard is missing.')
assert(estimateSource.includes('Estimating quantities…') && estimateSource.includes('spinner-border'), 'Quantity loading state is missing.')
for (const dimension of ['width', 'depth', 'height']) {
  assert(estimateSource.includes(`${dimension}:`) && estimateSource.includes(`dimension-${'${dimension}'}`), `Dimension ${dimension} is missing.`)
}
assert(estimateSource.includes('!Number.isFinite(value) || value <= 0'), 'Client dimension validation is missing.')
for (const field of ['item.component', 'item.material', 'item.estimated_quantity', 'item.unit', 'item.calculation_basis', 'item.confidence']) {
  assert(estimateSource.includes(field), `Quantity field ${field} is not displayed.`)
}
assert(estimateSource.includes('quantityEstimates.components.length') && estimateSource.includes('estimated components'), 'Estimated component count is missing.')
assert(estimateSource.includes('Dimensions: {dimensions.width}') && estimateSource.includes('W × D × H'), 'Dimension summary is missing.')
assert(estimateSource.includes('These are preliminary engineering estimates and will be refined during pricing.'), 'Preliminary estimate notice is missing.')

const dimensionStart = estimateSource.indexOf('function handleDimensionChange')
const dimensionBlock = estimateSource.slice(dimensionStart, estimateSource.indexOf('\n  }', dimensionStart) + 4)
assert(dimensionBlock.includes('clearQuantityEstimate()'), 'Dimension changes do not clear estimates.')
assert(estimateSource.includes('quantityRequestId.current += 1'), 'Stale quantity request invalidation is missing.')

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('quantityEstimates') && !payloadBlock.includes('dimensions'), 'Quantity data leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase76-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { estimateBomQuantities } = await viteSsr.ssrLoadModule('/src/services/quantityEstimationService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { furniture_type: 'chair', components: [], status: 'estimated' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const dimensions = { width: 450, depth: 500, height: 900 }
  const components = [{ component: 'Frame', recommended_material: 'Mahogany', category: 'Solid Wood', source: 'Primary Recommendation', unit: 'piece', quantity: null, notes: 'Quantity calculated in Phase 7.6' }]
  const result = await estimateBomQuantities('chair', dimensions, components)
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/bom/estimate-quantities' && captured.method === 'post', 'Quantity endpoint request is wrong.')
  const payload = JSON.parse(captured.data)
  assert(payload.furniture_type === 'chair' && JSON.stringify(payload.dimensions) === JSON.stringify(dimensions) && JSON.stringify(payload.components) === JSON.stringify(components), 'Quantity request payload is wrong.')
  assert(captured.headers.Authorization === 'Bearer phase76-token', 'Bearer token was not attached.')
  assert(result.status === 'estimated', 'Quantity response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('ESTIMATE_BUTTON_OK=True')
console.log('BUTTON_DISABLED_BEFORE_BOM_OK=True')
console.log('DIMENSION_INPUT_OK=True')
console.log('AUTH_REQUEST_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('DUPLICATE_REQUEST_PREVENTION_OK=True')
console.log('QUANTITY_DISPLAY_OK=True')
console.log('DIMENSION_SUMMARY_OK=True')
console.log('NOTICE_DISPLAY_OK=True')
console.log('RESET_ON_DIMENSION_CHANGE_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_6_FRONTEND_VALIDATION_OK=True')
