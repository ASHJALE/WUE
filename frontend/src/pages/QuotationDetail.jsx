import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../services/apiErrors.js'
import {
  approveQuotation,
  completeQuotation,
  downloadQuotationPdf,
  getQuotation,
  rejectQuotation,
} from '../services/quotationService.js'
import { ErrorAlert, LoadingState } from '../components/AppFeedback.jsx'

function display(value) {
  if (value === null || value === undefined || value === '') return 'Not available'
  return String(value)
}

export default function QuotationDetail() {
  const { id } = useParams()
  const [quotation, setQuotation] = useState(null)
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState('')
  const [error, setError] = useState('')

  const loadQuotation = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setQuotation(await getQuotation(id)) }
    catch (requestError) { setError(getApiErrorMessage(requestError, 'Quotation could not be loaded.')) }
    finally { setLoading(false) }
  }, [id])

  useEffect(() => { loadQuotation() }, [loadQuotation])

  async function runWorkflow(name, operation) {
    if (!window.confirm(`Confirm quotation ${name}?`)) return
    setAction(name)
    setError('')
    try {
      await operation(id)
      await loadQuotation()
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, `Quotation ${name} failed.`))
    } finally {
      setAction('')
    }
  }

  async function downloadPdf() {
    setAction('pdf')
    setError('')
    try { await downloadQuotationPdf(id) }
    catch (requestError) { setError(getApiErrorMessage(requestError, 'PDF download failed.')) }
    finally { setAction('') }
  }

  if (loading && !quotation) return <LoadingState label="Loading quotation details…" />
  if (!quotation && error) return <ErrorAlert message={error} onRetry={loadQuotation} />
  if (!quotation) return null

  const metadata = [
    ['ID', quotation.id], ['Quotation number', quotation.quotation_number],
    ['Estimate ID', quotation.estimate_id], ['User ID', quotation.user_id],
    ['Username', quotation.username], ['Furniture type ID', quotation.furniture_type_id],
    ['Furniture type', quotation.furniture_type_name], ['Status', quotation.status],
    ['Currency', quotation.currency_code], ['Valid until', quotation.valid_until],
    ['Notes', quotation.notes], ['Created at', new Date(quotation.created_at).toLocaleString()],
    ['Updated at', new Date(quotation.updated_at).toLocaleString()],
  ]
  const totals = [
    ['Material total', quotation.material_total], ['Labor cost', quotation.labor_cost],
    ['Logistics cost', quotation.logistics_cost], ['Subtotal before profit', quotation.subtotal_before_profit],
    ['Profit percentage', quotation.profit_percentage], ['Profit amount', quotation.profit_amount],
    ['Grand total', quotation.grand_total],
  ]

  return (
    <section>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div><h1 className="h2 mb-1">{quotation.quotation_number}</h1><p className="text-secondary mb-0">Estimate #{quotation.estimate_id} · {quotation.status}</p></div>
        <div className="d-flex flex-wrap gap-2">
          {quotation.status === 'draft' && <><button className="btn btn-primary" disabled={Boolean(action)} onClick={() => runWorkflow('approval', approveQuotation)} title="Approve this draft quotation" type="button">Approve</button><button className="btn btn-outline-danger" disabled={Boolean(action)} onClick={() => runWorkflow('rejection', rejectQuotation)} title="Reject this draft quotation" type="button">Reject</button></>}
          {quotation.status === 'approved' && <button className="btn btn-success" disabled={Boolean(action)} onClick={() => runWorkflow('completion', completeQuotation)} title="Mark this approved quotation complete" type="button">Complete</button>}
          <button className="btn btn-outline-success" disabled={Boolean(action)} onClick={downloadPdf} title="Download quotation as PDF" type="button">{action === 'pdf' ? 'Preparing PDF…' : 'Download PDF'}</button>
          <Link className="btn btn-outline-secondary" to="/quotations">Back</Link>
        </div>
      </div>
      {error && <ErrorAlert message={error} />}
      <div className="row g-4 mb-4">
        <div className="col-lg-7"><div className="card border-0 shadow-sm h-100"><div className="card-body p-4"><h2 className="h5">Quotation metadata</h2><dl className="row mb-0">{metadata.map(([label, value]) => <div className="col-md-6 mb-3" key={label}><dt className="small text-secondary">{label}</dt><dd className="mb-0 text-break">{display(value)}</dd></div>)}</dl></div></div></div>
        <div className="col-lg-5"><div className="card border-0 shadow-sm h-100"><div className="card-body p-4"><h2 className="h5">Backend totals</h2><dl className="mb-0">{totals.map(([label, value]) => <div className="d-flex justify-content-between gap-3 border-bottom py-2" key={label}><dt className="text-secondary">{label}</dt><dd className="mb-0 fw-semibold">{quotation.currency_code} {display(value)}</dd></div>)}</dl></div></div></div>
      </div>
      <div className="card border-0 shadow-sm"><div className="card-body p-4"><h2 className="h5">Quotation items</h2>
        {quotation.items.length === 0 ? <p className="text-secondary mb-0">No quotation items.</p> : (
          <div className="table-responsive"><table className="table align-middle"><thead><tr><th>ID</th><th>Material</th><th>Material ID</th><th>BOM row ID</th><th>Quantity</th><th>Unit</th><th>Unit price</th><th>Line total</th><th>Alternative</th><th>Created</th></tr></thead><tbody>{quotation.items.map((item) => <tr key={item.id}><td>{item.id}</td><td>{item.material_name_snapshot}</td><td>{item.material_id}</td><td>{display(item.furniture_material_id)}</td><td>{item.quantity}</td><td>{item.unit_snapshot}</td><td>{item.unit_price_snapshot}</td><td>{item.line_total}</td><td>{item.is_alternative ? 'Yes' : 'No'}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>
        )}
      </div></div>
    </section>
  )
}
