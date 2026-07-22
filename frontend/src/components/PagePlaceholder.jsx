function PagePlaceholder({ title, description }) {
  return (
    <section className="card border-0 shadow-sm">
      <div className="card-body p-4 p-md-5">
        <span className="badge text-bg-success mb-3">Phase 6.1</span>
        <h1 className="display-6 fw-semibold">{title}</h1>
        <p className="lead text-secondary mb-0">{description}</p>
      </div>
    </section>
  )
}

export default PagePlaceholder
