import axios from 'axios'

// Get API URL from environment or default to localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002'

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_URL,
  timeout: 300000, // 5 minutes timeout (image editing is fast)
})

/**
 * Generate edited image
 * @param {File[]} images - Array of 1-2 image files
 * @param {Object} config - Edit configuration
 * @returns {Promise} - Response with job_id
 */
export const generateEdit = async (images, config) => {
  const formData = new FormData()

  // Add images
  if (images.length >= 1) {
    formData.append('image1', images[0])
  }
  if (images.length >= 2) {
    formData.append('image2', images[1])
  }

  // Add config as JSON string
  formData.append('config', JSON.stringify(config))

  return await api.post('/api/edit', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}

/**
 * Get job status
 * @param {string} jobId - Job identifier
 * @returns {Promise} - Job status response
 */
export const getJobStatus = async (jobId) => {
  return await api.get(`/api/jobs/${jobId}/status`)
}

/**
 * Download edited image
 * @param {string} jobId - Job identifier
 */
export const downloadImage = async (jobId) => {
  const response = await api.get(`/api/jobs/${jobId}/download`, {
    responseType: 'blob',
  })

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `edited_${jobId}.jpg`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Delete/cancel a job
 * @param {string} jobId - Job identifier
 * @returns {Promise}
 */
export const deleteJob = async (jobId) => {
  return await api.delete(`/api/jobs/${jobId}`)
}

/**
 * Create WebSocket connection for real-time updates
 * @param {string} jobId - Job identifier
 * @param {Function} onMessage - Message handler
 * @param {Function} onError - Error handler
 * @returns {WebSocket}
 */
export const createWebSocket = (jobId, onMessage, onError) => {
  // Convert HTTP/HTTPS to WS/WSS
  const wsUrl = API_URL.replace(/^http/, 'ws')
  const ws = new WebSocket(`${wsUrl}/ws/${jobId}`)

  ws.onopen = () => {
    console.log('WebSocket connected')
  }

  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (err) {
      console.error('Error parsing WebSocket message:', err)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
    if (onError) onError(error)
  }

  ws.onclose = () => {
    console.log('WebSocket disconnected')
  }

  return ws
}

export default api
