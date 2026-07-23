import apiClient from '../api/client.js'

export async function estimateBomQuantities(furnitureType, dimensions, components) {
  const response = await apiClient.post('/bom/estimate-quantities', {
    furniture_type: furnitureType,
    dimensions,
    components,
  })
  return response.data
}
