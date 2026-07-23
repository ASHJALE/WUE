import apiClient from '../api/client.js'

export async function integratePhase7Estimate(estimateId, payload) {
  const response = await apiClient.post(`/estimates/${estimateId}/integrate-phase7`, payload)
  return response.data
}

export async function getPhase7Image(uploadId) {
  const response = await apiClient.get(`/images/${uploadId}/content`, { responseType: 'blob' })
  return response.data
}
