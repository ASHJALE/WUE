import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getEstimate } from '../services/estimateService.js'
import { ErrorAlert, LoadingState } from '../components/AppFeedback.jsx'

function display(value) {
  if (value === null || value === undefined || value === '') return 'Not available'
  return String(value)
}

export default function EstimateDetail() {
  const { id } = useParams()
  const [estimate, setEstimate] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  if (loading) return <LoadingState label="Loading estimate details…" />
  if (error) return <ErrorAlert message={error} onRetry={loadEstimate} />
  if (!estimate) return null

  const fields = [
    ['ID', estimate.id], ['User ID', estimate.user_id], ['Username', estimate.username],
    ['Selected furniture type ID', estimate.selected_furniture_type_id],
    ['Selected furniture type', estimate.selected_furniture_type_name],
    ['Recognized furniture type ID', estimate.recognized_furniture_type_id],
    ['Recognized furniture type', estimate.recognized_furniture_type_name],
    ['Image path', estimate.image_path], ['Input method', estimate.input_method],
    ['Recognition confidence', estimate.recognition_confidence], ['Status', estimate.status],
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
      <div className="card border-0 shadow-sm"><div className="card-body p-4">
        <dl className="row mb-0">
          {fields.map(([label, value]) => (
            <div className="col-md-6 mb-3" key={label}><dt className="text-secondary small">{label}</dt><dd className="mb-0 text-break">{display(value)}</dd></div>
          ))}
        </dl>
        <div className="alert alert-light border mb-0">BOM summary and quotation links are not included in the estimate response. Use Preview BOM to load the dedicated backend preview.</div>
      </div></div>
    </section>
  )
}
