import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { ACCESS_TOKEN_KEY, AUTH_UNAUTHORIZED_EVENT } from '../api/client.js'
import {
  clearAccessToken,
  fetchCurrentUser,
  loginAndLoadCurrentUser,
  registerUser,
} from '../services/authSession.js'

export const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY))
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const clearSession = useCallback(() => {
    clearAccessToken()
    setAccessToken(null)
    setUser(null)
  }, [])

  const restoreSession = useCallback(async () => {
    const storedToken = localStorage.getItem(ACCESS_TOKEN_KEY)
    if (!storedToken) {
      clearSession()
      setLoading(false)
      return null
    }

    setLoading(true)
    setAccessToken(storedToken)
    try {
      const restoredUser = await fetchCurrentUser()
      setUser(restoredUser)
      return restoredUser
    } catch {
      clearSession()
      return null
    } finally {
      setLoading(false)
    }
  }, [clearSession])

  useEffect(() => {
    restoreSession()
  }, [restoreSession])

  useEffect(() => {
    const handleUnauthorized = () => {
      clearSession()
      setLoading(false)
    }
    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
    return () => window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized)
  }, [clearSession])

  const login = useCallback(async (identifier, password) => {
    try {
      const session = await loginAndLoadCurrentUser(identifier, password)
      setAccessToken(session.token)
      setUser(session.user)
      return session.user
    } catch (error) {
      clearSession()
      throw error
    }
  }, [clearSession])

  const register = useCallback(async (registration) => {
    return registerUser(registration)
  }, [])

  const logout = useCallback(() => {
    clearSession()
    setLoading(false)
  }, [clearSession])

  const value = useMemo(() => ({
    accessToken,
    user,
    loading,
    isAuthenticated: Boolean(accessToken && user),
    login,
    register,
    logout,
    restoreSession,
  }), [accessToken, user, loading, login, register, logout, restoreSession])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider.')
  }
  return context
}
