import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { ErrorAlert } from '../components/AppFeedback.jsx'
import FurnitureImagePicker from '../components/FurnitureImagePicker.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { createEstimate, getEstimates, getFurnitureTypes } from '../services/estimateService.js'
import { classifyFurnitureImage, uploadFurnitureImage } from '../services/imageService.js'
import { recommendMaterials } from '../services/materialRecommendationService.js'
import { generateStructuredBom } from '../services/bomGenerationService.js'
import { estimateBomQuantities } from '../services/quantityEstimationService.js'
import { calculatePreliminaryCost } from '../services/costCalculationService.js'
import { assemblePreliminaryQuotation } from '../services/quotationAssemblyService.js'
import { integratePhase7Estimate } from '../services/phase7IntegrationService.js'

const furnitureClassNames = {
  chair: 'Chair',
  bed: 'Bed',
  sofa: 'Sofa',
  dining_table: 'Dining Table',
  lamp_shade: 'Lamp Shade',
}

function confidenceLabel(confidence) {
  if (confidence >= 0.8) return 'High confidence'
  if (confidence >= 0.5) return 'Moderate confidence'
  return 'Low confidence'
}

const initialForm = {
  input_method: 'predefined',
  selected_furniture_type_id: '',
  recognized_furniture_type_id: '',
  image_path: '',
  recognition_confidence: '',
}

const dimensionDefaults = {
  chair: { width: '450', depth: '500', height: '900' },
  bed: { width: '1600', depth: '2000', height: '1000' },
  sofa: { width: '2100', depth: '900', height: '850' },
  dining_table: { width: '1800', depth: '900', height: '750' },
  lamp_shade: { width: '350', depth: '350', height: '600' },
}

const laborHourDefaults = {
  chair: '8',
  bed: '14',
  sofa: '18',
  dining_table: '12',
  lamp_shade: '5',
}

const phpCurrency = new Intl.NumberFormat('en-PH', {
  style: 'currency',
  currency: 'PHP',
  minimumFractionDigits: 2,
})

