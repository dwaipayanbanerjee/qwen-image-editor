import { useState, useEffect, useRef } from 'react'

const SEEDREAM_PRICE_PER_IMAGE = 0.03 // $0.03 per image

export default function EditConfig({ images, config, onChange, onGenerate, onBack }) {
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [imagePreviewUrls, setImagePreviewUrls] = useState([])

  // Ensure config has model_type, default to 'qwen'
  useEffect(() => {
    if (!config.model_type) {
      onChange({ ...config, model_type: 'qwen' })
    }
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
    }

    onChange(updates)
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

  const estimatedTime = () => {
    if (config.model_type === 'seedream') {
      // Seedream is faster, typically 30-60 seconds
      return config.enhance_prompt ? 60 : 40
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
    }
    return '0.00'
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        Configure Edit
      </h2>

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
        </div>

        {/* Model Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            AI Model *
          </label>
          <select
            value={config.model_type || 'qwen'}
            onChange={handleModelTypeChange}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
          >
            <option value="qwen">Qwen-Image-Edit (Local, Free)</option>
            <option value="seedream">Seedream-4 (Cloud, $0.03/image)</option>
          </select>
          <div className="mt-2 p-3 bg-gray-50 rounded-lg text-sm">
            {config.model_type === 'qwen' ? (
              <div className="text-gray-700">
                <strong>Qwen-Image-Edit:</strong> Runs locally on your Mac. Free to use, but requires 64GB RAM.
                Processing time: ~{estimatedTime()}s for {config.num_inference_steps} steps.
              </div>
            ) : (
              <div className="text-gray-700">
                <strong>Seedream-4:</strong> High-quality cloud generation via Replicate.
                Faster processing (~{estimatedTime()}s). Cost: ${estimatedCost()} for {config.max_images || 1} image(s).
              </div>
            )}
          </div>
        </div>

        {/* Prompt */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Edit Prompt *
          </label>
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

        {/* Negative Prompt (Qwen only) */}
        {config.model_type === 'qwen' && (
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
            {config.model_type === 'qwen' ? (
              <>
                {/* Qwen Settings */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Guidance Scale: {config.true_cfg_scale.toFixed(1)}
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
            ) : (
              <>
                {/* Seedream Settings */}
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
        <div className={config.model_type === 'seedream' ? "bg-yellow-50 border border-yellow-200 rounded-lg p-4" : "bg-blue-50 border border-blue-200 rounded-lg p-4"}>
          <div className="flex items-start">
            <svg
              className={config.model_type === 'seedream' ? "w-5 h-5 text-yellow-500 mt-0.5 mr-2" : "w-5 h-5 text-blue-500 mt-0.5 mr-2"}
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            <div className={config.model_type === 'seedream' ? "text-sm text-yellow-800" : "text-sm text-blue-800"}>
              <p className="font-medium">Estimated processing time: ~{estimatedTime()} seconds</p>
              {config.model_type === 'qwen' ? (
                <p className="text-xs mt-1">Running locally on your Mac with {config.num_inference_steps} inference steps</p>
              ) : (
                <>
                  <p className="text-xs mt-1">Running on Replicate cloud (Seedream-4)</p>
                  <p className="font-semibold mt-2">Cost: ${estimatedCost()} USD</p>
                  <p className="text-xs">({config.max_images || 1} image(s) × $0.03 per image)</p>
                </>
              )}
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
            onClick={onGenerate}
            disabled={!config.prompt.trim()}
            className="px-8 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Generate Edited Image
          </button>
        </div>
      </div>
    </div>
  )
}
