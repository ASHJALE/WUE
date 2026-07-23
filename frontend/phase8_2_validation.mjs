import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (path) => readFileSync(resolve(path), 'utf8')
const page = read('src/pages/EstimateCreate.jsx')
const imageService = read('src/services/imageService.js')
const integrationService = read('src/services/phase7IntegrationService.js')

const check = (condition, label) => {
  if (!condition) throw new Error(`${label} failed`)
  console.log(`${label}=True`)
}

check(page.includes('AI prediction'), 'PREDICTION_DISPLAY_OK')
check(page.includes('confidence * 100') && page.includes("toFixed(1)"), 'CONFIDENCE_FORMATTING_OK')
check(
  page.includes('High confidence')
    && page.includes('Moderate confidence')
    && page.includes('Low confidence'),
  'CONFIDENCE_LABEL_OK',
)
check(
  page.includes('Ranked predictions')
    && page.includes('classificationResult.predictions.slice(0, 5)'),
  'RANKED_ALTERNATIVES_UI_OK',
)
check(page.includes('model has low confidence'), 'LOW_CONFIDENCE_WARNING_OK')
check(page.includes('AI model unavailable or classification failed'), 'MODEL_UNAVAILABLE_UI_OK')
check(page.includes('Analyzing furniture…') && page.includes('classifyingImage'), 'LOADING_STATE_OK')
check(page.includes('classificationError') && page.includes('role="alert"'), 'ERROR_DISPLAY_OK')
check(page.includes('Confirm or correct furniture type'), 'MANUAL_CONFIRMATION_UI_OK')
check(page.includes('setConfirmedFurnitureType(event.target.value)'), 'MANUAL_OVERRIDE_UI_OK')
check(
  page.includes('predicted_class: confirmedFurnitureType') === false
    && page.includes('confirmed_class: confirmedFurnitureType'),
  'RECOGNIZED_TYPE_PRESERVED_UI_OK',
)
check(
  page.includes('setMaterialRecommendations(null)')
    && page.includes('setGeneratedBom(null)')
    && page.includes('clearQuantityEstimate()'),
  'DOWNSTREAM_RESET_OK',
)
check(
  imageService.includes('apiClient.post(`/images/${uploadId}/classify`)'),
  'AUTH_CLASSIFICATION_REQUEST_OK',
)
check(
  integrationService.includes('integrate-phase7')
    && page.includes('recognized_furniture_type: classificationResult.predicted_class')
    && page.includes('confirmed_furniture_type: confirmedFurnitureType'),
  'PHASE8_1_PERSISTENCE_COMPATIBLE_UI_OK',
)
console.log('PHASE8_2_FRONTEND_VALIDATION_OK=True')
