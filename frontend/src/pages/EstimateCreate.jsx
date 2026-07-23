import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { ErrorAlert } from '../components/AppFeedback.jsx'
import FurnitureImagePicker from '../components/FurnitureImagePicker.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { createEstimate, getFurnitureTypes } from '../services/estimateService.js'
import { classifyFurnitureImage, uploadFurnitureImage } from '../services/imageService.js'
import { recommendMaterials } from '../services/materialRecommendationService.js'
import { generateStructuredBom } from '../services/bomGenerationService.js'

const furnitureClassNames = {
  chair: 'Chair',
  bed: 'Bed',
  sofa: 'Sofa',
  dining_table: 'Dining Table',
  lamp_shade: 'Lamp Shade',
}

const initialForm = {
  input_method: 'predefined',
  selected_furniture_type_id: '',
  recognized_furniture_type_id: '',
  image_path: '',
  recognition_confidence: '',
}

export default function EstimateCreate() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState(initialForm)
  const [furnitureTypes, setFurnitureTypes] = useState([])
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
  const recommendationRequestId = useRef(0)
  const classificationRequestId = useRef(0)
  const bomRequestId = useRef(0)

  useEffect(() => {
    let active = true
    getFurnitureTypes()
      .then((records) => { if (active) setFurnitureTypes(records.filter((item) => item.is_active)) })
      .catch((requestError) => { if (active) setError(getApiErrorMessage(requestError, 'Furniture types could not be loaded.')) })
      .finally(() => { if (active) setLoadingTypes(false) })
    return () => { active = false }
  }, [])

  function updateField(event) {
    const { name, value } = event.target
    setForm((current) => ({ ...current, [name]: value }))
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
    try {
      const result = await generateStructuredBom(
        materialRecommendations.furniture_type,
        materialRecommendations.materials,
      )
      if (bomRequestId.current === requestId) setGeneratedBom(result)
    } catch (requestError) {
      if (bomRequestId.current === requestId) {
        setBomError(getApiErrorMessage(requestError, 'The structured BOM could not be generated.'))
      }
    } finally {
      if (bomRequestId.current === requestId) setGeneratingBom(false)
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
                  <p className="text-secondary small">Analyze an uploaded image with the WUE development classifier.</p>
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
                  {classificationError && <div className="alert alert-danger mt-3 mb-0" role="alert">{classificationError}</div>}
                  {classificationResult && (
                    <div className="classification-result mt-4" aria-live="polite">
                      <div className="alert alert-warning" role="note">
                        <strong>Development classifier:</strong> this deterministic placeholder is for workflow testing and is not production-ready AI.
                      </div>
                      <dl className="row mb-3">
                        <dt className="col-sm-5">Predicted furniture type</dt><dd className="col-sm-7">{classificationResult.display_name}</dd>
                        <dt className="col-sm-5">Confidence</dt><dd className="col-sm-7">{(classificationResult.confidence * 100).toFixed(1)}%</dd>
                        <dt className="col-sm-5">Model</dt><dd className="col-sm-7">{classificationResult.model_name} v{classificationResult.model_version}</dd>
                      </dl>
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
