import apiClient from '../api/client.js'

export async function getQuotations(params = {}) {
  const response = await apiClient.get('/quotations', { params })
  return response.data
}

export async function getQuotation(id) {
  const response = await apiClient.get(`/quotations/${id}`)
  return response.data
}

export async function generateQuotation(estimateId, data) {
  const response = await apiClient.post(`/estimates/${estimateId}/quotation`, data)
  return response.data
}

export async function approveQuotation(id) {
  const response = await apiClient.post(`/quotations/${id}/approve`)
  return response.data
}

export async function rejectQuotation(id) {
  const response = await apiClient.post(`/quotations/${id}/reject`)
  return response.data
}

export async function completeQuotation(id) {
  const response = await apiClient.post(`/quotations/${id}/complete`)
  return response.data
}

function filenameFromDisposition(disposition, id) {
  if (!disposition) return `quotation-${id}.pdf`
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const quotedMatch = disposition.match(/filename="([^"]+)"/i)
  const plainMatch = disposition.match(/filename=([^;]+)/i)
  const candidate = utf8Match?.[1]
    ? decodeURIComponent(utf8Match[1])
    : quotedMatch?.[1] || plainMatch?.[1]?.trim()
  return candidate?.replace(/[\\/:*?"<>|]/g, '_') || `quotation-${id}.pdf`
}

export async function downloadQuotationPdf(id) {
  const response = await apiClient.get(`/quotations/${id}/pdf`, {
    responseType: 'blob',
  })
  const filename = filenameFromDisposition(response.headers['content-disposition'], id)
  const objectUrl = URL.createObjectURL(response.data)
  const link = document.createElement('a')
  try {
    link.href = objectUrl
    link.download = filename
    link.style.display = 'none'
    document.body.appendChild(link)
    link.click()
  } finally {
    link.remove()
    URL.revokeObjectURL(objectUrl)
  }
  return filename
}
