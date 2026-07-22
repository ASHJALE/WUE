import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <section className="text-center py-5">
      <p className="display-1 fw-bold text-success mb-0">404</p>
      <h1>Page not found</h1>
      <p className="text-secondary">The page you requested does not exist.</p>
      <Link className="btn btn-success" to="/">Return home</Link>
    </section>
  )
}
