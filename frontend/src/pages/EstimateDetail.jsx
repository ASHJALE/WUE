import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getEstimate } from '../services/estimateService.js'
import { ErrorAlert, LoadingState } from '../components/AppFeedback.jsx'
import { getPhase7Image } from '../services/phase7IntegrationService.js'

function display(value) {
  if (value === null || value === undefined || value === '') return 'Not available'
  return String(value)
}

export default function EstimateDetail() {
  const { id } = useParams()
  const [estimate, setEstimate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [imageUrl, setImageUrl] = useState('')

  const loadEstimate = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setEstimate(await getEstimate(id))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Estimate could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { loadEstimate() }, [loadEstimate])

  useEffect(() => {
    if (!estimate?.phase7_upload_id) {
      setImageUrl('')
      return undefined
    }
    let active = true
    let objectUrl = ''
    getPhase7Image(estimate.phase7_upload_id)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setImageUrl(objectUrl)
      })
      .catch(() => { if (active) setImageUrl('') })
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [estimate?.phase7_upload_id])

  if (loading) return <LoadingState label="Loading estimate details…" />
  if (error) return <ErrorAlert message={error} onRetry={loadEstimate} />
  if (!estimate) return null

  const confidence = estimate.recognition_confidence === null
    ? null
    : `${(Number(estimate.recognition_confidence) * 100).toFixed(1)}%`
  const fields = [
    ['ID', estimate.id], ['User ID', estimate.user_id], ['Username', estimate.username],
    ['Selected furniture type ID', estimate.selected_furniture_type_id],
    ['Selected furniture type', estimate.selected_furniture_type_name],
    ['Recognized furniture type ID', estimate.recognized_furniture_type_id],
    ['Recognized furniture type', estimate.recognized_furniture_type_name],
    ['Image path', estimate.image_path], ['Input method', estimate.input_method],
    ['Recognition confidence', confidence],
    ['Integration status', estimate.integration_status], ['Status', estimate.status],
    ['Created at', new Date(estimate.created_at).toLocaleString()],
    ['Updated at', new Date(estimate.updated_at).toLocaleString()],
  ]

  return (
    <section>
      <div className="d-flex align-items-center justify-content-between gap-3 mb-4">
        <div><h1 className="h2 mb-1">Estimate #{estimate.id}</h1><p className="text-secondary mb-0">Complete estimate response from WUE.</p></div>
        <div className="d-flex flex-wrap gap-2">
          <Link className="btn btn-success" to={`/estimates/${estimate.id}/bom`}>Preview BOM</Link>
          <Link className="btn btn-outline-secondary" to="/estimates">Back to estimates</Link>
        </div>
      </div>
      {estimate.integration_status !== 'integrated' && (
        <div className="alert alert-info" role="note">
          This estimate was created before AI workflow integration and may not contain saved recognition data.
        </div>
      )}
      <div className="card border-0 shadow-sm"><div className="card-body p-4">
        {imageUrl && (
          <figure className="mb-4">
            <img
              alt={`Uploaded furniture for Estimate #${estimate.id}`}
              className="img-fluid rounded-3 border estimate-detail-image"
              src={imageUrl}
            />
            <figcaption className="text-secondary small mt-2">Saved AI-assisted workflow image</figcaption>
          </figure>
        )}
        <h2 className="h5">Estimate Details</h2>
        <dl className="row mb-0">
          {fields.map(([label, value]) => (
            <div className="col-md-6 mb-3" key={label}><dt className="text-secondary small">{label}</dt><dd className="mb-0 text-break">{display(value)}</dd></div>
          ))}
        </dl>
        {estimate.saved_cost_summary && (
          <section className="border-top pt-3 mt-2" aria-labelledby="saved-cost-heading">
            <h2 className="h5" id="saved-cost-heading">Saved Preliminary Cost</h2>
            <dl className="row mb-0">
              <dt className="col-sm-7">Material Cost</dt><dd className="col-sm-5">₱{Number(estimate.saved_cost_summary.total_material_cost).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</dd>
              <dt className="col-sm-7">Labor Cost</dt><dd className="col-sm-5">₱{Number(estimate.saved_cost_summary.labor.labor_cost).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</dd>
              <dt className="col-sm-7">Profit</dt><dd className="col-sm-5">₱{Number(estimate.saved_cost_summary.profit_amount).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</dd>
              <dt className="col-sm-7">Final Estimated Cost</dt><dd className="col-sm-5 fw-bold">₱{Number(estimate.saved_cost_summary.final_estimated_cost).toLocaleString('en-PH', { minimumFractionDigits: 2 })}</dd>
            </dl>
          </section>
        )}
        {estimate.preliminary_quotation_id && (
          <p className="alert alert-light border mt-3 mb-0">
            Saved preliminary quotation reference: <strong>{estimate.preliminary_quotation_id}</strong>
          </p>
        )}
      </div></div>
    </section>
  )
}
