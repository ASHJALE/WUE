import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import EstimateCard from '../components/EstimateCard.jsx'
import { EmptyState, ErrorAlert, LoadingState } from '../components/AppFeedback.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getEstimates } from '../services/estimateService.js'

export default function Estimates() {
  const { user } = useAuth()
  const [estimates, setEstimates] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadEstimates = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const records = await getEstimates({ user_id: user.id, limit: 200 })
      setEstimates(records)
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Estimates could not be loaded.'))
    } finally {
      setLoading(false)
    }
  }, [user.id])

  useEffect(() => {
    loadEstimates()
  }, [loadEstimates])

  return (
    <section>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div>
          <h1 className="h2 mb-1">Estimates</h1>
          <p className="text-secondary mb-0">Review and create your furniture estimates.</p>
        </div>
        <Link className="btn btn-success" to="/estimates/new">Create estimate</Link>
      </div>

      {loading && <LoadingState cards={3} label="Loading estimates…" />}

      {!loading && error && <ErrorAlert message={error} onRetry={loadEstimates} />}

      {!loading && !error && estimates.length === 0 && (
        <EmptyState title="No estimates yet" description="Create your first furniture estimate to get started." action={<Link className="btn btn-success" to="/estimates/new">Create estimate</Link>} />
      )}

      {!loading && !error && estimates.length > 0 && (
        <div className="row g-4">
          {estimates.map((estimate) => (
            <div className="col-sm-6 col-xl-4" key={estimate.id}>
              <EstimateCard estimate={estimate} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
