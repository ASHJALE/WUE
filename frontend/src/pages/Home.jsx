import { Link } from 'react-router-dom'
import { FaChartLine, FaFileInvoiceDollar, FaTree } from 'react-icons/fa6'

export default function Home() {
  return (
    <section>
      <div className="app-hero card border-0 shadow-sm overflow-hidden mb-4"><div className="card-body p-4 p-md-5 p-lg-6">
        <span className="badge text-bg-success mb-3">Wood U Estimate</span>
        <h1 className="display-5 fw-bold col-lg-8">Furniture estimation built for clear material decisions.</h1>
        <p className="lead text-secondary col-lg-7">Create estimates, preview bills of materials, and manage quotation workflows in one focused workspace.</p>
        <div className="d-flex flex-wrap gap-2"><Link className="btn btn-success btn-lg" to="/register">Get started</Link><Link className="btn btn-outline-success btn-lg" to="/login">Sign in</Link></div>
      </div></div>
      <div className="row g-4">
        {[[FaTree, 'Material clarity', 'Review quantities, wastage, inventory, and alternatives.'], [FaFileInvoiceDollar, 'Reliable quotations', 'Preserve price snapshots and move quotations through approval.'], [FaChartLine, 'Useful overview', 'Track recent activity and real dashboard summaries.']].map(([Icon, title, text]) => <div className="col-md-4" key={title}><div className="card border-0 shadow-sm h-100"><div className="card-body p-4"><Icon className="text-success mb-3" size="1.75rem" aria-hidden="true" /><h2 className="h5">{title}</h2><p className="text-secondary mb-0">{text}</p></div></div></div>)}
      </div>
    </section>
  )
}
