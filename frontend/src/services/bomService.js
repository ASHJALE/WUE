import apiClient from '../api/client.js'

export async function getBomPreview(estimateId) {
  const response = await apiClient.get(`/estimates/${estimateId}/bom-preview`)
  return response.data
}
