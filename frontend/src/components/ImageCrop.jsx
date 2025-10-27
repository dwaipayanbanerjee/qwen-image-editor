import { useState, useRef } from 'react'
import ReactCrop from 'react-image-crop'
import 'react-image-crop/dist/ReactCrop.css'

// Optimal aspect ratios for Qwen-Image-Edit model
const ASPECT_RATIOS = [
  { name: 'Square (1:1)', value: 1, width: 1328, height: 1328 },
  { name: 'Landscape 16:9', value: 16 / 9, width: 1664, height: 928 },
  { name: 'Portrait 9:16', value: 9 / 16, width: 928, height: 1664 },
  { name: 'Standard 4:3', value: 4 / 3, width: 1472, height: 1140 },
  { name: 'Standard 3:4', value: 3 / 4, width: 1140, height: 1472 },
  { name: 'Free', value: null, width: null, height: null }
]

export default function ImageCrop({ image, imageName, onCropComplete, onSkip }) {
  const [crop, setCrop] = useState({
    unit: '%',
    width: 90,
    height: 90,
    x: 5,
    y: 5
  })
  const [completedCrop, setCompletedCrop] = useState(null)
  const [selectedRatio, setSelectedRatio] = useState(0) // Default to Square
  const imgRef = useRef(null)
  const previewCanvasRef = useRef(null)

  // Set initial aspect ratio
  const initializeAspectRatio = (aspectValue) => {
    if (aspectValue) {
      setCrop({
        unit: '%',
        width: 90,
        height: 90 / aspectValue,
        x: 5,
        y: 5,
        aspect: aspectValue
      })
    } else {
      setCrop({
        unit: '%',
        width: 90,
        height: 90,
        x: 5,
        y: 5
      })
    }
  }

  const handleAspectRatioChange = (index) => {
    setSelectedRatio(index)
    initializeAspectRatio(ASPECT_RATIOS[index].value)
  }

  const generateCroppedImage = async () => {
    if (!completedCrop || !imgRef.current) {
      onSkip()
      return
    }

    const image = imgRef.current
    const canvas = document.createElement('canvas')
    const scaleX = image.naturalWidth / image.width
    const scaleY = image.naturalHeight / image.height

    // Calculate crop dimensions
    const pixelCrop = {
      x: completedCrop.x * scaleX,
      y: completedCrop.y * scaleY,
      width: completedCrop.width * scaleX,
      height: completedCrop.height * scaleY
    }

    canvas.width = pixelCrop.width
    canvas.height = pixelCrop.height

    const ctx = canvas.getContext('2d')
    ctx.drawImage(
      image,
      pixelCrop.x,
      pixelCrop.y,
      pixelCrop.width,
      pixelCrop.height,
      0,
      0,
      pixelCrop.width,
      pixelCrop.height
    )

    // Convert canvas to blob
    return new Promise((resolve) => {
      canvas.toBlob((blob) => {
        if (!blob) {
          resolve(null)
          return
        }
        // Create a File from the blob
        const file = new File([blob], imageName, { type: 'image/jpeg' })
        resolve(file)
      }, 'image/jpeg', 0.95)
    })
  }

  const handleApplyCrop = async () => {
    const croppedFile = await generateCroppedImage()
    if (croppedFile) {
      onCropComplete(croppedFile)
    } else {
      onSkip()
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        Crop Image: {imageName}
      </h2>

      {/* Aspect Ratio Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-3">
          Select Aspect Ratio (Optimized for Qwen-Image-Edit)
        </label>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2">
          {ASPECT_RATIOS.map((ratio, index) => (
            <button
              key={index}
              onClick={() => handleAspectRatioChange(index)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                selectedRatio === index
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <div className="font-semibold">{ratio.name}</div>
              {ratio.width && (
                <div className="text-xs opacity-80 mt-1">
                  {ratio.width}×{ratio.height}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex items-start">
          <svg
            className="w-5 h-5 text-blue-500 mt-0.5 mr-2"
            fill="currentColor"
            viewBox="0 0 20 20"
          >
            <path
              fillRule="evenodd"
              d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
              clipRule="evenodd"
            />
          </svg>
          <div className="text-sm text-blue-800">
            <p className="font-semibold mb-1">Optimal Resolutions</p>
            <p>The model works best with images between 512px and 4096px. Selected aspect ratios are optimized for best quality.</p>
          </div>
        </div>
      </div>

      {/* Crop Area */}
      <div className="mb-6 bg-gray-100 p-4 rounded-lg">
        <ReactCrop
          crop={crop}
          onChange={(c) => setCrop(c)}
          onComplete={(c) => setCompletedCrop(c)}
          aspect={ASPECT_RATIOS[selectedRatio].value}
        >
          <img
            ref={imgRef}
            src={image}
            alt="Crop preview"
            className="max-w-full max-h-[600px] mx-auto"
            style={{ maxHeight: '600px' }}
          />
        </ReactCrop>
      </div>

      {/* Crop Info */}
      {completedCrop && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-600">
            <span className="font-semibold">Crop Dimensions:</span>{' '}
            {Math.round(completedCrop.width)}×{Math.round(completedCrop.height)} pixels
            {imgRef.current && (
              <>
                {' '}(Original: {imgRef.current.naturalWidth}×{imgRef.current.naturalHeight})
              </>
            )}
          </p>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end space-x-4">
        <button
          onClick={onSkip}
          className="px-6 py-3 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300 transition-colors"
        >
          Skip Crop
        </button>
        <button
          onClick={handleApplyCrop}
          className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 transition-colors"
        >
          Apply Crop
        </button>
      </div>
    </div>
  )
}
