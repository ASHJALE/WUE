import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import BomItemCard from '../components/BomItemCard.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getBomPreview } from '../services/bomService.js'

export default function BomPreview() {
  const { id } = useParams()
  const [preview, setPreview] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadPreview = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setPreview(await getBomPreview(id))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'BOM preview could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { loadPreview() }, [loadPreview])

  if (loading) {
    return (
      <div className="text-center py-5" role="status">
        <div className="spinner-border text-success" />
        <p className="text-secondary mt-3">Loading BOM preview…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="alert alert-danger" role="alert">
        <p>{error}</p>
        <div className="d-flex gap-2">
          <button className="btn btn-sm btn-outline-danger" onClick={loadPreview} type="button">Retry</button>
          <Link className="btn btn-sm btn-outline-secondary" to={`/estimates/${id}`}>Back to estimate</Link>
        </div>
      </div>
    )
  }

  if (!preview || preview.items.length === 0) {
    return (
      <section className="card border-0 shadow-sm text-center py-5">
        <div className="card-body">
          <h1 className="h4">No BOM items available</h1>
          <p className="text-secondary">This estimate has no material rows to preview.</p>
          <Link className="btn btn-outline-secondary" to={`/estimates/${id}`}>Back to estimate</Link>
        </div>
      </section>
    )
  }

  return (
    <section>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h1 className="h2 mb-1">BOM Preview</h1>
          <p className="text-secondary mb-0">Estimate #{preview.estimate_id} · {preview.furniture_type_name}</p>
        </div>
        <div className="d-flex flex-wrap gap-2">
          <Link className="btn btn-outline-secondary" to={`/estimates/${preview.estimate_id}`}>Back to estimate</Link>
          <Link
            className="btn btn-success"
            state={{ estimateId: preview.estimate_id }}
            to={`/quotations/new?estimate_id=${preview.estimate_id}`}
          >
            Create quotation
          </Link>
        </div>
      </div>

      <div className="row g-3 mb-4">
        <div className="col-md-3"><div className="card border-0 shadow-sm h-100"><div className="card-body"><span className="small text-secondary">Furniture type ID</span><strong className="d-block">#{preview.furniture_type_id}</strong></div></div></div>
        <div className="col-md-3"><div className="card border-0 shadow-sm h-100"><div className="card-body"><span className="small text-secondary">Item count</span><strong className="d-block">{preview.item_count}</strong></div></div></div>
        <div className="col-md-3"><div className="card border-0 shadow-sm h-100"><div className="card-body"><span className="small text-secondary">Material total</span><strong className="d-block">{preview.material_total}</strong></div></div></div>
        <div className="col-md-3"><div className="card border-0 shadow-sm h-100"><div className="card-body"><span className="small text-secondary">Inventory shortage</span><strong className={`d-block ${preview.has_inventory_shortage ? 'text-danger' : 'text-success'}`}>{preview.has_inventory_shortage ? 'Yes' : 'No'}</strong></div></div></div>
      </div>

      <div className="row g-4">
        {preview.items.map((item) => (
          <div className="col-xl-6" key={item.furniture_material_id}>
            <BomItemCard item={item} />
          </div>
        ))}
      </div>
    </section>
  )
}
