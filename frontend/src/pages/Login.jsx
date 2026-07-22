import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { ErrorAlert } from '../components/AppFeedback.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'

export default function Login() {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!identifier.trim() || !password) {
      setError('Enter your username or email and password.')
      return
    }
    setSubmitting(true)
    try {
      await login(identifier.trim(), password)
      const original = location.state?.from
      const destination = original
        ? `${original.pathname}${original.search || ''}${original.hash || ''}`
        : '/dashboard'
      navigate(destination, { replace: true })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Login failed. Check your credentials and try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-md-7 col-lg-5">
        <section className="card border-0 shadow-sm">
          <div className="card-body p-4 p-md-5">
            <h1 className="h2 mb-1">Welcome back</h1>
            <p className="text-secondary mb-4">Sign in to continue to WUE.</p>
            {location.state?.message && <div className="alert alert-success" role="status">{location.state.message}</div>}
            {error && <ErrorAlert message={error} />}
            <form onSubmit={handleSubmit} noValidate>
              <div className="mb-3">
                <label className="form-label" htmlFor="login-identifier">Username or email</label>
                <input
                  autoComplete="username"
                  className="form-control"
                  disabled={submitting}
                  id="login-identifier"
                  onChange={(event) => setIdentifier(event.target.value)}
                  required
                  value={identifier}
                />
              </div>
              <div className="mb-4">
                <label className="form-label" htmlFor="login-password">Password</label>
                <input
                  autoComplete="current-password"
                  className="form-control"
                  disabled={submitting}
                  id="login-password"
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  type="password"
                  value={password}
                />
              </div>
              <button className="btn btn-success w-100" disabled={submitting} type="submit">
                {submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                {submitting ? 'Signing in…' : 'Sign in'}
              </button>
            </form>
            <p className="text-center text-secondary mt-4 mb-0">
              Need an account? <Link to="/register">Register</Link>
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
