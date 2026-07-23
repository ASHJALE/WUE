import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { ErrorAlert } from '../components/AppFeedback.jsx'
import FurnitureImagePicker from '../components/FurnitureImagePicker.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { createEstimate, getFurnitureTypes } from '../services/estimateService.js'
import { uploadFurnitureImage } from '../services/imageService.js'

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
  }

  async function handleImageUpload() {
    if (!selectedImage || uploadingImage) return
    setUploadingImage(true)
    setImageUploadError('')
    try {
      setImageUploadResult(await uploadFurnitureImage(selectedImage))
    } catch (requestError) {
      setImageUploadError(getApiErrorMessage(requestError, 'The furniture image could not be uploaded.'))
    } finally {
      setUploadingImage(false)
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
