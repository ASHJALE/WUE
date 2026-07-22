import { useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { ErrorAlert } from '../components/AppFeedback.jsx'
import { generateQuotation } from '../services/quotationService.js'

const initialForm = {
  labor_cost: '0.00',
  logistics_cost: '0.00',
  profit_margin_percentage: '0.00',
}

export default function QuotationCreate() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const estimateId = location.state?.estimateId || searchParams.get('estimate_id')
  const [form, setForm] = useState(initialForm)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!estimateId || !/^\d+$/.test(String(estimateId))) {
      setError('A valid estimate ID is required to generate a quotation.')
      return
    }
    for (const [field, label] of [
      ['labor_cost', 'Labor cost'],
      ['logistics_cost', 'Logistics cost'],
      ['profit_margin_percentage', 'Profit margin percentage'],
    ]) {
      const value = Number(form[field])
      if (form[field] === '' || Number.isNaN(value) || value < 0) {
        setError(`${label} must be zero or greater.`)
        return
      }
    }
    if (Number(form.profit_margin_percentage) > 100) {
      setError('Profit margin percentage must be between 0 and 100.')
      return
    }

    setSubmitting(true)
    try {
      const created = await generateQuotation(estimateId, {
        labor_cost: form.labor_cost,
        logistics_cost: form.logistics_cost,
        profit_margin_percentage: form.profit_margin_percentage,
      })
      navigate(`/quotations/${created.id}`, { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Quotation generation failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center"><div className="col-lg-7"><section className="card border-0 shadow-sm"><div className="card-body p-4 p-md-5">
      <div className="d-flex align-items-center justify-content-between gap-3 mb-4"><div><h1 className="h2 mb-1">Create quotation</h1><p className="text-secondary mb-0">Estimate #{estimateId || 'not selected'}</p></div><Link className="btn btn-outline-secondary" to={estimateId ? `/estimates/${estimateId}/bom` : '/estimates'}>Cancel</Link></div>
      {!estimateId && <div className="alert alert-warning">Select an estimate and preview its BOM before creating a quotation.</div>}
      {error && <ErrorAlert message={error} />}
      <form onSubmit={handleSubmit} noValidate>
        <div className="mb-3"><label className="form-label" htmlFor="labor-cost">Labor cost</label><input className="form-control" disabled={submitting || !estimateId} id="labor-cost" min="0" name="labor_cost" onChange={updateField} required step="0.01" type="number" value={form.labor_cost} /></div>
        <div className="mb-3"><label className="form-label" htmlFor="logistics-cost">Logistics cost</label><input className="form-control" disabled={submitting || !estimateId} id="logistics-cost" min="0" name="logistics_cost" onChange={updateField} required step="0.01" type="number" value={form.logistics_cost} /></div>
        <div className="mb-4"><label className="form-label" htmlFor="profit-margin">Profit margin percentage</label><input className="form-control" disabled={submitting || !estimateId} id="profit-margin" max="100" min="0" name="profit_margin_percentage" onChange={updateField} required step="0.01" type="number" value={form.profit_margin_percentage} /></div>
        <button className="btn btn-success w-100" disabled={submitting || !estimateId} type="submit">{submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}{submitting ? 'Generating quotation…' : 'Generate quotation'}</button>
      </form>
    </div></section></div></div>
  )
}
