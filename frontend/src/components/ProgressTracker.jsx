import { useState, useEffect, useRef } from 'react'
import { getJobStatus, downloadImage, deleteJob } from '../utils/api'

export default function ProgressTracker({ jobId, onComplete, onError, onCancel, onRestart }) {
  const [status, setStatus] = useState('processing')
  const [progress, setProgress] = useState(null)
  const [error, setError] = useState(null)
  const [connectionMethod, setConnectionMethod] = useState('polling')
  const pollingIntervalRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    console.log(`Starting HTTP polling for job ${jobId}`)
    setConnectionMethod('polling')

    // Poll job status every 1.5 seconds
    const pollJobStatus = async () => {
      try {
        const response = await getJobStatus(jobId)
        const data = response.data

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
    pollingIntervalRef.current = setInterval(pollJobStatus, 1500)

    // Cleanup on unmount
    return () => {
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }
    }
  }, [jobId, onComplete, onError])

  const handleDownload = async () => {
    try {
      await downloadImage(jobId)
    } catch (err) {
      console.error('Download error:', err)
      setError('Failed to download image')
    }
  }

  const handleCancel = async () => {
    try {
      // Stop polling
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current)
        pollingIntervalRef.current = null
      }

      await deleteJob(jobId)
      onCancel()
    } catch (err) {
      console.error('Cancel error:', err)
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
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        {status === 'complete' ? 'Edit Complete!' : 'Processing...'}
      </h2>

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
                    <span>Progress</span>
                    <span>{progress.progress}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-3">
                    <div
                      className="bg-purple-600 h-3 rounded-full transition-all duration-500"
                      style={{ width: `${progress.progress}%` }}
                    />
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

        {/* Job ID */}
        <div className="text-sm text-gray-500 text-center">
          Job ID: <code className="bg-gray-100 px-2 py-1 rounded">{jobId}</code>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-center space-x-4">
          {status === 'complete' && (
            <>
              <button
                onClick={handleDownload}
                className="px-6 py-3 bg-green-600 text-white rounded-lg font-semibold hover:bg-green-700 transition-colors flex items-center"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Image
              </button>

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
      </div>
    </div>
  )
}
