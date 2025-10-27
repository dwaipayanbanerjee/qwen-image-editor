import { useState } from 'react'

export default function EditConfig({ images, config, onChange, onGenerate, onBack }) {
  const [showAdvanced, setShowAdvanced] = useState(false)

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

  const estimatedTime = () => {
    const baseTime = 45 // seconds for 50 steps
    const timeMultiplier = config.num_inference_steps / 50
    return Math.round(baseTime * timeMultiplier)
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
            {images.map((image, index) => (
              <div key={index} className="relative">
                <img
                  src={URL.createObjectURL(image)}
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

        {/* Negative Prompt */}
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
            {/* CFG Scale */}
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

            {/* Inference Steps */}
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
          </div>
        )}

        {/* Estimated Time */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start">
            <svg
              className="w-5 h-5 text-blue-500 mt-0.5 mr-2"
              fill="currentColor"
              viewBox="0 0 20 20"
            >
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z"
                clipRule="evenodd"
              />
            </svg>
            <div className="text-sm text-blue-800">
              <p className="font-medium">Estimated processing time: ~{estimatedTime()} seconds</p>
              <p className="text-xs mt-1">Running on A40 GPU with {config.num_inference_steps} inference steps</p>
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
