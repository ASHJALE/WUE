import apiClient from '../api/client.js'

export async function getEstimates(params = {}) {
  const response = await apiClient.get('/estimates', { params })
  return response.data
}

export async function getEstimate(id) {
  const response = await apiClient.get(`/estimates/${id}`)
  return response.data
}

export async function createEstimate(data) {
  const response = await apiClient.post('/estimates', data)
  return response.data
}

export async function getFurnitureTypes() {
  const response = await apiClient.get('/furniture-types', {
    params: { skip: 0, limit: 200 },
  })
  return response.data
}
