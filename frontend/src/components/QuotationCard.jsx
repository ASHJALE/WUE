import { Link } from 'react-router-dom'

const statusClasses = {
  draft: 'text-bg-secondary',
  approved: 'text-bg-primary',
  rejected: 'text-bg-danger',
  completed: 'text-bg-success',
}

function QuotationCard({ quotation }) {
  return (
    <article className="card h-100 border-0 shadow-sm">
      <div className="card-body d-flex flex-column p-4">
        <div className="d-flex align-items-start justify-content-between gap-2 mb-3">
          <div>
            <h2 className="h5 mb-1">{quotation.quotation_number}</h2>
            <span className="small text-secondary">Estimate #{quotation.estimate_id}</span>
          </div>
          <span className={`badge ${statusClasses[quotation.status] || 'text-bg-secondary'}`}>
            {quotation.status}
          </span>
        </div>
        <dl className="row small mb-4">
          <dt className="col-5 text-secondary">Furniture</dt><dd className="col-7">{quotation.furniture_type_name}</dd>
          <dt className="col-5 text-secondary">Customer</dt><dd className="col-7">{quotation.username}</dd>
          <dt className="col-5 text-secondary">Grand total</dt><dd className="col-7 fw-semibold">{quotation.currency_code} {quotation.grand_total}</dd>
          <dt className="col-5 text-secondary">Created</dt><dd className="col-7 mb-0">{new Date(quotation.created_at).toLocaleDateString()}</dd>
        </dl>
        <Link className="btn btn-outline-success mt-auto" to={`/quotations/${quotation.id}`}>View quotation</Link>
      </div>
    </article>
  )
}

export default QuotationCard
