import apiClient from '../api/client.js'

export async function recommendMaterials(furnitureType) {
  const response = await apiClient.post('/materials/recommend', {
    furniture_type: furnitureType,
  })
  return response.data
}
