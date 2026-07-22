import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { LoadingState } from './AppFeedback.jsx'

function ProtectedRoute() {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingState label="Restoring your session…" />

  return isAuthenticated
    ? <Outlet />
    : <Navigate to="/login" replace state={{ from: location }} />
}

export default ProtectedRoute
