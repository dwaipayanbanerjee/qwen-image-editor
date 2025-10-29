import { useState, useEffect, useRef } from 'react'

// Pricing constants
const SEEDREAM_PRICE_PER_IMAGE = 0.03
const QWEN_IMAGE_EDIT_PRICE = 0.01
const QWEN_IMAGE_EDIT_PLUS_PRICE = 0.02
const QWEN_IMAGE_PRICE = 0.015

const PROMPT_HISTORY_KEY = 'qwen_editor_prompt_history'
const MAX_HISTORY_SIZE = 20

export default function EditConfig({ images, config, onChange, onGenerate, onBack }) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [imagePreviewUrls, setImagePreviewUrls] = useState([])
  const [promptHistory, setPromptHistory] = useState([])
  const [showHistoryDropdown, setShowHistoryDropdown] = useState(false)
  const historyDropdownRef = useRef(null)

  // Load prompt history from localStorage
  useEffect(() => {
    try {
      const history = JSON.parse(localStorage.getItem(PROMPT_HISTORY_KEY) || '[]')
      setPromptHistory(history)
    } catch (err) {
      console.error('Failed to load prompt history:', err)
      setPromptHistory([])
    }
  }, [])

  // Ensure config has model_type, default to 'qwen'
  useEffect(() => {
    if (!config.model_type) {
      onChange({ ...config, model_type: 'qwen' })
    }
  }, [])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (historyDropdownRef.current && !historyDropdownRef.current.contains(event.target)) {
        setShowHistoryDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Create and cleanup object URLs
  useEffect(() => {
    const urls = images.map(image => URL.createObjectURL(image))
    setImagePreviewUrls(urls)

    // Cleanup function to revoke URLs
    return () => {
      urls.forEach(url => URL.revokeObjectURL(url))
    }
  }, [images])

  const handlePromptChange = (e) => {
    onChange({ ...config, prompt: e.target.value })
  }

  const selectPromptFromHistory = (prompt) => {
    onChange({ ...config, prompt })
    setShowHistoryDropdown(false)
  }

  const savePromptToHistory = (prompt) => {
    if (!prompt || !prompt.trim()) return

    try {
      // Remove duplicates and add to front
      const newHistory = [prompt, ...promptHistory.filter(p => p !== prompt)].slice(0, MAX_HISTORY_SIZE)
      setPromptHistory(newHistory)
      localStorage.setItem(PROMPT_HISTORY_KEY, JSON.stringify(newHistory))
    } catch (err) {
      console.error('Failed to save prompt history:', err)
    }
  }

  const clearPromptHistory = () => {
    setPromptHistory([])
    localStorage.removeItem(PROMPT_HISTORY_KEY)
    setShowHistoryDropdown(false)
  }

  const handleNegativePromptChange = (e) => {
    onChange({ ...config, negative_prompt: e.target.value })
  }

  const handleCfgScaleChange = (e) => {
    onChange({ ...config, true_cfg_scale: parseFloat(e.target.value) })
  }

  const handleStepsChange = (e) => {
    onChange({ ...config, num_inference_steps: parseInt(e.target.value) })
  }

  const handleModelTypeChange = (e) => {
    const modelType = e.target.value
    // Update model type and set appropriate defaults
    const updates = { ...config, model_type: modelType }

    if (modelType === 'seedream') {
      // Set Seedream defaults
      updates.size = config.size || '2K'
      updates.aspect_ratio = config.aspect_ratio || '4:3'
      updates.enhance_prompt = config.enhance_prompt || false
      updates.sequential_image_generation = config.sequential_image_generation || 'disabled'
      updates.max_images = config.max_images || 1
    } else if (modelType === 'qwen_gguf') {
      // Set GGUF defaults
      updates.quantization_level = config.quantization_level || 'Q5_K_S'
    }

    onChange(updates)
  }

  const handleQuantizationLevelChange = (e) => {
    onChange({ ...config, quantization_level: e.target.value })
  }

  const handleSizeChange = (e) => {
    onChange({ ...config, size: e.target.value })
  }

  const handleAspectRatioChange = (e) => {
    onChange({ ...config, aspect_ratio: e.target.value })
  }

  const handleEnhancePromptChange = (e) => {
    onChange({ ...config, enhance_prompt: e.target.checked })
  }

  const handleMaxImagesChange = (e) => {
    onChange({ ...config, max_images: parseInt(e.target.value) })
  }

  const handleDisableSafetyCheckerChange = (e) => {
    onChange({ ...config, disable_safety_checker: e.target.checked })
  }

  const estimatedTime = () => {
    if (config.model_type === 'seedream') {
      // Seedream is faster, typically 30-60 seconds
      return config.enhance_prompt ? 60 : 40
    } else if (config.model_type === 'qwen_gguf') {
      // GGUF is faster than standard Qwen, typically 20-30% faster
      const baseTime = 32 // seconds for 50 steps (faster than standard)
      const timeMultiplier = config.num_inference_steps / 50
      return Math.round(baseTime * timeMultiplier)
    } else {
      // Qwen time based on steps
      const baseTime = 45 // seconds for 50 steps
      const timeMultiplier = config.num_inference_steps / 50
      return Math.round(baseTime * timeMultiplier)
    }
  }

  const estimatedCost = () => {
    if (config.model_type === 'seedream') {
      const maxImages = config.max_images || 1
      return (maxImages * SEEDREAM_PRICE_PER_IMAGE).toFixed(2)
    } else if (config.model_type === 'qwen_image_edit') {
      return QWEN_IMAGE_EDIT_PRICE.toFixed(2)
    } else if (config.model_type === 'qwen_image_edit_plus') {
      return QWEN_IMAGE_EDIT_PLUS_PRICE.toFixed(2)
    } else if (config.model_type === 'qwen_image') {
      return QWEN_IMAGE_PRICE.toFixed(3)
    }
    return '0.00'
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          Configure Edit
        </h2>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 bg-gray-100 text-gray-700 rounded-full text-sm font-medium">
            {images.length} {images.length === 1 ? 'Image' : 'Images'}
          </span>
          {config.model_type === 'seedream' && config.max_images > 1 && (
            <span className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-sm font-medium">
              {config.max_images} Output{config.max_images > 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      <div className="space-y-6">
        {/* Image Preview */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Selected Images ({images.length})
          </label>
          <div className="grid grid-cols-2 gap-4">
            {imagePreviewUrls.map((url, index) => (
              <div key={index} className="relative">
                <img
                  src={url}
                  alt={`Selected ${index + 1}`}
                  className="w-full h-40 object-cover rounded-lg border-2 border-gray-200"
                />
                <div className="absolute bottom-2 left-2 bg-black bg-opacity-60 text-white px-2 py-1 rounded text-sm">
                  Image {index + 1}
                </div>
              </div>
            ))}
          </div>

          {/* Warning for too many images with Qwen */}
          {(config.model_type === 'qwen' || config.model_type === 'qwen_gguf') && images.length > 2 && (
            <div className="mt-3 bg-yellow-50 border border-yellow-300 rounded-lg p-3">
              <div className="flex items-start">
                <svg className="w-5 h-5 text-yellow-600 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="text-sm text-yellow-800">
                  <p className="font-semibold">Note: Qwen models support maximum 2 images</p>
                  <p className="text-xs">Only the first 2 images will be used. For {images.length} images, use Seedream model instead.</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            AI Model *
          </label>

          {/* Local Models */}
          <div className="mb-4">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Local Models (Free)</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Qwen Standard */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'qwen' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'qwen'
                  ? 'border-purple-500 bg-purple-50 shadow-md'
                  : 'border-gray-200 hover:border-purple-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800">Qwen Standard</div>
                <div className="px-2 py-0.5 bg-purple-100 text-purple-700 rounded text-xs font-medium">FREE</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Full quality (20B params)</div>
                <div>• ~45s / 50 steps</div>
                <div>• 64GB RAM needed</div>
              </div>
              {config.model_type === 'qwen' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-purple-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            {/* Qwen GGUF */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'qwen_gguf' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'qwen_gguf'
                  ? 'border-green-500 bg-green-50 shadow-md'
                  : 'border-gray-200 hover:border-green-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800">GGUF Quantized</div>
                <div className="px-2 py-0.5 bg-green-100 text-green-700 rounded text-xs font-medium">RECOMMENDED</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Faster (~32s / 50 steps)</div>
                <div>• Less VRAM (17GB)</div>
                <div>• Good quality</div>
              </div>
              {config.model_type === 'qwen_gguf' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            </div>
          </div>

          {/* Cloud Models */}
          <div className="mb-3">
            <div className="text-xs font-semibold text-gray-500 uppercase mb-2">Cloud Models (Paid via Replicate)</div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
            {/* Qwen-Image-Edit Cloud */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'qwen_image_edit' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'qwen_image_edit'
                  ? 'border-orange-500 bg-orange-50 shadow-md'
                  : 'border-gray-200 hover:border-orange-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800 text-sm">Qwen Edit</div>
                <div className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded text-xs font-medium">$0.01</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Simple edits</div>
                <div>• 1 input, 1 output</div>
                <div>• Cheapest option</div>
              </div>
              {config.model_type === 'qwen_image_edit' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-orange-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            {/* Qwen-Image-Edit-Plus */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'qwen_image_edit_plus' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'qwen_image_edit_plus'
                  ? 'border-pink-500 bg-pink-50 shadow-md'
                  : 'border-gray-200 hover:border-pink-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800 text-sm">Qwen Edit+</div>
                <div className="px-2 py-0.5 bg-pink-100 text-pink-700 rounded text-xs font-medium">$0.02</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Pose/style transfer</div>
                <div>• 1-2 inputs</div>
                <div>• Advanced edits</div>
              </div>
              {config.model_type === 'qwen_image_edit_plus' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-pink-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            {/* Qwen-Image Text-to-Image */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'qwen_image' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'qwen_image'
                  ? 'border-indigo-500 bg-indigo-50 shadow-md'
                  : 'border-gray-200 hover:border-indigo-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800 text-sm">Qwen Image</div>
                <div className="px-2 py-0.5 bg-indigo-100 text-indigo-700 rounded text-xs font-medium">$0.015</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Text-to-image</div>
                <div>• No input needed</div>
                <div>• Create from text</div>
              </div>
              {config.model_type === 'qwen_image' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-indigo-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>

            {/* Seedream */}
            <button
              type="button"
              onClick={() => handleModelTypeChange({ target: { value: 'seedream' }})}
              className={`relative p-4 border-2 rounded-lg text-left transition-all ${
                config.model_type === 'seedream'
                  ? 'border-blue-500 bg-blue-50 shadow-md'
                  : 'border-gray-200 hover:border-blue-300'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="font-semibold text-gray-800 text-sm">Seedream-4</div>
                <div className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">$0.03/img</div>
              </div>
              <div className="text-xs text-gray-600 space-y-1">
                <div>• Multi-output (~40s)</div>
                <div>• 1-10 inputs</div>
                <div>• 1-15 outputs</div>
              </div>
              {config.model_type === 'seedream' && (
                <div className="absolute top-2 right-2">
                  <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </button>
            </div>
          </div>

          {/* Hidden select for form compatibility */}
          <select
            value={config.model_type || 'qwen'}
            onChange={handleModelTypeChange}
            className="hidden"
          >
            <option value="qwen">Qwen-Image-Edit</option>
            <option value="qwen_gguf">Qwen-Image-Edit-2509 GGUF</option>
            <option value="qwen_image_edit">Qwen-Image-Edit (Cloud)</option>
            <option value="qwen_image_edit_plus">Qwen-Image-Edit-Plus</option>
            <option value="qwen_image">Qwen-Image (Text-to-Image)</option>
            <option value="seedream">Seedream-4</option>
          </select>
          {/* Model Info Badge */}
          <div className={`p-3 rounded-lg text-sm border ${
            config.model_type === 'qwen' ? 'bg-purple-50 border-purple-200' :
            config.model_type === 'qwen_gguf' ? 'bg-green-50 border-green-200' :
            config.model_type === 'qwen_image_edit' ? 'bg-orange-50 border-orange-200' :
            config.model_type === 'qwen_image_edit_plus' ? 'bg-pink-50 border-pink-200' :
            config.model_type === 'qwen_image' ? 'bg-indigo-50 border-indigo-200' :
            'bg-blue-50 border-blue-200'
          }`}>
            <div className="flex items-start gap-2">
              <svg className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
                config.model_type === 'qwen' ? 'text-purple-600' :
                config.model_type === 'qwen_gguf' ? 'text-green-600' :
                config.model_type === 'qwen_image_edit' ? 'text-orange-600' :
                config.model_type === 'qwen_image_edit_plus' ? 'text-pink-600' :
                config.model_type === 'qwen_image' ? 'text-indigo-600' :
                'text-blue-600'
              }`} fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                {config.model_type === 'qwen' ? (
                  <>
                    <p className="font-medium text-gray-800">Local processing with full 20B parameter model</p>
                    <p className="text-xs text-gray-600 mt-1">1-2 input images • 1 output • {config.num_inference_steps} steps</p>
                  </>
                ) : config.model_type === 'qwen_gguf' ? (
                  <>
                    <p className="font-medium text-gray-800">Faster quantized model, best for most users</p>
                    <p className="text-xs text-gray-600 mt-1">1-2 input images • 1 output • {config.num_inference_steps} steps • {config.quantization_level || 'Q5_K_S'}</p>
                  </>
                ) : config.model_type === 'qwen_image_edit' ? (
                  <>
                    <p className="font-medium text-gray-800">Simple cloud-based image editing</p>
                    <p className="text-xs text-gray-600 mt-1">1 input image • 1 output • $0.01 per prediction</p>
                  </>
                ) : config.model_type === 'qwen_image_edit_plus' ? (
                  <>
                    <p className="font-medium text-gray-800">Advanced pose and style transfer</p>
                    <p className="text-xs text-gray-600 mt-1">1-2 input images • 1 output • $0.02 per prediction</p>
                  </>
                ) : config.model_type === 'qwen_image' ? (
                  <>
                    <p className="font-medium text-gray-800">Text-to-image generation (no input image needed)</p>
                    <p className="text-xs text-gray-600 mt-1">Text prompt only • 1 output • $0.015 per prediction</p>
                  </>
                ) : (
                  <>
                    <p className="font-medium text-gray-800">High-quality cloud generation with multi-output support</p>
                    <p className="text-xs text-gray-600 mt-1">1-10 input images • 1-{config.max_images || 1} output images • Cost: ${estimatedCost()}</p>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Quantization Level Selection (GGUF only) */}
        {config.model_type === 'qwen_gguf' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Quantization Level
            </label>
            <select
              value={config.quantization_level || 'Q5_K_S'}
              onChange={handleQuantizationLevelChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            >
              <option value="Q2_K">Q2_K - Lowest quality, fastest, ~7GB VRAM</option>
              <option value="Q4_K_M">Q4_K_M - Good quality, fast, ~14GB VRAM</option>
              <option value="Q5_K_S">Q5_K_S - Best balance (Recommended), ~17GB VRAM</option>
              <option value="Q8_0">Q8_0 - Highest quality, slower, ~22GB VRAM</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Higher quantization = better quality but more VRAM and slower processing. Q5_K_S is recommended for most users.
            </p>
          </div>
        )}

        {/* Prompt */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-gray-700">
              Edit Prompt *
            </label>
            {promptHistory.length > 0 && (
              <button
                type="button"
                onClick={() => setShowHistoryDropdown(!showHistoryDropdown)}
                className="text-xs text-purple-600 hover:text-purple-700 font-medium flex items-center"
              >
                <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                History ({promptHistory.length})
              </button>
            )}
          </div>

          {/* Prompt History Dropdown */}
          {showHistoryDropdown && promptHistory.length > 0 && (
            <div ref={historyDropdownRef} className="mb-2 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              <div className="flex items-center justify-between p-2 border-b border-gray-200">
                <span className="text-xs font-semibold text-gray-700">Recent Prompts</span>
                <button
                  type="button"
                  onClick={clearPromptHistory}
                  className="text-xs text-red-600 hover:text-red-700"
                >
                  Clear All
                </button>
              </div>
              <div className="divide-y divide-gray-100">
                {promptHistory.map((historyPrompt, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => selectPromptFromHistory(historyPrompt)}
                    className="w-full text-left px-3 py-2 hover:bg-purple-50 transition-colors"
                  >
                    <p className="text-sm text-gray-800 line-clamp-2">{historyPrompt}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          <textarea
            value={config.prompt}
            onChange={handlePromptChange}
            placeholder="Describe what you want to change in the image(s)... e.g., 'change the background to a sunset sky' or 'make the person wearing a red hat'"
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
            rows={4}
            required
          />
          <p className="mt-1 text-sm text-gray-500">
            Be specific about what you want to edit. The model works best with clear, detailed instructions.
          </p>
        </div>

        {/* Negative Prompt (Qwen models only) */}
        {(config.model_type === 'qwen' || config.model_type === 'qwen_gguf') && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Negative Prompt (Optional)
            </label>
            <textarea
              value={config.negative_prompt}
              onChange={handleNegativePromptChange}
              placeholder="Describe what you want to avoid... e.g., 'blurry, low quality, distorted'"
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
              rows={2}
            />
            <p className="mt-1 text-sm text-gray-500">
              Help guide the model by specifying what to avoid in the output.
            </p>
          </div>
        )}

        {/* Advanced Settings Toggle */}
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-purple-600 hover:text-purple-700 font-medium text-sm flex items-center"
        >
          {showAdvanced ? '▼' : '▶'} Advanced Settings
        </button>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="bg-gray-50 rounded-lg p-4 space-y-4">
            {/* Common Cloud Model Settings */}
            {(config.model_type === 'seedream' || config.model_type === 'qwen_image_edit' || config.model_type === 'qwen_image_edit_plus' || config.model_type === 'qwen_image') && (
              <div className="pb-4 border-b border-gray-300">
                <h4 className="font-semibold text-sm text-gray-700 mb-3">Cloud Model Settings</h4>
                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="disable_safety_checker"
                    checked={config.disable_safety_checker !== false}
                    onChange={handleDisableSafetyCheckerChange}
                    className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                  />
                  <label htmlFor="disable_safety_checker" className="ml-2 text-sm text-gray-700">
                    Disable Safety Checker (allows NSFW content)
                  </label>
                </div>
                <p className="mt-1 text-xs text-gray-500 ml-6">
                  ⚠️ Disables content filtering. Use responsibly. Default: enabled for flexibility.
                </p>
              </div>
            )}

            {/* Qwen Local Models Settings */}
            {(config.model_type === 'qwen' || config.model_type === 'qwen_gguf') && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Guidance Scale (CFG): {config.true_cfg_scale.toFixed(1)}
                  </label>
                  <input
                    type="range"
                    min="1.0"
                    max="10.0"
                    step="0.5"
                    value={config.true_cfg_scale}
                    onChange={handleCfgScaleChange}
                    className="w-full"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Higher values = stronger adherence to prompt (recommended: 4.0)
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Inference Steps: {config.num_inference_steps}
                  </label>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    step="10"
                    value={config.num_inference_steps}
                    onChange={handleStepsChange}
                    className="w-full"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    More steps = better quality but slower (recommended: 50)
                  </p>
                </div>
              </>
            )}

            {/* Qwen-Image Text-to-Image Settings */}
            {config.model_type === 'qwen_image' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Guidance Scale: {config.guidance?.toFixed(1) || '4.0'}
                  </label>
                  <input
                    type="range"
                    min="1.0"
                    max="20.0"
                    step="0.5"
                    value={config.guidance || 4.0}
                    onChange={(e) => onChange({ ...config, guidance: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    Higher values = stronger adherence to prompt
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Inference Steps: {config.num_inference_steps}
                  </label>
                  <input
                    type="range"
                    min="20"
                    max="100"
                    step="10"
                    value={config.num_inference_steps}
                    onChange={handleStepsChange}
                    className="w-full"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    More steps = better quality but slower
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Generation Strength: {config.strength?.toFixed(2) || '0.90'}
                  </label>
                  <input
                    type="range"
                    min="0.0"
                    max="1.0"
                    step="0.1"
                    value={config.strength || 0.9}
                    onChange={(e) => onChange({ ...config, strength: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    How much the model transforms the prompt (0.0-1.0)
                  </p>
                </div>
              </>
            )}

            {/* Seedream Settings */}
            {config.model_type === 'seedream' && (
              <>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Image Resolution
                  </label>
                  <select
                    value={config.size || '2K'}
                    onChange={handleSizeChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="1K">1K (1024px)</option>
                    <option value="2K">2K (2048px)</option>
                    <option value="4K">4K (4096px)</option>
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    Higher resolution = better quality but slightly slower
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Aspect Ratio
                  </label>
                  <select
                    value={config.aspect_ratio || '4:3'}
                    onChange={handleAspectRatioChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  >
                    <option value="1:1">1:1 (Square)</option>
                    <option value="4:3">4:3 (Standard)</option>
                    <option value="3:4">3:4 (Portrait)</option>
                    <option value="16:9">16:9 (Widescreen)</option>
                    <option value="9:16">9:16 (Mobile)</option>
                    <option value="match_input_image">Match Input Image</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Max Images to Generate
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="15"
                    value={config.max_images || 1}
                    onChange={handleMaxImagesChange}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  />
                  <p className="mt-1 text-xs text-gray-500">
                    More images = higher cost (${(config.max_images || 1) * SEEDREAM_PRICE_PER_IMAGE})
                  </p>
                </div>

                <div className="flex items-center">
                  <input
                    type="checkbox"
                    id="enhance_prompt"
                    checked={config.enhance_prompt || false}
                    onChange={handleEnhancePromptChange}
                    className="w-4 h-4 text-purple-600 border-gray-300 rounded focus:ring-purple-500"
                  />
                  <label htmlFor="enhance_prompt" className="ml-2 text-sm text-gray-700">
                    Enhance Prompt (slower but better quality)
                  </label>
                </div>
              </>
            )}
          </div>
        )}

        {/* Estimated Time & Cost */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Time Estimate */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-blue-500 mt-0.5 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
              </svg>
              <div className="text-sm text-blue-800">
                <p className="font-semibold">Processing Time</p>
                <p className="text-2xl font-bold mt-1">~{estimatedTime()}s</p>
                <p className="text-xs mt-1 text-blue-600">
                  {config.model_type === 'seedream' ? 'Cloud processing' : 'Local processing'}
                </p>
              </div>
            </div>
          </div>

          {/* Cost Estimate */}
          <div className={`rounded-lg p-4 border ${
            config.model_type === 'qwen' || config.model_type === 'qwen_gguf'
              ? 'bg-green-50 border-green-200'
              : 'bg-yellow-50 border-yellow-200'
          }`}>
            <div className="flex items-start">
              <svg className={`w-5 h-5 mt-0.5 mr-2 ${
                config.model_type === 'qwen' || config.model_type === 'qwen_gguf' ? 'text-green-600' : 'text-yellow-600'
              }`} fill="currentColor" viewBox="0 0 20 20">
                <path d="M8.433 7.418c.155-.103.346-.196.567-.267v1.698a2.305 2.305 0 01-.567-.267C8.07 8.34 8 8.114 8 8c0-.114.07-.34.433-.582zM11 12.849v-1.698c.22.071.412.164.567.267.364.243.433.468.433.582 0 .114-.07.34-.433.582a2.305 2.305 0 01-.567.267z" />
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-13a1 1 0 10-2 0v.092a4.535 4.535 0 00-1.676.662C6.602 6.234 6 7.009 6 8c0 .99.602 1.765 1.324 2.246.48.32 1.054.545 1.676.662v1.941c-.391-.127-.68-.317-.843-.504a1 1 0 10-1.51 1.31c.562.649 1.413 1.076 2.353 1.253V15a1 1 0 102 0v-.092a4.535 4.535 0 001.676-.662C13.398 13.766 14 12.991 14 12c0-.99-.602-1.765-1.324-2.246A4.535 4.535 0 0011 9.092V7.151c.391.127.68.317.843.504a1 1 0 101.511-1.31c-.563-.649-1.413-1.076-2.354-1.253V5z" clipRule="evenodd" />
              </svg>
              <div className={`text-sm ${
                config.model_type === 'qwen' || config.model_type === 'qwen_gguf' ? 'text-green-800' : 'text-yellow-800'
              }`}>
                <p className="font-semibold">Cost</p>
                <p className="text-2xl font-bold mt-1">
                  {config.model_type === 'qwen' || config.model_type === 'qwen_gguf' ? 'FREE' : `$${estimatedCost()}`}
                </p>
                <p className="text-xs mt-1">
                  {config.model_type === 'qwen' || config.model_type === 'qwen_gguf' ? 'No API costs' :
                   config.model_type === 'seedream' ? `${config.max_images || 1} × $0.03 per image` :
                   'Per prediction cost'}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <button
            onClick={onBack}
            className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
          >
            Back
          </button>

          <button
            onClick={() => {
              savePromptToHistory(config.prompt)
              onGenerate()
            }}
            disabled={!config.prompt.trim()}
            className="px-8 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-2"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Generate Edited Image
          </button>
        </div>
      </div>
    </div>
  )
}
