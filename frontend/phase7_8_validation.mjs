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

const serviceSource = await readFile(path.join(frontendDir, 'src/services/quotationAssemblyService.js'), 'utf8')
const estimateSource = await readFile(path.join(frontendDir, 'src/pages/EstimateCreate.jsx'), 'utf8')
const styles = await readFile(path.join(frontendDir, 'src/styles/app.css'), 'utf8')
const clientSource = await readFile(path.join(frontendDir, 'src/api/client.js'), 'utf8')

const buildOutput = run('npm.cmd', ['run', 'build'])
assert(buildOutput.includes('built in'), 'Frontend production build failed.')
console.log('NPM_BUILD_OK=True')

assert(serviceSource.includes("post('/quotation/assemble', payload)"), 'Quotation assembly request is incorrect.')
assert(clientSource.includes('config.headers.Authorization = `Bearer ${token}`'), 'Authenticated interceptor is missing.')
assert(estimateSource.includes("'Generate Preliminary Quotation'"), 'Generate quotation button is missing.')
assert(estimateSource.includes('disabled={!costResult || assemblingQuotation}'), 'Generate button disabled state is incorrect.')
assert(estimateSource.includes('if (!costResult || assemblingQuotation) return'), 'Duplicate quotation request guard is missing.')
assert(estimateSource.includes('Generating quotation…') && estimateSource.includes('spinner-border'), 'Quotation loading state is missing.')
for (const id of ['quotation-customer-name', 'quotation-project-name', 'quotation-location']) {
  assert(estimateSource.includes(`id="${id}"`), `Customer field ${id} is missing.`)
}
for (const heading of [
  'WUE Quotation Preview', 'Customer and Project', 'Furniture', 'Recommended Materials',
  'Bill of Materials', 'Quantity Estimates', 'Cost Summary', 'Assumptions',
]) {
  assert(estimateSource.includes(heading), `Quotation section ${heading} is missing.`)
}
for (const section of ['quotationPreview.recommendations', 'quotationPreview.bom', 'quotationPreview.quantity_estimates', 'quotationPreview.cost_summary']) {
  assert(estimateSource.includes(section), `Preview binding ${section} is missing.`)
}
assert(estimateSource.includes('PRELIMINARY'), 'Preliminary badge is missing.')
assert(estimateSource.includes('phpCurrency.format'), 'PHP formatting is missing.')
assert(styles.includes('@media print') && styles.includes('.quotation-preview'), 'Print-friendly layout is missing.')
assert(estimateSource.includes('This quotation is not yet saved.'), 'Unsaved notice is missing.')
assert(estimateSource.includes('PDF export will be available in a future phase.'), 'Future PDF notice is missing.')
assert(estimateSource.includes('quotationRequestId.current += 1'), 'Stale quotation invalidation is missing.')

const costResetStart = estimateSource.indexOf('function clearCostResult')
const costResetBlock = estimateSource.slice(costResetStart, estimateSource.indexOf('\n  }', costResetStart) + 4)
assert(costResetBlock.includes('clearQuotationPreview()'), 'Upstream cost reset does not clear quotation preview.')
const customerStart = estimateSource.indexOf('function handleQuotationCustomerChange')
const customerBlock = estimateSource.slice(customerStart, estimateSource.indexOf('\n  }', customerStart) + 4)
assert(customerBlock.includes('clearQuotationPreview()'), 'Customer changes do not clear quotation preview.')

const payloadStart = estimateSource.indexOf('const payload = {')
const payloadBlock = estimateSource.slice(payloadStart, estimateSource.indexOf('setSubmitting(true)', payloadStart))
for (const field of ['user_id', 'input_method', 'selected_furniture_type_id', 'recognized_furniture_type_id', 'image_path', 'recognition_confidence']) {
  assert(payloadBlock.includes(field), `Estimate payload field ${field} changed.`)
}
assert(!payloadBlock.includes('quotationPreview') && !payloadBlock.includes('costResult'), 'Phase 7 quotation data leaked into estimate payload.')

globalThis.localStorage = {
  getItem: (key) => key === 'wue_access_token' ? 'phase78-token' : null,
  setItem: () => {}, removeItem: () => {},
}
globalThis.window = new EventTarget()
const viteSsr = await createServer({ server: { middlewareMode: true }, appType: 'custom', optimizeDeps: { noDiscovery: true, include: [] } })
try {
  const { default: apiClient } = await viteSsr.ssrLoadModule('/src/api/client.js')
  const { assemblePreliminaryQuotation } = await viteSsr.ssrLoadModule('/src/services/quotationAssemblyService.js')
  const originalAdapter = apiClient.defaults.adapter
  let captured
  apiClient.defaults.adapter = async (config) => {
    captured = config
    return { data: { quotation_id: 'TMP-20260724-0001', status: 'preliminary', currency: 'PHP' }, status: 200, statusText: 'OK', headers: {}, config }
  }
  const payload = {
    customer: { name: 'Sample Customer', project_name: 'Dining Set', location: 'Angeles City' },
    classification: { predicted_class: 'chair' }, recommendations: [{}], bom: [{}],
    quantity_estimates: [{}], cost_summary: {},
  }
  const result = await assemblePreliminaryQuotation(payload)
  apiClient.defaults.adapter = originalAdapter
  assert(captured.url === '/quotation/assemble' && captured.method === 'post', 'Quotation endpoint request is wrong.')
  assert(JSON.stringify(JSON.parse(captured.data)) === JSON.stringify(payload), 'Quotation assembly payload changed.')
  assert(captured.headers.Authorization === 'Bearer phase78-token', 'Bearer token was not attached.')
  assert(result.status === 'preliminary' && result.currency === 'PHP', 'Quotation response was not returned.')
} finally {
  await viteSsr.close()
}

run('git', ['diff', '--check'], projectDir)
run('git', ['diff', '--cached', '--check'], projectDir)
assert(run('git', ['status', '--porcelain', '--', 'backend/alembic', 'backend/app/models'], projectDir).trim() === '', 'A migration or model changed.')

console.log('GENERATE_BUTTON_OK=True')
console.log('BUTTON_DISABLED_BEFORE_COST_OK=True')
console.log('AUTH_REQUEST_OK=True')
console.log('LOADING_STATE_OK=True')
console.log('DUPLICATE_REQUEST_OK=True')
console.log('HEADER_DISPLAY_OK=True')
console.log('CUSTOMER_DISPLAY_OK=True')
console.log('FURNITURE_DISPLAY_OK=True')
console.log('RECOMMENDATIONS_DISPLAY_OK=True')
console.log('BOM_DISPLAY_OK=True')
console.log('QUANTITY_DISPLAY_OK=True')
console.log('COST_DISPLAY_OK=True')
console.log('ASSUMPTIONS_DISPLAY_OK=True')
console.log('DISCLAIMER_DISPLAY_OK=True')
console.log('PRELIMINARY_BADGE_OK=True')
console.log('PHP_FORMATTING_OK=True')
console.log('PRINT_LAYOUT_OK=True')
console.log('UNSAVED_NOTICE_OK=True')
console.log('PDF_NOTICE_OK=True')
console.log('RESET_ON_UPSTREAM_CHANGE_OK=True')
console.log('NO_NEW_MIGRATIONS=True')
console.log('GIT_DIFF_CHECK_OK=True')
console.log('PHASE7_8_FRONTEND_VALIDATION_OK=True')
