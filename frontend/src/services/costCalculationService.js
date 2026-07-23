import apiClient from '../api/client.js'

export async function calculatePreliminaryCost(furnitureType, components, labor, profitMarginPercent) {
  const response = await apiClient.post('/costs/calculate', {
    furniture_type: furnitureType,
    components,
    labor,
    profit_margin_percent: profitMarginPercent,
  })
  return response.data
}
