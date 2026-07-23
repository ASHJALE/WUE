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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/bomGenerationService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("post('/bom/generate'") && serviceSource.includes('furniture_type: furnitureType') && serviceSource.includes('materials,'), 'BOM request is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("'Generate BOM'"), 'Generate BOM button is missing.')
assert(estimateSource.includes('disabled={!materialRecommendations || generatingBom}'), 'Generate button disabled state is incorrect.')
assert(estimateSource.includes('if (!materialRecommendations || generatingBom) return'), 'Duplicate BOM request guard is missing.')
assert(estimateSource.includes('Generating BOM…') && estimateSource.includes('spinner-border'), 'BOM loading state is missing.')
for (const field of ['item.component', 'item.recommended_material', 'item.category', 'item.source', 'item.unit', 'item.notes']) {
  assert(estimateSource.includes(field), `BOM display field ${field} is missing.`)
}
assert(estimateSource.includes('generatedBom.components.length') && estimateSource.includes('BOM components'), 'Component count is missing.')
assert(estimateSource.includes('Quantities will be calculated during the next estimation phase.'), 'Quantity notice is missing.')
assert(estimateSource.includes('<table') && estimateSource.includes('scope="col"') && estimateSource.includes('table-responsive'), 'Accessible responsive BOM table is missing.')
assert(estimateSource.includes('bomRequestId.current += 1'), 'Stale BOM request invalidation is missing.')

const recommendationStart = estimateSource.indexOf('async function handleMaterialRecommendation')
const recommendationBlock = estimateSource.slice(recommendationStart, estimateSource.indexOf('\n  }', recommendationStart) + 4)
assert(recommendationBlock.includes('setGeneratedBom(null)') && recommendationBlock.includes('bomRequestId.current += 1'), 'Recommendation changes do not clear BOM state.')

for (const functionName of ['handleImageChange', 'handleImageUpload', 'handleImageClassification', 'handleConfirmedTypeChange']) {
  const plainStart = estimateSource.indexOf(`function ${functionName}`)
  const asyncStart = estimateSource.indexOf(`async function ${functionName}`)
  const actualStart = Math.max(plainStart, asyncStart)
  assert(actualStart >= 0, `${functionName} is missing.`)
  const block = estimateSource.slice(actualStart, estimateSource.indexOf('\n  }', actualStart) + 4)
  assert(block.includes('setGeneratedBom(null)'), `${functionName} does not clear BOM state.`)
}

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('generatedBom') && !payloadBlock.includes('materialRecommendations'), 'BOM data leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase75-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { generateStructuredBom } = await viteSsr.ssrLoadModule('/src/services/bomGenerationService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { furniture_type: 'chair', components: [], status: 'generated' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const materials = [{ name: 'Mahogany', category: 'Solid Wood', priority: 'Primary', quality: 'Premium', reason: 'Strong.' }]
  const result = await generateStructuredBom('chair', materials)
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/bom/generate' && captured.method === 'post', 'BOM endpoint request is wrong.')
  const payload = JSON.parse(captured.data)
  assert(
    payload.furniture_type === 'chair' && JSON.stringify(payload.materials) === JSON.stringify(materials),
    'BOM request payload is wrong.',
  )
  assert(captured.headers.Authorization === 'Bearer phase75-token', 'Bearer token was not attached.')
  assert(result.status === 'generated', 'BOM response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('GENERATE_BUTTON_OK=True')
console.log('BUTTON_DISABLED_BEFORE_RECOMMENDATIONS_OK=True')
console.log('AUTH_REQUEST_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('DUPLICATE_REQUEST_PREVENTION_OK=True')
console.log('BOM_DISPLAY_OK=True')
console.log('COMPONENT_COUNT_OK=True')
console.log('NOTICE_DISPLAY_OK=True')
console.log('RESET_ON_RECOMMENDATION_CHANGE_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_5_FRONTEND_VALIDATION_OK=True')
