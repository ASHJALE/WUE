import apiClient from '../api/client.js'

export async function generateStructuredBom(furnitureType, materials) {
  const response = await apiClient.post('/bom/generate', {
    furniture_type: furnitureType,
    materials,
  })
  return response.data
}
