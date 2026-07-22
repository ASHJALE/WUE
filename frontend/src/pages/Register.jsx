import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { getApiErrorMessage } from '../services/apiErrors.js'

const initialForm = {
  username: '',
  email: '',
  full_name: '',
  password: '',
  confirmPassword: '',
}

export default function Register() {
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  function updateField(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    if (!form.username.trim() || !form.email.trim() || !form.full_name.trim() || !form.password) {
      setError('Complete every required field.')
      return
    }
    if (form.username.trim().length < 3) {
      setError('Username must contain at least 3 characters.')
      return
    }
    if (form.password.length < 8) {
      setError('Password must contain at least 8 characters.')
      return
    }
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setSubmitting(true)
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        full_name: form.full_name.trim(),
        password: form.password,
      })
      navigate('/login', {
        replace: true,
        state: { message: 'Registration successful. Sign in to continue.' },
      })
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, 'Registration failed. Please try again.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="row justify-content-center">
      <div className="col-md-8 col-lg-6">
        <section className="card border-0 shadow-sm">
          <div className="card-body p-4 p-md-5">
            <h1 className="h2 mb-1">Create an account</h1>
            <p className="text-secondary mb-4">Register to start using WUE.</p>
            {error && <div className="alert alert-danger" role="alert">{error}</div>}
            <form onSubmit={handleSubmit} noValidate>
              <div className="row g-3">
                <div className="col-md-6">
                  <label className="form-label" htmlFor="register-username">Username</label>
                  <input className="form-control" disabled={submitting} id="register-username" maxLength="50" name="username" onChange={updateField} required value={form.username} />
                </div>
                <div className="col-md-6">
                  <label className="form-label" htmlFor="register-email">Email</label>
                  <input autoComplete="email" className="form-control" disabled={submitting} id="register-email" maxLength="255" name="email" onChange={updateField} required type="email" value={form.email} />
                </div>
                <div className="col-12">
                  <label className="form-label" htmlFor="register-full-name">Full name</label>
                  <input autoComplete="name" className="form-control" disabled={submitting} id="register-full-name" maxLength="150" name="full_name" onChange={updateField} required value={form.full_name} />
                </div>
                <div className="col-md-6">
                  <label className="form-label" htmlFor="register-password">Password</label>
                  <input autoComplete="new-password" className="form-control" disabled={submitting} id="register-password" maxLength="128" minLength="8" name="password" onChange={updateField} required type="password" value={form.password} />
                </div>
                <div className="col-md-6">
                  <label className="form-label" htmlFor="register-confirm-password">Confirm password</label>
                  <input autoComplete="new-password" className="form-control" disabled={submitting} id="register-confirm-password" maxLength="128" minLength="8" name="confirmPassword" onChange={updateField} required type="password" value={form.confirmPassword} />
                </div>
              </div>
              <button className="btn btn-success w-100 mt-4" disabled={submitting} type="submit">
                {submitting && <span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />}
                {submitting ? 'Creating account…' : 'Create account'}
              </button>
            </form>
            <p className="text-center text-secondary mt-4 mb-0">
              Already registered? <Link to="/login">Sign in</Link>
            </p>
          </div>
        </section>
      </div>
    </div>
  )
}
