import { useState, useEffect, useRef } from 'react'
import { getJobStatus, deleteJob, createWebSocket, getOutputImages, downloadImageByIndex, getImagePreviewUrl } from '../utils/api'

export default function ProgressTracker({ jobId, onComplete, onError, onCancel, onRestart }) {
  const [status, setStatus] = useState('processing')
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [connectionMethod, setConnectionMethod] = useState('connecting')
  const [outputImages, setOutputImages] = useState([])
  const [zoomedImage, setZoomedImage] = useState(null)
  const pollingIntervalRef = useRef(null)
  const websocketRef = useRef(null)

  // Handle ESC key to close zoom modal
  useEffect(() => {
    const handleEscKey = (e) => {
      if (e.key === 'Escape' && zoomedImage) {
        setZoomedImage(null)
      }
    }

    document.addEventListener('keydown', handleEscKey)
    return () => document.removeEventListener('keydown', handleEscKey)
  }, [zoomedImage])

  useEffect(() => {
    if (!jobId) return

    let isMounted = true

    // Try WebSocket first
    console.log(`Attempting WebSocket connection for job ${jobId}`)

    try {
      const ws = createWebSocket(
        jobId,
        (data) => {
          if (!isMounted) return

          console.log('WebSocket message received:', data)
          setStatus(data.status)
          setProgress(data.progress)

          if (data.error) {
            setError(data.error)
          }

          // Handle completion
          if (data.status === 'complete') {
            setConnectionMethod('websocket')
            // Fetch output images list
            fetchOutputImages()
            onComplete()
          } else if (data.status === 'error') {
            setConnectionMethod('websocket')
            onError(data.error || 'Unknown error occurred')
          } else {
            setConnectionMethod('websocket')
          }
        },
        (err) => {
          console.warn('WebSocket error, falling back to polling:', err)
          if (!isMounted) return

          // Fallback to HTTP polling
          startPolling()
        }
      )

      websocketRef.current = ws

      // Set success state after connection opens
      ws.addEventListener('open', () => {
        if (isMounted) {
          console.log('WebSocket connected successfully')
          setConnectionMethod('websocket')
        }
      })

      // Fallback to polling if WebSocket doesn't connect in 3 seconds
      const fallbackTimer = setTimeout(() => {
        if (connectionMethod === 'connecting' && isMounted) {
          console.log('WebSocket timeout, falling back to polling')
          if (websocketRef.current) {
            websocketRef.current.close()
            websocketRef.current = null
          }
          startPolling()
        }
      }, 3000)

      // Cleanup
      return () => {
        isMounted = false
        clearTimeout(fallbackTimer)
        if (websocketRef.current) {
          websocketRef.current.close()
          websocketRef.current = null
        }
        if (pollingIntervalRef.current) {
          clearInterval(pollingIntervalRef.current)
          pollingIntervalRef.current = null
        }
      }
    } catch (err) {
      console.warn('Failed to create WebSocket, using polling:', err)
      startPolling()
    }

    function startPolling() {
      if (!isMounted) return

      console.log(`Starting HTTP polling for job ${jobId}`)
      setConnectionMethod('polling')

      // Poll job status every 1.5 seconds
      const pollJobStatus = async () => {
        try {
          const response = await getJobStatus(jobId)
          const data = response.data

          if (!isMounted) return

          setStatus(data.status)
          setProgress(data.progress)

          if (data.error) {
            setError(data.error)
          }

          // Stop polling if job is complete or errored
          if (data.status === 'complete') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            // Fetch output images list
            fetchOutputImages()
            onComplete()
          } else if (data.status === 'error') {
            if (pollingIntervalRef.current) {
              clearInterval(pollingIntervalRef.current)
              pollingIntervalRef.current = null
            }
            onError(data.error || 'Unknown error occurred')
          }
        } catch (err) {
          console.error('Polling error:', err)
          // Continue polling even on error
        }
      }

      // Initial poll
      pollJobStatus()

      // Set up polling interval
      if (!pollingIntervalRef.current) {
        pollingIntervalRef.current = setInterval(pollJobStatus, 1500)
      }
    }
  }, [jobId, onComplete, onError])

  const fetchOutputImages = async () => {
    try {
      const response = await getOutputImages(jobId)
      setOutputImages(response.data.images || [])
    } catch (err) {
      console.error('Failed to fetch output images:', err)
      setOutputImages([])
    }
  }

  const handleDownloadByIndex = async (index, filename) => {
    try {
      await downloadImageByIndex(jobId, index, filename)
    } catch (err) {
      console.error(`Download error for image ${index}:`, err)
      setError(`Failed to download image ${index + 1}`)
    }
  }

  const handleCancel = async () => {
    try {
      // Stop polling
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }

      // Close WebSocket if active
      if (websocketRef.current) {
        websocketRef.current.close()
        websocketRef.current = null
      }

      // Delete job
      await deleteJob(jobId)
      onCancel()
    } catch (err) {
      console.error('Cancel error:', err)
      // Call onCancel anyway to let user continue
      onCancel()
    }
  }

  const getStatusColor = () => {
    switch (status) {
      case 'processing':
        return 'text-blue-600 bg-blue-50'
      case 'complete':
        return 'text-green-600 bg-green-50'
      case 'error':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case 'processing':
        return (
          <svg className="animate-spin h-8 w-8 text-blue-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        )
      case 'complete':
        return (
          <svg className="h-8 w-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'error':
        return (
          <svg className="h-8 w-8 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      default:
        return null
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="text-center mb-6">
        <h2 className="text-3xl font-bold text-gray-800 mb-2">
          {status === 'complete' ? '✨ Edit Complete!' : status === 'error' ? '❌ Error Occurred' : '⚙️ Processing...'}
        </h2>
        {status === 'complete' && outputImages.length > 0 && (
          <p className="text-gray-600">
            Generated {outputImages.length} {outputImages.length === 1 ? 'image' : 'images'} successfully
          </p>
        )}
      </div>

      <div className="space-y-6">
        {/* Status Badge */}
        <div className="flex items-center justify-center space-x-4">
          {getStatusIcon()}
          <div>
            <span className={`inline-block px-4 py-2 rounded-full font-semibold text-sm ${getStatusColor()}`}>
              {status.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Connection Method Info */}
        <div className="text-xs text-center text-gray-400">
          Using {connectionMethod} for updates
        </div>

        {/* Progress Information */}
        {progress && (
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="space-y-4">
              {/* Stage */}
              {progress.stage && (
                <div>
                  <p className="text-sm text-gray-600">Stage</p>
                  <p className="text-lg font-semibold text-gray-800">{progress.stage}</p>
                </div>
              )}

              {/* Message */}
              {progress.message && (
                <div>
                  <p className="text-sm text-gray-600">Status</p>
                  <p className="text-lg text-gray-800">{progress.message}</p>
                </div>
              )}

              {/* Progress Bar */}
              {progress.progress !== undefined && (
                <div>
                  <div className="flex justify-between text-sm text-gray-600 mb-2">
                    <span className="font-medium">Progress</span>
                    <span className="font-bold text-purple-600">{progress.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden shadow-inner">
                    <div
                      className="bg-gradient-to-r from-purple-500 to-blue-500 h-4 rounded-full transition-all duration-500 relative overflow-hidden"
                      style={{ width: `${progress.progress}%` }}
                    >
                      {/* Animated shimmer effect */}
                      {progress.progress < 100 && (
                        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Error Display */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            <strong className="font-bold">Error: </strong>
            <span>{error}</span>
          </div>
        )}

        {/* Output Images Display */}
        {status === 'complete' && outputImages.length > 0 && (
          <div className="space-y-4">
            <div className="text-center">
              <h3 className="text-lg font-semibold text-gray-800">
                Output Images ({outputImages.length})
              </h3>
              <p className="text-xs text-gray-500 mt-1">
                📁 Also saved to <code className="bg-gray-100 px-2 py-0.5 rounded">~/output/</code>
              </p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {outputImages.map((img) => (
                <div key={img.index} className="bg-gray-50 rounded-lg p-4 shadow-md">
                  {/* Image Preview */}
                  <div className="mb-3 relative group">
                    <img
                      src={getImagePreviewUrl(jobId, img.index)}
                      alt={`Output ${img.index + 1}`}
                      className="w-full h-64 object-contain rounded-lg border-2 border-gray-300 cursor-zoom-in hover:border-purple-500 transition-all"
                      onClick={() => setZoomedImage({ jobId, index: img.index, img })}
                      onError={(e) => {
                        e.target.style.display = 'none'
                      }}
                    />
                    {/* Click to zoom hint */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                      <div className="bg-black bg-opacity-70 text-white px-3 py-2 rounded-lg text-sm flex items-center gap-2">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0zM10 7v3m0 0v3m0-3h3m-3 0H7" />
                        </svg>
                        Click to enlarge
                      </div>
                    </div>
                  </div>

                  {/* Image Info */}
                  <div className="space-y-2 text-sm text-gray-600">
                    <div className="flex justify-between">
                      <span className="font-medium">Image {img.index + 1}</span>
                      {img.width && img.height && (
                        <span>{img.width} × {img.height}</span>
                      )}
                    </div>
                    {img.size_bytes && (
                      <div className="text-xs text-gray-500">
                        Size: {(img.size_bytes / 1024).toFixed(1)} KB
                      </div>
                    )}
                  </div>

                  {/* Download Button */}
                  <button
                    onClick={() => handleDownloadByIndex(img.index, img.filename)}
                    className="mt-3 w-full px-4 py-2 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-700 transition-colors flex items-center justify-center"
                  >
                    <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Download Image {img.index + 1}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Job ID */}
        <div className="text-sm text-gray-500 text-center">
          Job ID: <code className="bg-gray-100 px-2 py-1 rounded">{jobId}</code>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          {status === 'complete' && (
            <>
              <button
                onClick={onRestart}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
              >
                Edit Another Image
              </button>
            </>
          )}

          {status === 'processing' && (
            <button
              onClick={handleCancel}
              className="px-6 py-3 bg-red-600 text-white rounded-lg font-semibold hover:bg-red-700 transition-colors"
            >
              Cancel
            </button>
          )}

          {status === 'error' && (
            <>
              <button
                onClick={onCancel}
                className="px-6 py-3 bg-gray-600 text-white rounded-lg font-semibold hover:bg-gray-700 transition-colors"
              >
                Go Back
              </button>

              <button
                onClick={onRestart}
                className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
              >
                Start Over
              </button>
            </>
          )}
        </div>

        {/* Image Zoom Modal */}
        {zoomedImage && (
          <div
            className="fixed inset-0 bg-black bg-opacity-90 z-50 flex items-center justify-center p-4"
            onClick={() => setZoomedImage(null)}
          >
            <div className="relative max-w-7xl max-h-full">
              {/* Close button */}
              <button
                onClick={() => setZoomedImage(null)}
                className="absolute -top-12 right-0 text-white hover:text-gray-300 transition-colors"
              >
                <div className="flex items-center gap-2 bg-black bg-opacity-50 px-4 py-2 rounded-lg">
                  <span className="text-sm">Press ESC or click outside to close</span>
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              </button>

              {/* Zoomed Image */}
              <img
                src={getImagePreviewUrl(zoomedImage.jobId, zoomedImage.index)}
                alt={`Output ${zoomedImage.index + 1} - Full Size`}
                className="max-w-full max-h-[90vh] object-contain rounded-lg shadow-2xl"
                onClick={(e) => e.stopPropagation()}
              />

              {/* Image Info Overlay */}
              <div className="absolute bottom-4 left-4 bg-black bg-opacity-70 text-white px-4 py-2 rounded-lg">
                <p className="text-sm font-medium">Image {zoomedImage.index + 1}</p>
                {zoomedImage.img.width && zoomedImage.img.height && (
                  <p className="text-xs">{zoomedImage.img.width} × {zoomedImage.img.height}</p>
                )}
              </div>

              {/* Download button in modal */}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDownloadByIndex(zoomedImage.index, zoomedImage.img.filename)
                }}
                className="absolute bottom-4 right-4 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors flex items-center gap-2 shadow-lg"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
