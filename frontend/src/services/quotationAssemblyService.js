import apiClient from '../api/client.js'

export async function assemblePreliminaryQuotation(payload) {
  const response = await apiClient.post('/quotation/assemble', payload)
  return response.data
}