export default function EstimateCreate() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [furnitureTypes, setFurnitureTypes] = useState([])
  const [ownedEstimates, setOwnedEstimates] = useState([])
  const [targetEstimateId, setTargetEstimateId] = useState('')
  const [loadingTypes, setLoadingTypes] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [selectedImage, setSelectedImage] = useState(null)
  const [uploadingImage, setUploadingImage] = useState(false)
  const [imageUploadError, setImageUploadError] = useState('')
  const [imageUploadResult, setImageUploadResult] = useState(null)
  const [classifyingImage, setClassifyingImage] = useState(false)
  const [classificationError, setClassificationError] = useState('')
  const [classificationResult, setClassificationResult] = useState(null)
  const [confirmedFurnitureType, setConfirmedFurnitureType] = useState('')
  const [classificationConfirmed, setClassificationConfirmed] = useState(false)
  const [recommendingMaterials, setRecommendingMaterials] = useState(false)
  const [recommendationError, setRecommendationError] = useState('')
  const [materialRecommendations, setMaterialRecommendations] = useState(null)
  const [generatingBom, setGeneratingBom] = useState(false)
  const [bomError, setBomError] = useState('')
  const [generatedBom, setGeneratedBom] = useState(null)
  const [dimensions, setDimensions] = useState(dimensionDefaults.chair)
  const [estimatingQuantities, setEstimatingQuantities] = useState(false)
  const [quantityError, setQuantityError] = useState('')
  const [quantityEstimates, setQuantityEstimates] = useState(null)
  const [costInputs, setCostInputs] = useState({ labor_hours: '8', hourly_rate: '150', profit_margin_percent: '20' })
  const [calculatingCost, setCalculatingCost] = useState(false)
  const [costError, setCostError] = useState('')
  const [costResult, setCostResult] = useState(null)
  const [quotationCustomer, setQuotationCustomer] = useState({
    name: 'Sample Customer',
    project_name: 'Furniture Project',
    location: 'Angeles City',
  })
  const [assemblingQuotation, setAssemblingQuotation] = useState(false)
  const [quotationError, setQuotationError] = useState('')
  const [quotationPreview, setQuotationPreview] = useState(null)
  const [savingIntegration, setSavingIntegration] = useState(false)
  const [integrationError, setIntegrationError] = useState('')
  const [integrationResult, setIntegrationResult] = useState(null)
  const [workflowDirty, setWorkflowDirty] = useState(false)
  const recommendationRequestId = useRef(0)
  const classificationRequestId = useRef(0)
  const bomRequestId = useRef(0)
  const quantityRequestId = useRef(0)
  const costRequestId = useRef(0)
  const quotationRequestId = useRef(0)
  const integrationRequestId = useRef(0)

  useEffect(() => {
    let active = true
    Promise.all([getFurnitureTypes(), getEstimates({ user_id: user.id, limit: 200 })])
      .then(([types, estimates]) => {
        if (!active) return
        setFurnitureTypes(types.filter((item) => item.is_active))
        setOwnedEstimates(estimates)
        if (estimates.length) setTargetEstimateId(String(estimates[0].id))
      })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError, 'Furniture types could not be loaded.')) })
      .finally(() => { if (active) setLoadingTypes(false) })
    return () => { active = false }
  }, [user.id])

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
  }

  function clearQuantityEstimate() {
    setEstimatingQuantities(false)
    setQuantityError('')
    setQuantityEstimates(null)
    quantityRequestId.current += 1
    clearCostResult()
  }

  function clearCostResult() {
    setCalculatingCost(false)
    setCostError('')
    setCostResult(null)
    costRequestId.current += 1
    clearQuotationPreview()
  }

  function clearQuotationPreview() {
    setAssemblingQuotation(false)
    setQuotationError('')
    setQuotationPreview(null)
    quotationRequestId.current += 1
    setSavingIntegration(false)
    setIntegrationError('')
    integrationRequestId.current += 1
    if (integrationResult) setWorkflowDirty(true)
  }

  function handleDimensionChange(event) {
    setDimensions((current) => ({ ...current, [event.target.name]: event.target.value }))
    clearQuantityEstimate()
  }

  function handleCostInputChange(event) {
    setCostInputs((current) => ({ ...current, [event.target.name]: event.target.value }))
    clearCostResult()
  }

  function handleQuotationCustomerChange(event) {
    setQuotationCustomer((current) => ({ ...current, [event.target.name]: event.target.value }))
    clearQuotationPreview()
  }

  function handleTargetEstimateChange(event) {
    setTargetEstimateId(event.target.value)
    setIntegrationResult(null)
    setIntegrationError('')
    setWorkflowDirty(Boolean(quotationPreview))
    integrationRequestId.current += 1
  }

  function handleImageChange(file) {
    setSelectedImage(file)
    setImageUploadError('')
    setImageUploadResult(null)
    setClassificationError('')
    setClassificationResult(null)
    setConfirmedFurnitureType('')
    setClassificationConfirmed(false)
    setRecommendationError('')
    setMaterialRecommendations(null)
    setRecommendingMaterials(false)
    recommendationRequestId.current += 1
    setClassifyingImage(false)
    classificationRequestId.current += 1
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
  }

  async function handleImageUpload() {
    if (!selectedImage || uploadingImage) return
    setUploadingImage(true)
    setImageUploadError('')
    setImageUploadResult(null)
    setClassificationError('')
    setClassificationResult(null)
    setConfirmedFurnitureType('')
    setClassificationConfirmed(false)
    setRecommendationError('')
    setMaterialRecommendations(null)
    setRecommendingMaterials(false)
    recommendationRequestId.current += 1
    setClassifyingImage(false)
    classificationRequestId.current += 1
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
    try {
      setImageUploadResult(await uploadFurnitureImage(selectedImage))
    } catch (requestError) {
      setImageUploadError(getApiErrorMessage(requestError, 'The furniture image could not be uploaded.'))
    } finally {
      setUploadingImage(false)
    }
  }

  async function handleImageClassification() {
    if (!imageUploadResult || classifyingImage) return
    const requestId = classificationRequestId.current + 1
    classificationRequestId.current = requestId
    setClassifyingImage(true)
    setClassificationError('')
    setClassificationResult(null)
    setConfirmedFurnitureType('')
    setClassificationConfirmed(false)
    setRecommendationError('')
    setMaterialRecommendations(null)
    setRecommendingMaterials(false)
    recommendationRequestId.current += 1
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
    try {
      const result = await classifyFurnitureImage(imageUploadResult.upload_id)
      if (classificationRequestId.current === requestId) {
        setClassificationResult(result)
        setConfirmedFurnitureType(result.predicted_class)
      }
    } catch (requestError) {
      if (classificationRequestId.current === requestId) {
        setClassificationError(getApiErrorMessage(requestError, 'The furniture image could not be analyzed.'))
      }
    } finally {
      if (classificationRequestId.current === requestId) setClassifyingImage(false)
    }
  }

  function handleConfirmedTypeChange(event) {
    setConfirmedFurnitureType(event.target.value)
    setClassificationConfirmed(false)
    setRecommendationError('')
    setMaterialRecommendations(null)
    setRecommendingMaterials(false)
    recommendationRequestId.current += 1
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
  }

  function confirmFurnitureType() {
    setClassificationConfirmed(true)
    setRecommendationError('')
    setMaterialRecommendations(null)
    setRecommendingMaterials(false)
    recommendationRequestId.current += 1
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
  }

  async function handleMaterialRecommendation() {
    if (!classificationConfirmed || !confirmedFurnitureType || recommendingMaterials) return
    const requestId = recommendationRequestId.current + 1
    recommendationRequestId.current = requestId
    setRecommendingMaterials(true)
    setRecommendationError('')
    setGeneratingBom(false)
    setBomError('')
    setGeneratedBom(null)
    bomRequestId.current += 1
    clearQuantityEstimate()
    try {
      const result = await recommendMaterials(confirmedFurnitureType)
      if (recommendationRequestId.current === requestId) setMaterialRecommendations(result)
    } catch (requestError) {
      if (recommendationRequestId.current === requestId) {
        setRecommendationError(getApiErrorMessage(requestError, 'Materials could not be recommended.'))
      }
    } finally {
      if (recommendationRequestId.current === requestId) setRecommendingMaterials(false)
    }
  }

  async function handleBomGeneration() {
    if (!materialRecommendations || generatingBom) return
    const requestId = bomRequestId.current + 1
    bomRequestId.current = requestId
    setGeneratingBom(true)
    setBomError('')
    clearQuantityEstimate()
    try {
      const result = await generateStructuredBom(
        materialRecommendations.furniture_type,
        materialRecommendations.materials,
      )
      if (bomRequestId.current === requestId) {
        setGeneratedBom(result)
        setDimensions(dimensionDefaults[result.furniture_type])
      }
    } catch (requestError) {
      if (bomRequestId.current === requestId) {
        setBomError(getApiErrorMessage(requestError, 'The structured BOM could not be generated.'))
      }
    } finally {
      if (bomRequestId.current === requestId) setGeneratingBom(false)
    }
  }

  async function handleQuantityEstimation() {
    if (!generatedBom || estimatingQuantities) return
    const numericDimensions = Object.fromEntries(
      Object.entries(dimensions).map(([key, value]) => [key, Number(value)]),
    )
    if (Object.values(numericDimensions).some((value) => !Number.isFinite(value) || value <= 0)) {
      setQuantityError('Width, depth, and height must all be positive numbers.')
      setQuantityEstimates(null)
      return
    }
    const requestId = quantityRequestId.current + 1
    quantityRequestId.current = requestId
    setEstimatingQuantities(true)
    setQuantityError('')
    clearCostResult()
    try {
      const result = await estimateBomQuantities(
        generatedBom.furniture_type,
        numericDimensions,
        generatedBom.components,
      )
      if (quantityRequestId.current === requestId) {
        setQuantityEstimates(result)
        setCostInputs((current) => ({
          ...current,
          labor_hours: laborHourDefaults[result.furniture_type],
        }))
      }
    } catch (requestError) {
      if (quantityRequestId.current === requestId) {
        setQuantityError(getApiErrorMessage(requestError, 'Material quantities could not be estimated.'))
      }
    } finally {
      if (quantityRequestId.current === requestId) setEstimatingQuantities(false)
    }
  }

  async function handleCostCalculation() {
    if (!quantityEstimates || calculatingCost) return
    const laborHours = Number(costInputs.labor_hours)
    const hourlyRate = Number(costInputs.hourly_rate)
    const profitMargin = Number(costInputs.profit_margin_percent)
    if (!Number.isFinite(laborHours) || laborHours < 0) {
      setCostError('Labor hours must be zero or greater.')
      return
    }
    if (!Number.isFinite(hourlyRate) || hourlyRate < 0) {
      setCostError('Hourly rate must be zero or greater.')
      return
    }
    if (!Number.isFinite(profitMargin) || profitMargin < 0 || profitMargin > 100) {
      setCostError('Profit margin must be between 0 and 100 percent.')
      return
    }
    const requestId = costRequestId.current + 1
    costRequestId.current = requestId
    setCalculatingCost(true)
    setCostError('')
    clearQuotationPreview()
    try {
      const result = await calculatePreliminaryCost(
        quantityEstimates.furniture_type,
        quantityEstimates.components,
        { hours: laborHours, hourly_rate: hourlyRate },
        profitMargin,
      )
      if (costRequestId.current === requestId) setCostResult(result)
    } catch (requestError) {
      if (costRequestId.current === requestId) {
        setCostError(getApiErrorMessage(requestError, 'The preliminary cost could not be calculated.'))
      }
    } finally {
      if (costRequestId.current === requestId) setCalculatingCost(false)
    }
  }

  async function handleQuotationAssembly() {
    if (!costResult || assemblingQuotation) return
    if (Object.values(quotationCustomer).some((value) => !value.trim())) {
      setQuotationError('Customer name, project name, and location are required.')
      return
    }
    const requestId = quotationRequestId.current + 1
    quotationRequestId.current = requestId
    setAssemblingQuotation(true)
    setQuotationError('')
    try {
      const classification = {
        ...classificationResult,
        confirmed_class: confirmedFurnitureType,
      }
      const result = await assemblePreliminaryQuotation({
        customer: quotationCustomer,
        classification,
        recommendations: materialRecommendations.materials,
        bom: generatedBom.components,
        quantity_estimates: quantityEstimates.components,
        cost_summary: costResult,
      })
      if (quotationRequestId.current === requestId) setQuotationPreview(result)
    } catch (requestError) {
      if (quotationRequestId.current === requestId) {
        setQuotationError(getApiErrorMessage(requestError, 'The preliminary quotation could not be assembled.'))
      }
    } finally {
      if (quotationRequestId.current === requestId) setAssemblingQuotation(false)
    }
  }

  async function handlePhase7Integration() {
    if (!quotationPreview || !targetEstimateId || savingIntegration) return
    const confirmed = window.confirm(
      `This will save the current AI-assisted estimate results to Estimate #${targetEstimateId}.`,
    )
    if (!confirmed) return
    const requestId = integrationRequestId.current + 1
    integrationRequestId.current = requestId
    setSavingIntegration(true)
    setIntegrationError('')
    try {
      const result = await integratePhase7Estimate(targetEstimateId, {
        upload: {
          upload_id: imageUploadResult.upload_id,
          image_path: `uploads/furniture/${imageUploadResult.stored_filename}`,
        },
        classification: {
          recognized_furniture_type: classificationResult.predicted_class,
          confirmed_furniture_type: confirmedFurnitureType,
          confidence: classificationResult.confidence,
        },
        dimensions: {
          width: Number(dimensions.width),
          depth: Number(dimensions.depth),
          height: Number(dimensions.height),
          unit: 'mm',
        },
        recommendations: materialRecommendations.materials,
        bom: generatedBom.components,
        quantity_estimates: quantityEstimates.components,
        cost_summary: costResult,
        preliminary_quotation: quotationPreview,
      })
      if (integrationRequestId.current === requestId) {
        setIntegrationResult(result)
        setWorkflowDirty(false)
      }
    } catch (requestError) {
      if (integrationRequestId.current === requestId) {
        setIntegrationError(getApiErrorMessage(requestError, 'Estimate results could not be saved.'))
      }
    } finally {
      if (integrationRequestId.current === requestId) setSavingIntegration(false)
    }
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!form.input_method) {
      setError('Select an input method.')
      return
    }
    if (form.input_method === 'image_upload' && !form.image_path.trim()) {
      setError('Image upload requires an image path.')
      return
    }
    const hasRecognizedType = Boolean(form.recognized_furniture_type_id)
    const hasConfidence = form.recognition_confidence !== ''
    if (hasRecognizedType !== hasConfidence) {
      setError('Recognized furniture type and confidence must be supplied together.')
      return
    }
    if (hasConfidence) {
      const confidence = Number(form.recognition_confidence)
      if (Number.isNaN(confidence) || confidence < 0 || confidence > 1) {
        setError('Recognition confidence must be between 0 and 1.')
        return
      }
    }

    const payload = {
      user_id: user.id,
      input_method: form.input_method,
      selected_furniture_type_id: form.selected_furniture_type_id ? Number(form.selected_furniture_type_id) : null,
      recognized_furniture_type_id: form.recognized_furniture_type_id ? Number(form.recognized_furniture_type_id) : null,
      image_path: form.image_path.trim() || null,
      recognition_confidence: hasConfidence ? form.recognition_confidence : null,
    }
    setSubmitting(true)
    try {
      const created = await createEstimate(payload)
      navigate(`/estimates/${created.id}`, { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Estimate creation failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-lg-8">
        <section className="card border-0 shadow-sm">
          <div className="card-body p-4 p-md-5">
            <div className="d-flex align-items-center justify-content-between gap-3 mb-4">
              <div><h1 className="h2 mb-1">Create estimate</h1><p className="text-secondary mb-0">Enter the fields supported by the WUE estimate API.</p></div>
              <Link className="btn btn-outline-secondary" to="/estimates">Cancel</Link>
            </div>
            {error && <ErrorAlert message={error} />}
            <form onSubmit={handleSubmit} noValidate>
              <FurnitureImagePicker
                disabled={submitting}
                onFileChange={handleImageChange}
                onUpload={handleImageUpload}
                uploadError={imageUploadError}
                uploading={uploadingImage}
                uploadResult={imageUploadResult}
              />
              <section className="card border-0 bg-light mb-4" aria-labelledby="classification-heading">
                <div className="card-body p-3 p-md-4">
                  <h2 className="h5" id="classification-heading">Furniture Classification</h2>
                  <p className="text-secondary small">Analyze an uploaded image with the configured local WUE classifier.</p>
                  <button
                    className="btn btn-outline-success"
                    disabled={!imageUploadResult || classifyingImage}
                    onClick={handleImageClassification}
                    type="button"
                  >
                    {classifyingImage && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                    {classifyingImage ? 'Analyzing furniture…' : 'Analyze Furniture'}
                  </button>
                  {!imageUploadResult && <p className="text-secondary small mt-2 mb-0">Upload an image before analysis.</p>}
                  {classificationError && (
                    <div className="alert alert-danger mt-3 mb-0" role="alert">
                      <strong>AI model unavailable or classification failed.</strong>{' '}
                      {classificationError} You can continue using the predefined furniture selection in the estimate form.
                    </div>
                  )}
                  {classificationResult && (
                    <div className="classification-result mt-4" aria-live="polite">
                      {classificationResult.model.mode === 'development_fallback' && (
                        <div className="alert alert-warning" role="note">
                          <strong>Development fallback:</strong> this is not a trained-model prediction and must not be treated as production AI.
                        </div>
                      )}
                      {classificationResult.low_confidence && (
                        <div className="alert alert-warning" role="note">
                          The model has low confidence. Review the alternatives and manually confirm the correct furniture type.
                        </div>
                      )}
                      <dl className="row mb-3">
                        <dt className="col-sm-5">AI prediction</dt><dd className="col-sm-7">{classificationResult.recognized_furniture_type.name}</dd>
                        <dt className="col-sm-5">Confidence</dt><dd className="col-sm-7">{(classificationResult.confidence * 100).toFixed(1)}% — {confidenceLabel(classificationResult.confidence)}</dd>
                        <dt className="col-sm-5">Model</dt><dd className="col-sm-7">{classificationResult.model.backend} / {classificationResult.model.version}</dd>
                      </dl>
                      <section aria-labelledby="ranked-predictions-heading" className="mb-3">
                        <h3 className="h6" id="ranked-predictions-heading">Ranked predictions</h3>
                        <ol className="list-group list-group-numbered">
                          {classificationResult.predictions.slice(0, 5).map((prediction) => (
                            <li className="list-group-item d-flex justify-content-between align-items-center" key={prediction.key}>
                              <span>{prediction.name}</span>
                              <span aria-label={`${prediction.name} confidence ${(prediction.confidence * 100).toFixed(1)} percent`}>
                                {(prediction.confidence * 100).toFixed(1)}%
                              </span>
                            </li>
                          ))}
                        </ol>
                      </section>
                      <label className="form-label" htmlFor="confirmed-furniture-type">Confirm or correct furniture type</label>
                      <select
                        className="form-select"
                        id="confirmed-furniture-type"
                        onChange={handleConfirmedTypeChange}
                        value={confirmedFurnitureType}
                      >
                        {classificationResult.supported_classes.map((item) => (
                          <option key={item} value={item}>{furnitureClassNames[item]}</option>
                        ))}
                      </select>
                      <button className="btn btn-success mt-3" onClick={confirmFurnitureType} type="button">
                        Confirm Furniture Type
                      </button>
                      <p className="text-secondary small mt-2 mb-0">The AI prediction is advisory and requires user confirmation.</p>
                      {classificationConfirmed && (
                        <p className="alert alert-success mt-3 mb-0" role="status">
                          Confirmed furniture type: {furnitureClassNames[confirmedFurnitureType]}
                        </p>
                      )}
                    </div>
                  )}
                </div>
              </section>
              <section className="card border-0 bg-light mb-4" aria-labelledby="recommendation-heading">
                <div className="card-body p-3 p-md-4">
                  <div className="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2">
                    <div>
                      <h2 className="h5 mb-1" id="recommendation-heading">Material Recommendations</h2>
                      <p className="text-secondary small mb-0">Get configurable suggestions for the confirmed furniture type.</p>
                    </div>
                    <button
                      className="btn btn-outline-success flex-shrink-0"
                      disabled={!classificationConfirmed || !confirmedFurnitureType || recommendingMaterials}
                      onClick={handleMaterialRecommendation}
                      type="button"
                    >
                      {recommendingMaterials && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                      {recommendingMaterials ? 'Recommending materials…' : 'Recommend Materials'}
                    </button>
                  </div>
                  {!classificationConfirmed && <p className="text-secondary small mt-3 mb-0">Confirm a furniture type to enable recommendations.</p>}
                  {recommendationError && <div className="alert alert-danger mt-3 mb-0" role="alert">{recommendationError}</div>}
                  {materialRecommendations && (
                    <div className="mt-4" aria-live="polite">
                      <p className="fw-semibold">{materialRecommendations.materials.length} recommended materials</p>
                      {['Primary', 'Alternative'].map((priority) => (
                        <section className="mb-4" key={priority} aria-labelledby={`${priority.toLowerCase()}-materials-heading`}>
                          <h3 className="h6" id={`${priority.toLowerCase()}-materials-heading`}>{priority} Materials</h3>
                          <ul className="row g-3 list-unstyled mb-0">
                            {materialRecommendations.materials.filter((item) => item.priority === priority).map((item) => (
                              <li className="col-md-6" key={`${priority}-${item.name}`}>
                                <article className="card border-0 shadow-sm h-100">
                                  <div className="card-body">
                                    <div className="d-flex flex-wrap gap-2 mb-2">
                                      <span className={`badge ${priority === 'Primary' ? 'text-bg-success' : 'text-bg-secondary'}`}>{item.priority}</span>
                                      <span className="badge text-bg-light border">{item.quality}</span>
                                    </div>
                                    <h4 className="h6 mb-1">{item.name}</h4>
                                    <p className="small text-secondary mb-2">{item.category}</p>
                                    <p className="small mb-0">{item.reason}</p>
                                  </div>
                                </article>
                              </li>
                            ))}
                          </ul>
                        </section>
                      ))}
                      <div className="alert alert-info mb-0" role="note">
                        These recommendations are configurable and may be refined after production AI integration.
                      </div>
                    </div>
                  )}
                </div>
              </section>
              <section className="card border-0 bg-light mb-4" aria-labelledby="generated-bom-heading">
                <div className="card-body p-3 p-md-4">
                  <div className="d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-2">
                    <div>
                      <h2 className="h5 mb-1" id="generated-bom-heading">Structured Bill of Materials</h2>
                      <p className="text-secondary small mb-0">Convert the current recommendations into furniture components.</p>
                    </div>
                    <button
                      className="btn btn-outline-success flex-shrink-0"
                      disabled={!materialRecommendations || generatingBom}
                      onClick={handleBomGeneration}
                      type="button"
                    >
                      {generatingBom && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                      {generatingBom ? 'Generating BOM…' : 'Generate BOM'}
                    </button>
                  </div>
                  {!materialRecommendations && <p className="text-secondary small mt-3 mb-0">Generate material recommendations before creating a BOM.</p>}
                  {bomError && <div className="alert alert-danger mt-3 mb-0" role="alert">{bomError}</div>}
                  {generatedBom && (
                    <div className="mt-4" aria-live="polite">
                      <p className="fw-semibold">{generatedBom.components.length} BOM components</p>
                      <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                          <caption className="visually-hidden">Generated bill of materials components</caption>
                          <thead><tr>
                            <th scope="col">Component</th>
                            <th scope="col">Recommended Material</th>
                            <th scope="col">Category</th>
                            <th scope="col">Source</th>
                            <th scope="col">Unit</th>
                            <th scope="col">Notes</th>
                          </tr></thead>
                          <tbody>
                            {generatedBom.components.map((item) => (
                              <tr key={item.component}>
                                <th scope="row">{item.component}</th>
                                <td>{item.recommended_material}</td>
                                <td>{item.category}</td>
                                <td>{item.source}</td>
                                <td>{item.unit}</td>
                                <td>{item.notes}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="alert alert-info mt-3 mb-0" role="note">
                        Quantities will be calculated during the next estimation phase.
                      </div>
                    </div>
                  )}
                </div>
              </section>
              <section className="card border-0 bg-light mb-4" aria-labelledby="quantity-estimate-heading">
                <div className="card-body p-3 p-md-4">
                  <h2 className="h5" id="quantity-estimate-heading">Preliminary Quantity Estimate</h2>
                  <p className="text-secondary small">Enter overall furniture dimensions in millimeters.</p>
                  <fieldset disabled={!generatedBom || estimatingQuantities}>
                    <legend className="visually-hidden">Furniture dimensions</legend>
                    <div className="row g-3">
                      {['width', 'depth', 'height'].map((dimension) => (
                        <div className="col-sm-4" key={dimension}>
                          <label className="form-label text-capitalize" htmlFor={`dimension-${dimension}`}>{dimension} (mm)</label>
                          <input
                            className="form-control"
                            id={`dimension-${dimension}`}
                            min="1"
                            name={dimension}
                            onChange={handleDimensionChange}
                            required
                            step="1"
                            type="number"
                            value={dimensions[dimension]}
                          />
                        </div>
                      ))}
                    </div>
                  </fieldset>
                  <button
                    className="btn btn-outline-success mt-3"
                    disabled={!generatedBom || estimatingQuantities}
                    onClick={handleQuantityEstimation}
                    type="button"
                  >
                    {estimatingQuantities && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                    {estimatingQuantities ? 'Estimating quantities…' : 'Estimate Quantities'}
                  </button>
                  {!generatedBom && <p className="text-secondary small mt-2 mb-0">Generate a structured BOM before estimating quantities.</p>}
                  {quantityError && <div className="alert alert-danger mt-3 mb-0" role="alert">{quantityError}</div>}
                  {quantityEstimates && (
                    <div className="mt-4" aria-live="polite">
                      <div className="d-flex flex-column flex-md-row justify-content-between gap-2 mb-3">
                        <p className="fw-semibold mb-0">{quantityEstimates.components.length} estimated components</p>
                        <p className="text-secondary small mb-0">
                          Dimensions: {dimensions.width} × {dimensions.depth} × {dimensions.height} mm (W × D × H)
                        </p>
                      </div>
                      <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                          <caption className="visually-hidden">Preliminary component quantity estimates</caption>
                          <thead><tr>
                            <th scope="col">Component</th>
                            <th scope="col">Material</th>
                            <th scope="col">Estimated Quantity</th>
                            <th scope="col">Unit</th>
                            <th scope="col">Calculation Basis</th>
                            <th scope="col">Confidence</th>
                          </tr></thead>
                          <tbody>
                            {quantityEstimates.components.map((item) => (
                              <tr key={item.component}>
                                <th scope="row">{item.component}</th>
                                <td>{item.material}</td>
                                <td>{item.estimated_quantity}</td>
                                <td>{item.unit}</td>
                                <td>{item.calculation_basis}</td>
                                <td>{item.confidence}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <div className="alert alert-warning mt-3 mb-0" role="note">
                        These are preliminary engineering estimates and will be refined during pricing.
                      </div>
                    </div>
                  )}
                </div>
              </section>
              <section className="card border-0 bg-light mb-4" aria-labelledby="cost-calculation-heading">
                <div className="card-body p-3 p-md-4">
                  <h2 className="h5" id="cost-calculation-heading">Preliminary Cost Calculation</h2>
                  <p className="text-secondary small">Configure labor and profit assumptions for the current quantity estimate.</p>
                  <fieldset disabled={!quantityEstimates || calculatingCost}>
                    <legend className="visually-hidden">Labor and profit inputs</legend>
                    <div className="row g-3">
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="labor-hours">Labor Hours</label>
                        <input className="form-control" id="labor-hours" min="0" name="labor_hours" onChange={handleCostInputChange} required step="0.25" type="number" value={costInputs.labor_hours} />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="hourly-rate">Hourly Rate (PHP)</label>
                        <input className="form-control" id="hourly-rate" min="0" name="hourly_rate" onChange={handleCostInputChange} required step="0.01" type="number" value={costInputs.hourly_rate} />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="profit-margin-percent">Profit Margin (%)</label>
                        <input className="form-control" id="profit-margin-percent" max="100" min="0" name="profit_margin_percent" onChange={handleCostInputChange} required step="0.01" type="number" value={costInputs.profit_margin_percent} />
                      </div>
                    </div>
                  </fieldset>
                  <button
                    className="btn btn-outline-success mt-3"
                    disabled={!quantityEstimates || calculatingCost}
                    onClick={handleCostCalculation}
                    type="button"
                  >
                    {calculatingCost && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                    {calculatingCost ? 'Calculating cost…' : 'Calculate Cost'}
                  </button>
                  {!quantityEstimates && <p className="text-secondary small mt-2 mb-0">Estimate component quantities before calculating cost.</p>}
                  {costError && <div className="alert alert-danger mt-3 mb-0" role="alert">{costError}</div>}
                  {costResult && (
                    <div className="mt-4" aria-live="polite">
                      <div className="table-responsive">
                        <table className="table table-hover align-middle mb-0">
                          <caption className="visually-hidden">Preliminary itemized component costs</caption>
                          <thead><tr>
                            <th scope="col">Component</th>
                            <th scope="col">Material</th>
                            <th scope="col">Estimated Quantity</th>
                            <th scope="col">Unit</th>
                            <th scope="col">Unit Price</th>
                            <th scope="col">Subtotal</th>
                          </tr></thead>
                          <tbody>
                            {costResult.components.map((item) => (
                              <tr key={item.component}>
                                <th scope="row">{item.component}</th>
                                <td>{item.material}</td>
                                <td>{item.estimated_quantity}</td>
                                <td>{item.unit}</td>
                                <td>{phpCurrency.format(Number(item.unit_price))}</td>
                                <td>{phpCurrency.format(Number(item.subtotal))}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <section className="card border-success mt-3" aria-labelledby="cost-summary-heading">
                        <div className="card-body">
                          <h3 className="h6" id="cost-summary-heading">Cost Summary</h3>
                          <dl className="row mb-0">
                            <dt className="col-sm-7">Total Material Cost</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(costResult.total_material_cost))}</dd>
                            <dt className="col-sm-7">Labor Hours</dt><dd className="col-sm-5 text-sm-end">{costResult.labor.hours}</dd>
                            <dt className="col-sm-7">Hourly Rate</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(costResult.labor.hourly_rate))}</dd>
                            <dt className="col-sm-7">Labor Cost</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(costResult.labor.labor_cost))}</dd>
                            <dt className="col-sm-7">Profit Margin</dt><dd className="col-sm-5 text-sm-end">{costResult.profit_margin_percent}%</dd>
                            <dt className="col-sm-7">Profit Amount</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(costResult.profit_amount))}</dd>
                            <dt className="col-sm-7 fs-5">Final Estimated Cost</dt><dd className="col-sm-5 text-sm-end fs-5 fw-bold">{phpCurrency.format(Number(costResult.final_estimated_cost))}</dd>
                          </dl>
                        </div>
                      </section>
                      <div className="alert alert-warning mt-3 mb-2" role="note">
                        This preliminary estimate includes material cost, labor cost, and profit only. No overhead cost is included.
                      </div>
                      <div className="alert alert-info mb-0" role="note">
                        Material prices are configurable preliminary values and may be updated by an administrator or supplier integration.
                      </div>
                    </div>
                  )}
                </div>
              </section>
              <section className="card border-0 bg-light mb-4 no-print" aria-labelledby="quotation-assembly-heading">
                <div className="card-body p-3 p-md-4">
                  <h2 className="h5" id="quotation-assembly-heading">Preliminary Quotation Preview</h2>
                  <p className="text-secondary small">Add customer details and assemble all Phase 7 results.</p>
                  <fieldset disabled={!costResult || assemblingQuotation}>
                    <legend className="visually-hidden">Quotation customer and project details</legend>
                    <div className="row g-3">
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="quotation-customer-name">Customer Name</label>
                        <input className="form-control" id="quotation-customer-name" maxLength="150" name="name" onChange={handleQuotationCustomerChange} required value={quotationCustomer.name} />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="quotation-project-name">Project Name</label>
                        <input className="form-control" id="quotation-project-name" maxLength="150" name="project_name" onChange={handleQuotationCustomerChange} required value={quotationCustomer.project_name} />
                      </div>
                      <div className="col-md-4">
                        <label className="form-label" htmlFor="quotation-location">Location</label>
                        <input className="form-control" id="quotation-location" maxLength="200" name="location" onChange={handleQuotationCustomerChange} required value={quotationCustomer.location} />
                      </div>
                    </div>
                  </fieldset>
                  <button className="btn btn-success mt-3" disabled={!costResult || assemblingQuotation} onClick={handleQuotationAssembly} type="button">
                    {assemblingQuotation && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                    {assemblingQuotation ? 'Generating quotation…' : 'Generate Preliminary Quotation'}
                  </button>
                  {!costResult && <p className="text-secondary small mt-2 mb-0">Complete a successful cost calculation first.</p>}
                  {quotationError && <div className="alert alert-danger mt-3 mb-0" role="alert">{quotationError}</div>}
                </div>
              </section>
              {quotationPreview && (
                <article className="quotation-preview card border-0 shadow-sm mb-4" aria-labelledby="quotation-preview-title" aria-live="polite">
                  <div className="card-body p-4 p-lg-5">
                    <header className="border-bottom pb-3 mb-4">
                      <div className="d-flex flex-column flex-sm-row justify-content-between gap-3">
                        <div>
                          <p className="text-success fw-semibold mb-1">WUE Quotation Preview</p>
                          <h2 className="h3" id="quotation-preview-title">{quotationPreview.quotation_id}</h2>
                          <p className="text-secondary mb-0">Generated {new Date(quotationPreview.generated_at).toLocaleString()}</p>
                        </div>
                        <div className="text-sm-end">
                          <span className="badge text-bg-warning fs-6">PRELIMINARY</span>
                          <p className="small mt-2 mb-0">Currency: {quotationPreview.currency}</p>
                        </div>
                      </div>
                    </header>

                    <section className="mb-4" aria-labelledby="preview-customer-heading">
                      <h3 className="h5" id="preview-customer-heading">Customer and Project</h3>
                      <dl className="row mb-0">
                        <dt className="col-sm-4">Customer Name</dt><dd className="col-sm-8">{quotationPreview.customer.name}</dd>
                        <dt className="col-sm-4">Project Name</dt><dd className="col-sm-8">{quotationPreview.project.name}</dd>
                        <dt className="col-sm-4">Location</dt><dd className="col-sm-8">{quotationPreview.customer.location}</dd>
                      </dl>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-furniture-heading">
                      <h3 className="h5" id="preview-furniture-heading">Furniture</h3>
                      <p className="mb-1"><strong>Furniture Type:</strong> {quotationPreview.furniture.display_name}</p>
                      <p className="mb-0"><strong>Classification Confidence:</strong> {(quotationPreview.furniture.confidence * 100).toFixed(1)}%</p>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-materials-heading">
                      <h3 className="h5" id="preview-materials-heading">Recommended Materials</h3>
                      <div className="row g-3">
                        {['Primary', 'Alternative'].map((priority) => (
                          <div className="col-md-6" key={priority}>
                            <h4 className="h6">{priority}</h4>
                            <ul className="mb-0">
                              {quotationPreview.recommendations.filter((item) => item.priority === priority).map((item) => (
                                <li key={`${priority}-${item.name}`}>{item.name} — {item.category}</li>
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-bom-heading">
                      <h3 className="h5" id="preview-bom-heading">Bill of Materials</h3>
                      <div className="table-responsive"><table className="table table-sm">
                        <thead><tr><th scope="col">Component</th><th scope="col">Material</th><th scope="col">Category</th></tr></thead>
                        <tbody>{quotationPreview.bom.map((item) => (
                          <tr key={item.component}><th scope="row">{item.component}</th><td>{item.recommended_material}</td><td>{item.category}</td></tr>
                        ))}</tbody>
                      </table></div>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-quantities-heading">
                      <h3 className="h5" id="preview-quantities-heading">Quantity Estimates</h3>
                      <div className="table-responsive"><table className="table table-sm">
                        <thead><tr><th scope="col">Component</th><th scope="col">Quantity</th><th scope="col">Unit</th></tr></thead>
                        <tbody>{quotationPreview.quantity_estimates.map((item) => (
                          <tr key={item.component}><th scope="row">{item.component}</th><td>{item.estimated_quantity}</td><td>{item.unit}</td></tr>
                        ))}</tbody>
                      </table></div>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-cost-heading">
                      <h3 className="h5" id="preview-cost-heading">Cost Summary</h3>
                      <dl className="row mb-0">
                        <dt className="col-sm-7">Material Cost</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(quotationPreview.cost_summary.total_material_cost))}</dd>
                        <dt className="col-sm-7">Labor Cost</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(quotationPreview.cost_summary.labor.labor_cost))}</dd>
                        <dt className="col-sm-7">Profit</dt><dd className="col-sm-5 text-sm-end">{phpCurrency.format(Number(quotationPreview.cost_summary.profit_amount))}</dd>
                        <dt className="col-sm-7 fs-5">Final Estimated Cost</dt><dd className="col-sm-5 text-sm-end fs-5 fw-bold">{phpCurrency.format(Number(quotationPreview.cost_summary.final_estimated_cost))}</dd>
                      </dl>
                    </section>

                    <section className="mb-4" aria-labelledby="preview-assumptions-heading">
                      <h3 className="h5" id="preview-assumptions-heading">Assumptions</h3>
                      <ul>{quotationPreview.assumptions.map((item) => <li key={item}>{item}</li>)}</ul>
                    </section>
                    <div className="alert alert-warning fw-semibold" role="note">{quotationPreview.disclaimer}</div>
                    <p className="mb-1"><strong>This quotation is not yet saved.</strong></p>
                    <p className="text-secondary mb-0">PDF export will be available in a future phase.</p>
                  </div>
                </article>
              )}
              <section className="card border-success mb-4 no-print" aria-labelledby="save-estimate-results-heading">
                <div className="card-body p-3 p-md-4">
                  <h2 className="h5" id="save-estimate-results-heading">Save Estimate Results</h2>
                  <p className="text-secondary small">Persist the completed AI-assisted workflow to an estimate you own.</p>
                  <label className="form-label" htmlFor="phase7-target-estimate">Target Estimate</label>
                  <select className="form-select" id="phase7-target-estimate" onChange={handleTargetEstimateChange} value={targetEstimateId}>
                    <option value="">Select an estimate</option>
                    {ownedEstimates.map((item) => <option key={item.id} value={item.id}>Estimate #{item.id} — {item.status}</option>)}
                  </select>
                  {!ownedEstimates.length && <p className="alert alert-warning mt-3 mb-0">Create an estimate record before saving the completed workflow.</p>}
                  <button
                    aria-label="Save completed AI-assisted estimate results"
                    className="btn btn-success mt-3"
                    disabled={
                      !quotationPreview
                      || !targetEstimateId
                      || savingIntegration
                      || (Boolean(integrationResult) && !workflowDirty)
                    }
                    onClick={handlePhase7Integration}
                    type="button"
                  >
                    {savingIntegration && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                    {savingIntegration ? 'Saving estimate results…' : 'Save Estimate Results'}
                  </button>
                  {workflowDirty && quotationPreview && <p className="text-warning-emphasis mt-2 mb-0" role="status">Unsaved changes</p>}
                  {integrationError && <div className="alert alert-danger mt-3 mb-0" role="alert">{integrationError}</div>}
                  {integrationResult && !workflowDirty && (
                    <div className="alert alert-success mt-3 mb-0" role="status">
                      <strong>Estimate results saved.</strong>{' '}
                      <Link to={`/estimates/${integrationResult.estimate_id}`}>Open Estimate Details</Link>
                    </div>
                  )}
                </div>
              </section>
              <div className="mb-3">
                <label className="form-label" htmlFor="estimate-user">User</label>
                <input className="form-control" id="estimate-user" readOnly value={`${user.username} (#${user.id})`} />
              </div>
              <div className="mb-3">
                <label className="form-label" htmlFor="input-method">Input method</label>
                <select className="form-select" disabled={submitting} id="input-method" name="input_method" onChange={updateField} required value={form.input_method}>
                  <option value="predefined">Predefined furniture</option>
                  <option value="image_upload">Image upload</option>
                </select>
              </div>
              <div className="mb-3">
                <label className="form-label" htmlFor="selected-type">Selected furniture type</label>
                <select className="form-select" disabled={submitting || loadingTypes} id="selected-type" name="selected_furniture_type_id" onChange={updateField} value={form.selected_furniture_type_id}>
                  <option value="">No selection</option>
                  {furnitureTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              </div>
              <div className="mb-3">
                <label className="form-label" htmlFor="image-path">Image path</label>
                <input className="form-control" disabled={submitting} id="image-path" maxLength="500" name="image_path" onChange={updateField} placeholder="Required only for image_upload" value={form.image_path} />
              </div>
              <div className="row g-3 mb-4">
                <div className="col-md-7">
                  <label className="form-label" htmlFor="recognized-type">Recognized furniture type</label>
                  <select className="form-select" disabled={submitting || loadingTypes} id="recognized-type" name="recognized_furniture_type_id" onChange={updateField} value={form.recognized_furniture_type_id}>
                    <option value="">No recognition result</option>
                    {furnitureTypes.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
                  </select>
                </div>
                <div className="col-md-5">
                  <label className="form-label" htmlFor="recognition-confidence">Recognition confidence</label>
                  <input className="form-control" disabled={submitting} id="recognition-confidence" max="1" min="0" name="recognition_confidence" onChange={updateField} step="0.0001" type="number" value={form.recognition_confidence} />
                </div>
              </div>
              <button className="btn btn-success w-100" disabled={submitting || loadingTypes} type="submit">
                {submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                {submitting ? 'Creating estimate…' : 'Create estimate'}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  )
}
