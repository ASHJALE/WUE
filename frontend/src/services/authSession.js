import apiClient, { ACCESS_TOKEN_KEY } from '../api/client.js'

export function storeAccessToken(token) {
  localStorage.setItem(ACCESS_TOKEN_KEY, token)
}

export function clearAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
}

export async function fetchCurrentUser() {
  const response = await apiClient.get('/auth/me')
  return response.data
}

export async function loginAndLoadCurrentUser(identifier, password) {
  const body = new URLSearchParams()
  body.set('username', identifier)
  body.set('password', password)
  const response = await apiClient.post('/auth/login', body, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  const token = response.data.access_token
  storeAccessToken(token)
  try {
    const user = await fetchCurrentUser()
    return { token, user }
  } catch (error) {
    clearAccessToken()
    throw error
  }
}

export async function registerUser(registration) {
  const response = await apiClient.post('/auth/register', registration)
  return response.data
}
