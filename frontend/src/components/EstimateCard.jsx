import { useState } from 'react'
import { Link } from 'react-router-dom'
import { FaImage } from 'react-icons/fa'

const statusClasses = {
  draft: 'text-bg-secondary',
  processing: 'text-bg-warning',
  processed: 'text-bg-info',
  quoted: 'text-bg-success',
}

function EstimateCard({ estimate }) {
  const [imageFailed, setImageFailed] = useState(false)
  const furnitureType = estimate.selected_furniture_type_name
    || estimate.recognized_furniture_type_name
    || 'Not selected'

  return (
    <article className="card h-100 border-0 shadow-sm">
      {estimate.image_path && !imageFailed ? (
        <img
          alt={`${furnitureType} estimate`}
          className="card-img-top estimate-card-image"
          onError={() => setImageFailed(true)}
          src={estimate.image_path}
        />
      ) : (
        <div className="estimate-card-image d-flex align-items-center justify-content-center bg-body-secondary text-secondary">
          <FaImage size="2rem" aria-hidden="true" />
        </div>
      )}
      <div className="card-body d-flex flex-column">
        <div className="d-flex align-items-start justify-content-between gap-2 mb-3">
          <h2 className="h5 mb-0">{furnitureType}</h2>
          <span className={`badge ${statusClasses[estimate.status] || 'text-bg-secondary'}`}>
            {estimate.status}
          </span>
        </div>
        <dl className="row small mb-4">
          <dt className="col-5 text-secondary">Estimate</dt>
          <dd className="col-7">#{estimate.id}</dd>
          <dt className="col-5 text-secondary">Estimated cost</dt>
          <dd className="col-7">Not available</dd>
          <dt className="col-5 text-secondary">Created</dt>
          <dd className="col-7 mb-0">{new Date(estimate.created_at).toLocaleDateString()}</dd>
        </dl>
        <Link className="btn btn-outline-success mt-auto" to={`/estimates/${estimate.id}`}>
          View estimate
        </Link>
      </div>
    </article>
  )
}

export default EstimateCard
