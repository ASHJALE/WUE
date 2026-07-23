import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(path), 'utf8')
const create = read('src/pages/EstimateCreate.jsx')
const detail = read('src/pages/EstimateDetail.jsx')
const service = read('src/services/phase7IntegrationService.js')
const estimateService = read('src/services/estimateService.js')

const requireText = (source, text, label) => {
  if (!source.includes(text)) throw new Error(`${label}: missing ${text}`)
  console.log(`${label}=True`)
}

requireText(create, 'Save Estimate Results', 'SAVE_BUTTON_OK')
requireText(create, '!quotationPreview', 'BUTTON_DISABLED_BEFORE_QUOTATION_OK')
requireText(create, 'This will save the current AI-assisted estimate results to Estimate #', 'CONFIRMATION_OK')
requireText(service, 'apiClient.post(`/estimates/${estimateId}/integrate-phase7`', 'AUTH_REQUEST_OK')
requireText(create, 'Saving estimate results…', 'SAVING_STATE_OK')
requireText(create, 'savingIntegration) return', 'DUPLICATE_REQUEST_PREVENTION_OK')
requireText(create, 'Estimate results saved', 'SUCCESS_MESSAGE_OK')
requireText(create, 'integrationError', 'ERROR_DISPLAY_OK')
requireText(create, 'Open Estimate Details', 'DETAILS_LINK_OK')
requireText(create, 'setWorkflowDirty(true)', 'DIRTY_STATE_OK')
requireText(create, 'Boolean(integrationResult) && !workflowDirty', 'RESAVE_AFTER_CHANGE_OK')
requireText(detail, 'estimate-detail-image', 'DETAILS_IMAGE_OK')
requireText(detail, 'Selected furniture type', 'DETAILS_SELECTED_TYPE_OK')
requireText(detail, 'Recognized furniture type', 'DETAILS_RECOGNIZED_TYPE_OK')
requireText(detail, 'Number(estimate.recognition_confidence) * 100', 'CONFIDENCE_FORMATTING_OK')
requireText(detail, 'Saved Preliminary Cost', 'SAVED_COST_DISPLAY_OK')
requireText(detail, 'created before AI workflow integration', 'OLD_ESTIMATE_NOTICE_OK')
requireText(detail, 'Preview BOM', 'FRONTEND_PREVIEW_BOM_OK')
requireText(create, 'createEstimate(payload)', 'ESTIMATE_CREATE_PRESENT')
requireText(estimateService, "apiClient.post('/estimates', data)", 'ESTIMATE_PAYLOAD_UNCHANGED')
console.log('PHASE8_1_FRONTEND_VALIDATION_OK=True')
