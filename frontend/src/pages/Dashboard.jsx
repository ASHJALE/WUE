import { Link } from 'react-router-dom'

export default function Dashboard() {
  return (
    <section>
      <h1 className="h2">Dashboard</h1>
      <p className="text-secondary">Start a new estimate or review your existing work.</p>
      <div className="d-flex flex-wrap gap-2">
        <Link className="btn btn-success" to="/estimates/new">Create estimate</Link>
        <Link className="btn btn-outline-success" to="/estimates">View estimates</Link>
      </div>
    </section>
  )
}
