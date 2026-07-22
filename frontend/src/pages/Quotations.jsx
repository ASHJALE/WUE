import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import QuotationCard from '../components/QuotationCard.jsx'
import { EmptyState, ErrorAlert, LoadingState } from '../components/AppFeedback.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getQuotations } from '../services/quotationService.js'

export default function Quotations() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [quotations, setQuotations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const estimateId = location.state?.estimateId || searchParams.get('estimate_id')
  const requestedAction = location.state?.action || searchParams.get('action')

  useEffect(() => {
    if (estimateId && requestedAction === 'create') {
      navigate(`/quotations/new?estimate_id=${estimateId}`, {
        replace: true,
        state: { estimateId },
      })
    }
  }, [estimateId, requestedAction, navigate])

  const loadQuotations = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      setQuotations(await getQuotations({ user_id: user.id, limit: 200 }))
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Quotations could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }, [user.id])

  useEffect(() => { loadQuotations() }, [loadQuotations])

  return (
    <section>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div><h1 className="h2 mb-1">Quotations</h1><p className="text-secondary mb-0">Review generated WUE quotations.</p></div>
        <Link className="btn btn-success" to="/estimates">Choose an estimate</Link>
      </div>
      {loading && <LoadingState cards={3} label="Loading quotations…" />}
      {!loading && error && <ErrorAlert message={error} onRetry={loadQuotations} />}
      {!loading && !error && quotations.length === 0 && (
        <EmptyState title="No quotations yet" description="Preview an estimate BOM before generating a quotation." action={<Link className="btn btn-success" to="/estimates">View estimates</Link>} />
      )}
      {!loading && !error && quotations.length > 0 && (
        <div className="row g-4">{quotations.map((quotation) => <div className="col-md-6 col-xl-4" key={quotation.id}><QuotationCard quotation={quotation} /></div>)}</div>
      )}
    </section>
  )
}
