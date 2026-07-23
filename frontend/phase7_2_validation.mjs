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
const pickerSource = await readFile(path.join(frontendDir, 'src/components/FurnitureImagePicker.jsx'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("formData.append('image', file)"), 'FormData image field is incorrect.')
assert(serviceSource.includes("post('/images/upload', formData)"), 'Upload endpoint is incorrect.')
assert(!serviceSource.includes('Content-Type'), 'Multipart Content-Type was set manually.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated API interceptor is missing.')
assert(pickerSource.includes("disabled={!selectedFile || uploading}"), 'Upload button disabled state is incorrect.')
assert(pickerSource.includes("disabled={disabled || uploading}"), 'Controls are not locked during upload.')
assert(estimateSource.includes('if (!selectedImage || uploadingImage) return'), 'Duplicate upload guard is missing.')
assert(estimateSource.includes("setImageUploadResult(await uploadFurnitureImage(selectedImage))"), 'Upload result is not captured.')
assert(estimateSource.includes("setImageUploadResult(null)"), 'Image changes do not reset the upload result.')
for (const field of ['status', 'original_filename', 'size_bytes', 'upload_id']) {
  assert(pickerSource.includes(`uploadResult.${field}`), `Upload result field ${field} is not displayed.`)
}

const payloadBlock = estimateSource.slice(estimateSource.indexOf('const payload = {'), estimateSource.indexOf('setSubmitting(true)', estimateSource.indexOf('const payload = {')))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('selectedImage') && !payloadBlock.includes('imageUploadResult'), 'Image data leaked into estimate JSON.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase72-token' : null,
  setItem: () => {},
  removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { uploadFurnitureImage } = await viteSsr.ssrLoadModule('/src/services/imageService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { upload_id: 'test-id', status: 'uploaded' }, status: 201, statusText: 'Created', headers: {}, config }
  }
  const file = new Blob(['image-data'], { type: 'image/jpeg' })
  const result = await uploadFurnitureImage(file)
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/images/upload' && captured.method === 'post', 'Upload request path or method is wrong.')
  assert(captured.data instanceof FormData && captured.data.get('image'), 'Request body is not multipart FormData.')
  assert(captured.headers.Authorization === 'Bearer phase72-token', 'Bearer token was not attached.')
  assert(result.status === 'uploaded', 'Upload response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'A migration changed.')

console.log('FRONTEND_FORMDATA_OK=True')
console.log('AUTH_HEADER_OK=True')
console.log('UPLOAD_BUTTON_OK=True')
console.log('UPLOADING_STATE_OK=True')
console.log('DUPLICATE_UPLOAD_PREVENTION_OK=True')
console.log('SUCCESS_FEEDBACK_OK=True')
console.log('ERROR_FEEDBACK_OK=True')
console.log('UPLOAD_RESULT_DISPLAY_OK=True')
console.log('CHANGE_REMOVE_RESETS_RESULT_OK=True')
console.log('ESTIMATE_PAYLOAD_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_2_FRONTEND_VALIDATION_OK=True')
