import { useState, useEffect } from 'react'
import ImageUpload from './components/ImageUpload'
import EditConfig from './components/EditConfig'
import ProgressTracker from './components/ProgressTracker'
import { generateEdit, getJobStatus } from './utils/api'

function App() {
  // State management
  const [step, setStep] = useState('upload') // upload, config, processing
  const [images, setImages] = useState([]) // Array of File objects (1-2 images)
  const [config, setConfig] = useState({
    prompt: '',
    negative_prompt: '',
    true_cfg_scale: 4.0,
    num_inference_steps: 50
  })
  const [jobId, setJobId] = useState(null)
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState(null)

  // Load saved job from localStorage on mount
  useEffect(() => {
    const savedJob = localStorage.getItem('qwen_editor_current_job')
    if (savedJob) {
      const jobId = savedJob
      // Check if job still exists
      getJobStatus(jobId)
        .then(response => {
          if (response.data.status === 'complete' || response.data.status === 'error') {
            localStorage.removeItem('qwen_editor_current_job')
          } else {
            setJobId(jobId)
            setStep('processing')
            setIsProcessing(true)
          }
        })
        .catch(() => {
          localStorage.removeItem('qwen_editor_current_job')
        })
    }
  }, [])

  const handleImagesReady = (uploadedImages) => {
    setImages(uploadedImages)
    setStep('config')
    setError(null)
  }

  const handleConfigChange = (newConfig) => {
    setConfig(newConfig)
  }

  const handleGenerate = async () => {
    if (images.length === 0) {
      setError('Please upload at least one image')
      return
    }

    if (!config.prompt.trim()) {
      setError('Please enter an edit prompt')
      return
    }

    try {
      setError(null)
      setIsProcessing(true)
      setStep('processing')

      const response = await generateEdit(images, config)
      const { job_id } = response.data

      setJobId(job_id)
      localStorage.setItem('qwen_editor_current_job', job_id)

    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start image editing')
      setIsProcessing(false)
      setStep('config')
    }
  }

  const handleComplete = () => {
    setIsProcessing(false)
    localStorage.removeItem('qwen_editor_current_job')
  }

  const handleError = (errorMessage) => {
    setError(errorMessage)
    setIsProcessing(false)
    localStorage.removeItem('qwen_editor_current_job')
  }

  const handleCancel = () => {
    setJobId(null)
    setIsProcessing(false)
    setStep('upload')
    setImages([])
    setConfig({
      prompt: '',
      negative_prompt: '',
      true_cfg_scale: 4.0,
      num_inference_steps: 50
    })
    localStorage.removeItem('qwen_editor_current_job')
  }

  const handleRestart = () => {
    setJobId(null)
    setIsProcessing(false)
    setStep('upload')
    setImages([])
    setError(null)
    localStorage.removeItem('qwen_editor_current_job')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50 to-blue-50">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            Qwen Image Editor
          </h1>
          <p className="text-gray-600">
            AI-powered image editing using Qwen-Image-Edit model
          </p>
        </div>

        {/* Error Display */}
        {error && (
          <div className="max-w-2xl mx-auto mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
            <strong className="font-bold">Error: </strong>
            <span>{error}</span>
          </div>
        )}

        {/* Main Content */}
        <div className="max-w-4xl mx-auto">
          {step === 'upload' && (
            <ImageUpload
              onImagesReady={handleImagesReady}
              maxImages={2}
            />
          )}

          {step === 'config' && (
            <EditConfig
              images={images}
              config={config}
              onChange={handleConfigChange}
              onGenerate={handleGenerate}
              onBack={() => setStep('upload')}
            />
          )}

          {step === 'processing' && jobId && (
            <ProgressTracker
              jobId={jobId}
              onComplete={handleComplete}
              onError={handleError}
              onCancel={handleCancel}
              onRestart={handleRestart}
            />
          )}
        </div>

        {/* Footer */}
        <div className="text-center mt-12 text-gray-500 text-sm">
          <p>Powered by Qwen-Image-Edit • Running on RunPod A40</p>
        </div>
      </div>
    </div>
  )
}

export default App
