import { FaBoxOpen, FaCircleExclamation } from 'react-icons/fa6'

export function LoadingState({ label = 'Loading…', cards = 0 }) {
  if (cards > 0) {
    return (
      <div aria-busy="true" aria-label={label} className="row g-4" role="status">
        {Array.from({ length: cards }, (_, index) => (
          <div className="col-sm-6 col-xl-4" key={index}>
            <div className="card border-0 shadow-sm h-100 placeholder-glow">
              <div className="card-body p-4">
                <span className="placeholder col-7" />
                <span className="placeholder col-4 d-block mt-3" />
                <span className="placeholder col-12 d-block mt-4 py-4" />
              </div>
            </div>
          </div>
        ))}
        <span className="visually-hidden">{label}</span>
      </div>
    )
  }
  return (
    <div aria-busy="true" className="app-loading text-center py-5" role="status">
      <div aria-hidden="true" className="spinner-border text-success" />
      <p className="text-secondary mt-3 mb-0">{label}</p>
    </div>
  )
}

export function ErrorAlert({ message, onRetry }) {
  return (
    <div className="alert alert-danger d-flex flex-column flex-sm-row align-items-sm-center justify-content-between gap-3" role="alert">
      <span className="d-flex align-items-start gap-2"><FaCircleExclamation className="flex-shrink-0 mt-1" aria-hidden="true" />{message}</span>
      {onRetry && <button className="btn btn-sm btn-outline-danger flex-shrink-0" onClick={onRetry} type="button">Try again</button>}
    </div>
  )
}

export function EmptyState({ title, description, action, icon: Icon = FaBoxOpen }) {
  return (
    <section className="card border-0 shadow-sm text-center app-empty-state">
      <div className="card-body p-5">
        <Icon className="text-success mb-3" size="2.5rem" aria-hidden="true" />
        <h2 className="h4">{title}</h2>
        <p className="text-secondary mx-auto">{description}</p>
        {action}
      </div>
    </section>
  )
}
