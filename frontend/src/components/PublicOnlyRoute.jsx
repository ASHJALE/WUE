import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'
import { LoadingState } from './AppFeedback.jsx'

function PublicOnlyRoute() {
  const { isAuthenticated, loading } = useAuth()

  if (loading) return <LoadingState label="Restoring your session…" />

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <Outlet />
}

export default PublicOnlyRoute
