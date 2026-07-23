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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/imageService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes('`/images/${uploadId}/classify`'), 'Classify endpoint is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("!imageUploadResult || classifyingImage"), 'Analyze disabled state is missing.')
assert(estimateSource.includes("if (!imageUploadResult || classifyingImage) return"), 'Duplicate classification guard is missing.')
assert(estimateSource.includes("Analyzing furniture…") && estimateSource.includes('spinner-border'), 'Analyzing state is missing.')
for (const value of ['display_name', 'confidence * 100', 'model_name', 'model_version']) {
  assert(estimateSource.includes(value), `Classification display ${value} is missing.`)
}
assert(estimateSource.includes('not production-ready AI') && estimateSource.includes('Development classifier:'), 'Development classifier notice is missing.')
assert(estimateSource.includes('id="confirmed-furniture-type"') && estimateSource.includes('classificationResult.supported_classes.map'), 'User correction select is missing.')
assert(estimateSource.includes('confirmedFurnitureType') && estimateSource.includes('setClassificationConfirmed(true)'), 'Confirmed type state is missing.')

const resetBlock = estimateSource.slice(estimateSource.indexOf('function handleImageChange'), estimateSource.indexOf('async function handleImageUpload'))
for (const reset of ['setImageUploadResult(null)', 'setClassificationResult(null)', "setConfirmedFurnitureType('')"]) {
  assert(resetBlock.includes(reset), `Reset behavior ${reset} is missing.`)
}

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('classification') && !payloadBlock.includes('confirmedFurnitureType'), 'Classification leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase73-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { classifyFurnitureImage } = await viteSsr.ssrLoadModule('/src/services/imageService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { predicted_class: 'chair', confidence: 0.82 }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const result = await classifyFurnitureImage('00000000-0000-0000-0000-000000000001')
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/images/00000000-0000-0000-0000-000000000001/classify', 'Classification URL is wrong.')
  assert(captured.method === 'post' && captured.headers.Authorization === 'Bearer phase73-token', 'Authenticated classification request is wrong.')
  assert(result.predicted_class === 'chair', 'Classification result is not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('ANALYZE_BUTTON_OK=True')
console.log('ANALYZE_DISABLED_BEFORE_UPLOAD_OK=True')
console.log('CLASSIFY_AUTH_REQUEST_OK=True')
console.log('ANALYZING_STATE_OK=True')
console.log('DUPLICATE_CLASSIFY_PREVENTION_OK=True')
console.log('CLASSIFICATION_RESULT_DISPLAY_OK=True')
console.log('CONFIDENCE_PERCENT_DISPLAY_OK=True')
console.log('DEVELOPMENT_NOTICE_OK=True')
console.log('USER_CORRECTION_SELECT_OK=True')
console.log('CONFIRMED_TYPE_STATE_OK=True')
console.log('CHANGE_REMOVE_RESETS_CLASSIFICATION_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_3_FRONTEND_VALIDATION_OK=True')
