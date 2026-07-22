export function getApiErrorMessage(error, fallback) {
  const detail = error.response?.data?.detail
  if (typeof detail === 'string') {
    return detail
  }
  if (Array.isArray(detail)) {
    return detail.map((item) => item.msg).filter(Boolean).join(' ')
  }
  if (error.code === 'ECONNABORTED') {
    return 'The request timed out. Check your connection and try again.'
  }
  if (!error.response) {
    return 'The WUE server could not be reached. Check your connection and try again.'
  }
  const messages = {
    401: 'Your session is no longer valid. Please sign in again.',
    403: 'You do not have permission to perform this action.',
    404: 'The requested WUE record could not be found.',
  }
  if (messages[error.response.status]) return messages[error.response.status]
  if (error.response.status >= 500) {
    return 'The WUE server encountered an error. Please try again.'
  }
  return fallback
}
