import apiClient from '../api/client.js'

export async function uploadFurnitureImage(file) {
  const formData = new FormData()
  formData.append('image', file)
  const response = await apiClient.post('/images/upload', formData)
  return response.data
}

export async function classifyFurnitureImage(uploadId) {
  const response = await apiClient.post(`/images/${uploadId}/classify`)
  return response.data
}
