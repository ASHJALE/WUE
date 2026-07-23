import { spawnSync } from 'node:child_process'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import React from 'react'
import { renderToString } from 'react-dom/server'
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

const pickerSource = await readFile(path.join(frontendDir, 'src/components/FurnitureImagePicker.jsx'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const styles = await readFile(path.join(frontendDir, 'src/styles/app.css'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Production build failed.')
console.log('NPM_BUILD_OK=True')

assert(estimateSource.includes('<FurnitureImagePicker disabled={submitting} />'), 'Image picker is not on Create Estimate.')
assert(pickerSource.includes('Furniture Image') && pickerSource.includes('type="file"'), 'Furniture image input is missing.')
assert(pickerSource.includes('accept="image/jpeg,image/png,image/webp"'), 'File input accept list is incorrect.')
assert(pickerSource.includes('5 * 1024 * 1024') && pickerSource.includes('file.size > MAX_FURNITURE_IMAGE_BYTES'), '5 MB validation is missing.')
assert(pickerSource.includes('URL.createObjectURL(file)') && pickerSource.includes('URL.revokeObjectURL(previewUrl)'), 'Object URL lifecycle is incomplete.')
assert(pickerSource.includes('selectedFile.name') && pickerSource.includes('formatImageSize(selectedFile.size)'), 'File metadata is not displayed.')
assert(pickerSource.includes('Change Image') && pickerSource.includes('Remove Image'), 'Image actions are missing.')
assert(pickerSource.includes('htmlFor="furniture-image"') && pickerSource.includes('alt={`Preview of selected furniture file'), 'Accessible label or preview alt text is missing.')
assert(styles.includes('.furniture-image-preview') && styles.includes('@media (max-width: 575.98px)'), 'Responsive image styling is missing.')

const payloadBlock = estimateSource.slice(estimateSource.indexOf('const payload = {'), estimateSource.indexOf('setSubmitting(true)'))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Existing estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('selectedFile') && !payloadBlock.includes('previewUrl'), 'Local image leaked into the backend payload.')

const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const pickerModule = await viteSsr.ssrLoadModule('/src/components/FurnitureImagePicker.jsx')
  assert(pickerModule.validateFurnitureImage({ type: 'image/jpeg', size: 1024 }) === '', 'JPEG should be accepted.')
  assert(pickerModule.validateFurnitureImage({ type: 'image/png', size: 1024 }) === '', 'PNG should be accepted.')
  assert(pickerModule.validateFurnitureImage({ type: 'image/webp', size: 1024 }) === '', 'WebP should be accepted.')
  assert(pickerModule.validateFurnitureImage({ type: 'image/gif', size: 1024 }).includes('Unsupported file type'), 'Unsupported type was not rejected.')
  assert(pickerModule.validateFurnitureImage({ type: 'image/jpeg', size: 5 * 1024 * 1024 + 1 }).includes('larger than 5 MB'), 'Oversized image was not rejected.')
  assert(pickerModule.formatImageSize(1.5 * 1024 * 1024) === '1.50 MB', 'File size display is incorrect.')
  const html = renderToString(React.createElement(pickerModule.default))
  assert(html.includes('Furniture Image') && html.includes('Choose Image') && html.includes('image/jpeg,image/png,image/webp'), 'Initial picker did not render correctly.')
} finally {
  await viteSsr.close()
}

assert(run('git', ['status', '--porcelain', '--', 'backend'], projectDir).trim() === '', 'Backend files changed.')
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic'], projectDir).trim() === '', 'Migration files changed.')

console.log('IMAGE_INPUT_OK=True')
console.log('JPEG_PNG_WEBP_ONLY=True')
console.log('MAX_5MB_VALIDATION_OK=True')
console.log('IMAGE_PREVIEW_OK=True')
console.log('FILENAME_DISPLAY_OK=True')
console.log('FILE_SIZE_DISPLAY_OK=True')
console.log('CHANGE_IMAGE_OK=True')
console.log('REMOVE_IMAGE_OK=True')
console.log('OBJECT_URL_CLEANUP_OK=True')
console.log('ACCESSIBILITY_OK=True')
console.log('RESPONSIVE_OK=True')
console.log('ESTIMATE_CREATION_UNCHANGED=True')
console.log('BACKEND_UNCHANGED=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('PHASE7_1_VALIDATION_OK=True')
