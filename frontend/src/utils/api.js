import axios from 'axios'

// Get API URL from environment or auto-detect based on hostname
const getApiUrl = () => {
  // If explicitly set in environment, use that
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL
  }

  // Auto-detect RunPod proxy URL
  // Example: https://2ww93nrkflzjy2-3000.proxy.runpod.net -> https://2ww93nrkflzjy2-8000.proxy.runpod.net
  if (typeof window !== 'undefined' && window.location.hostname.includes('proxy.runpod.net')) {
    const protocol = window.location.protocol
    const hostname = window.location.hostname.replace(/-3000\./, '-8000.')
    return `${protocol}//${hostname}`
  }

  // Default to localhost
  return 'http://localhost:8000'
}

const API_URL = getApiUrl()

// Log the API URL for debugging
console.log('API URL:', API_URL)

// Helper to calculate timeout based on inference steps
const calculateTimeout = (inferenceSteps = 50) => {
  // ~1 second per step + 60 second buffer
  return (inferenceSteps * 1000) + 60000
}

// Create axios instance with default config
export const api = axios.create({
  baseURL: API_URL,
  timeout: 180000, // 3 minutes default for non-edit requests
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

  // Calculate timeout based on inference steps
  const timeout = calculateTimeout(config.num_inference_steps || 50)

  return await api.post('/api/edit', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: timeout,
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
 * Get list of output images for a job
 * @param {string} jobId - Job identifier
 * @returns {Promise} - List of output images with metadata
 */
export const getOutputImages = async (jobId) => {
  return await api.get(`/api/jobs/${jobId}/images`)
}

/**
 * Download specific output image by index
 * @param {string} jobId - Job identifier
 * @param {number} index - Image index
 * @param {string} filename - Optional custom filename
 */
export const downloadImageByIndex = async (jobId, index, filename) => {
  const response = await api.get(`/api/jobs/${jobId}/images/${index}`, {
    responseType: 'blob',
  })

  // Create download link
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename || `edited_${jobId}_${index}.jpg`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

/**
 * Get preview URL for output image
 * @param {string} jobId - Job identifier
 * @param {number} index - Image index
 * @returns {string} - Preview URL
 */
export const getImagePreviewUrl = (jobId, index) => {
  return `${API_URL}/api/jobs/${jobId}/images/${index}`
}

/**
 * List images in ~/input folder
 * @returns {Promise} - List of images with metadata
 */
export const listInputFolderImages = async () => {
  return await api.get('/api/input-folder/list')
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
