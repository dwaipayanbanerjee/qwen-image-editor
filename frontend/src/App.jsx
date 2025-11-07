import { useState, useEffect } from 'react'
import ImageUpload from './components/ImageUpload'
import EditConfig from './components/EditConfig'
import ProgressTracker from './components/ProgressTracker'
import { generateEdit, getJobStatus } from './utils/api'

function App() {
  // State management
  const [step, setStep] = useState('upload') // upload, config, processing
  const [images, setImages] = useState([]) // Array of File objects (1-10 images depending on model)
  const [config, setConfig] = useState({
    model_type: 'qwen_gguf',
    prompt: '',
    negative_prompt: '',
    true_cfg_scale: 4.0,
    num_inference_steps: 50,
    quantization_level: 'Q5_K_S'
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
    // Text-to-image models don't require input images
    const textToImageModels = ['hunyuan', 'qwen_image']
    const requiresImage = !textToImageModels.includes(config.model_type)

    if (requiresImage && images.length === 0) {
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
      model_type: 'qwen_gguf',
      prompt: '',
      negative_prompt: '',
      true_cfg_scale: 4.0,
      num_inference_steps: 50,
      quantization_level: 'Q5_K_S'
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
          <h1 className="text-5xl font-bold bg-gradient-to-r from-purple-600 to-blue-600 bg-clip-text text-transparent mb-3">
            Image Editor
          </h1>
          <p className="text-gray-600 text-lg">
            AI-powered editing with Qwen GGUF, Hunyuan, and Seedream models
          </p>
          <div className="mt-2 flex justify-center gap-2 text-xs">
            <span className="px-2 py-1 bg-purple-100 text-purple-700 rounded-full font-medium">Local Models</span>
            <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded-full font-medium">Cloud API</span>
            <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full font-medium">Multi-Output</span>
          </div>
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
              maxImages={10}
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
        <div className="text-center mt-12 pb-8">
          <div className="max-w-2xl mx-auto">
            <div className="bg-white rounded-lg shadow-sm p-6 mb-4">
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <div className="text-2xl font-bold text-purple-600">6</div>
                  <div className="text-xs text-gray-600 mt-1">AI Models</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-blue-600">10</div>
                  <div className="text-xs text-gray-600 mt-1">Max Inputs</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-green-600">15</div>
                  <div className="text-xs text-gray-600 mt-1">Max Outputs</div>
                </div>
              </div>
            </div>
            <p className="text-gray-500 text-sm">
              Powered by Qwen-Image-Edit, GGUF Quantization, and Seedream-4
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
