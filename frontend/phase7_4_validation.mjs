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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/materialRecommendationService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("post('/materials/recommend'") && serviceSource.includes('furniture_type: furnitureType'), 'Recommendation request is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("'Recommend Materials'"), 'Recommend Materials button is missing.')
assert(estimateSource.includes('!classificationConfirmed || !confirmedFurnitureType || recommendingMaterials'), 'Recommendation disabled state is incorrect.')
assert(estimateSource.includes('if (!classificationConfirmed || !confirmedFurnitureType || recommendingMaterials) return'), 'Duplicate request guard is missing.')
assert(estimateSource.includes('Recommending materials…') && estimateSource.includes('spinner-border'), 'Recommendation loading state is missing.')
for (const field of ['item.name', 'item.category', 'item.priority', 'item.quality', 'item.reason']) {
  assert(estimateSource.includes(field), `Recommendation field ${field} is not displayed.`)
}
assert(estimateSource.includes("['Primary', 'Alternative'].map") && estimateSource.includes('>{priority} Materials</h3>'), 'Priority grouping is missing.')
assert(estimateSource.includes('materialRecommendations.materials.length') && estimateSource.includes('recommended materials'), 'Recommendation count is missing.')
assert(estimateSource.includes('These recommendations are configurable and may be refined after production AI integration.'), 'Recommendation notice is missing.')
assert(estimateSource.includes('recommendationRequestId.current += 1'), 'Recommendation invalidation is missing.')

for (const functionName of ['handleImageChange', 'handleImageUpload', 'handleImageClassification', 'handleConfirmedTypeChange']) {
  const start = estimateSource.indexOf(`function ${functionName}`)
  const alternateStart = estimateSource.indexOf(`async function ${functionName}`)
  const actualStart = Math.max(start, alternateStart)
  assert(actualStart >= 0, `${functionName} is missing.`)
  const block = estimateSource.slice(actualStart, estimateSource.indexOf('\n  }', actualStart) + 4)
  assert(block.includes('setMaterialRecommendations(null)'), `${functionName} does not clear recommendations.`)
}

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('materialRecommendations') && !payloadBlock.includes('confirmedFurnitureType'), 'Recommendations leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase74-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { recommendMaterials } = await viteSsr.ssrLoadModule('/src/services/materialRecommendationService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { furniture_type: 'chair', materials: [], status: 'recommended' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const result = await recommendMaterials('chair')
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/materials/recommend' && captured.method === 'post', 'Recommendation endpoint request is wrong.')
  assert(JSON.parse(captured.data).furniture_type === 'chair', 'Recommendation request payload is wrong.')
  assert(captured.headers.Authorization === 'Bearer phase74-token', 'Bearer token was not attached.')
  assert(result.status === 'recommended', 'Recommendation response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('RECOMMEND_BUTTON_OK=True')
console.log('BUTTON_DISABLED_BEFORE_CONFIRMATION_OK=True')
console.log('AUTH_REQUEST_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('DUPLICATE_REQUEST_PREVENTION_OK=True')
console.log('RECOMMENDATION_DISPLAY_OK=True')
console.log('GROUPING_DISPLAY_OK=True')
console.log('COUNT_DISPLAY_OK=True')
console.log('NOTICE_DISPLAY_OK=True')
console.log('RESET_ON_TYPE_CHANGE_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_4_FRONTEND_VALIDATION_OK=True')
