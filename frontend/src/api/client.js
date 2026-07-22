import axios from 'axios'

export const ACCESS_TOKEN_KEY = 'wue_access_token'
export const AUTH_UNAUTHORIZED_EVENT = 'wue:auth-unauthorized'
const API_BASE_URL = import.meta.env?.DEV
  ? '/api'
  : (import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000')

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem(ACCESS_TOKEN_KEY)
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT))
      }
    }
    // Authentication failures are never retried, preventing interceptor loops.
    return Promise.reject(error)
  },
)

export default apiClient
