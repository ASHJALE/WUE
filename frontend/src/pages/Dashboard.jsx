import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import DashboardCharts from '../components/DashboardCharts.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'
import { getDashboardSummary } from '../services/dashboardService.js'

function SummarySkeleton() {
  return <div className="row g-3 mb-4">{Array.from({ length: 6 }, (_, index) => <div className="col-sm-6 col-xl-2" key={index}><div className="card border-0 shadow-sm"><div className="card-body placeholder-glow"><span className="placeholder col-8" /><span className="placeholder col-5 d-block mt-3 py-3" /></div></div></div>)}</div>
}

function ActivityTable({ records, type }) {
  if (records.length === 0) return <p className="text-secondary mb-0">No recent {type.toLowerCase()}.</p>
  return (
    <div className="table-responsive"><table className="table align-middle mb-0"><thead><tr><th>ID</th><th>Furniture</th><th>Status</th><th>Created</th><th><span className="visually-hidden">Action</span></th></tr></thead><tbody>
      {records.map((record) => {
        const isEstimate = type === 'Estimates'
        return <tr key={record.id}><td>#{record.id}</td><td>{isEstimate ? record.selected_furniture_type_name || record.recognized_furniture_type_name || 'Not selected' : record.furniture_type_name}</td><td><span className="badge text-bg-secondary">{record.status}</span></td><td>{new Date(record.created_at).toLocaleDateString()}</td><td className="text-end"><Link className="btn btn-sm btn-outline-success" to={`/${type.toLowerCase()}/${record.id}`}>View</Link></td></tr>
      })}
    </tbody></table></div>
  )
}

export default function Dashboard() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError('')
    try { setDashboard(await getDashboardSummary()) }
    catch (requestError) { setError(getApiErrorMessage(requestError, 'Dashboard data could not be loaded.')) }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { loadDashboard() }, [loadDashboard])

  function handleLogout() {
    logout()
    navigate('/login', { replace: true })
  }

  const summaryCards = dashboard ? [
    ['Total Estimates', dashboard.summary.totalEstimates],
    ['Draft Quotations', dashboard.summary.draft],
    ['Approved Quotations', dashboard.summary.approved],
    ['Completed Quotations', dashboard.summary.completed],
    ['Rejected Quotations', dashboard.summary.rejected],
    ['Estimated Material Value', dashboard.summary.materialValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })],
  ] : []

  return (
    <section>
      <div className="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
        <div><h1 className="h2 mb-1">Dashboard</h1><p className="text-secondary mb-0">Authenticated WUE overview and recent activity.</p></div>
        <div className="d-flex flex-wrap gap-2">
          <Link className="btn btn-success" to="/estimates/new">New Estimate</Link>
          <Link className="btn btn-outline-success" to="/estimates">View Estimates</Link>
          <Link className="btn btn-outline-success" to="/quotations">View Quotations</Link>
          <a className="btn btn-outline-secondary" href="#profile">Profile</a>
          <button className="btn btn-outline-danger" onClick={handleLogout} type="button">Logout</button>
        </div>
      </div>
      {loading && <SummarySkeleton />}
      {!loading && error && <div className="alert alert-danger d-flex align-items-center justify-content-between gap-3" role="alert"><span>{error}</span><button className="btn btn-sm btn-outline-danger" onClick={loadDashboard} type="button">Retry</button></div>}
      {!loading && !error && dashboard && (
        <>
          <div className="row g-3 mb-4">{summaryCards.map(([label, value]) => <div className="col-sm-6 col-xl-2" key={label}><div className="card border-0 shadow-sm h-100"><div className="card-body"><span className="small text-secondary">{label}</span><strong className="display-6 d-block mt-2">{value}</strong></div></div></div>)}</div>
          {dashboard.estimates.length === 0 && dashboard.quotations.length === 0 && <div className="alert alert-light border text-center">No dashboard activity yet. Create an estimate to begin.</div>}
          <DashboardCharts quotations={dashboard.quotations} statusCounts={dashboard.quotationStatusCounts} timeline={dashboard.estimateTimeline} />
          <div className="row g-4 mb-4">
            <div className="col-xl-6"><section className="card border-0 shadow-sm h-100"><div className="card-body p-4"><div className="d-flex justify-content-between"><h2 className="h5">Recent Estimates</h2><Link to="/estimates">View all</Link></div><ActivityTable records={dashboard.recentEstimates} type="Estimates" /></div></section></div>
            <div className="col-xl-6"><section className="card border-0 shadow-sm h-100"><div className="card-body p-4"><div className="d-flex justify-content-between"><h2 className="h5">Recent Quotations</h2><Link to="/quotations">View all</Link></div><ActivityTable records={dashboard.recentQuotations} type="Quotations" /></div></section></div>
          </div>
          <section className="card border-0 shadow-sm" id="profile"><div className="card-body p-4"><h2 className="h5">Profile</h2><dl className="row mb-0"><dt className="col-sm-3 text-secondary">Username</dt><dd className="col-sm-9">{dashboard.user.username}</dd><dt className="col-sm-3 text-secondary">Email</dt><dd className="col-sm-9">{dashboard.user.email}</dd><dt className="col-sm-3 text-secondary">Full name</dt><dd className="col-sm-9">{dashboard.user.full_name}</dd><dt className="col-sm-3 text-secondary">Role</dt><dd className="col-sm-9 mb-0">{dashboard.user.role}</dd></dl></div></section>
        </>
      )}
    </section>
  )
}
