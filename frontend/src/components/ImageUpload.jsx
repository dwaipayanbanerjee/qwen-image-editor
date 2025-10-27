import { useState } from 'react'
import ImageCrop from './ImageCrop'

export default function ImageUpload({ onImagesReady, maxImages = 2 }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [previewUrls, setPreviewUrls] = useState([])
  const [croppingIndex, setCroppingIndex] = useState(null) // Track which image is being cropped
  const [imageDimensions, setImageDimensions] = useState([]) // Store dimensions for validation

  const handleFileSelect = async (e) => {
    const files = Array.from(e.target.files)

    // Limit to maxImages
    const filesToProcess = files.slice(0, maxImages - selectedFiles.length)

    if (filesToProcess.length === 0) return

    // Create preview URLs and read dimensions
    const newPreviewUrls = []
    const newDimensions = []

    for (const file of filesToProcess) {
      const url = URL.createObjectURL(file)
      newPreviewUrls.push(url)

      // Read image dimensions
      const dimensions = await getImageDimensions(url)
      newDimensions.push(dimensions)
    }

    setSelectedFiles(prev => [...prev, ...filesToProcess])
    setPreviewUrls(prev => [...prev, ...newPreviewUrls])
    setImageDimensions(prev => [...prev, ...newDimensions])
  }

  const getImageDimensions = (url) => {
    return new Promise((resolve) => {
      const img = new Image()
      img.onload = () => {
        resolve({ width: img.width, height: img.height })
      }
      img.onerror = () => {
        resolve({ width: 0, height: 0 })
      }
      img.src = url
    })
  }

  const isOptimalSize = (dimensions) => {
    if (!dimensions || dimensions.width === 0) return true // Unknown, assume OK
    const maxDim = Math.max(dimensions.width, dimensions.height)
    return maxDim >= 512 && maxDim <= 4096
  }

  const handleRemoveImage = (index) => {
    // Revoke object URL to free memory
    URL.revokeObjectURL(previewUrls[index])

    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
    setPreviewUrls(prev => prev.filter((_, i) => i !== index))
    setImageDimensions(prev => prev.filter((_, i) => i !== index))
  }

  const handleNext = () => {
    if (selectedFiles.length > 0) {
      onImagesReady(selectedFiles)
    }
  }

  const handleCropComplete = async (croppedFile) => {
    // Replace the file at croppingIndex with the cropped version
    const newFiles = [...selectedFiles]
    newFiles[croppingIndex] = croppedFile

    // Update preview URL
    const newPreviewUrls = [...previewUrls]
    URL.revokeObjectURL(newPreviewUrls[croppingIndex]) // Clean up old URL
    const newUrl = URL.createObjectURL(croppedFile)
    newPreviewUrls[croppingIndex] = newUrl

    // Update dimensions
    const newDimensions = [...imageDimensions]
    const dimensions = await getImageDimensions(newUrl)
    newDimensions[croppingIndex] = dimensions

    setSelectedFiles(newFiles)
    setPreviewUrls(newPreviewUrls)
    setImageDimensions(newDimensions)
    setCroppingIndex(null)
  }

  const handleSkipCrop = () => {
    setCroppingIndex(null)
  }

  // Show crop interface if cropping
  if (croppingIndex !== null) {
    return (
      <ImageCrop
        image={previewUrls[croppingIndex]}
        imageName={selectedFiles[croppingIndex].name}
        onCropComplete={handleCropComplete}
        onSkip={handleSkipCrop}
      />
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8">
      <h2 className="text-2xl font-bold text-gray-800 mb-6">
        Upload Images
      </h2>

      <div className="space-y-6">
        {/* Upload Area */}
        {selectedFiles.length < maxImages && (
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center hover:border-purple-500 transition-colors">
            <input
              type="file"
              id="image-upload"
              className="hidden"
              accept="image/*"
              multiple={maxImages > 1}
              onChange={handleFileSelect}
            />
            <label
              htmlFor="image-upload"
              className="cursor-pointer"
            >
              <div className="space-y-2">
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <div className="text-gray-600">
                  <span className="text-purple-600 font-semibold">Click to upload</span>
                  {' or drag and drop'}
                </div>
                <p className="text-xs text-gray-500">
                  {maxImages === 1 ? 'One image' : `Up to ${maxImages} images`} • PNG, JPG, JPEG
                </p>
              </div>
            </label>
          </div>
        )}

        {/* Preview Grid */}
        {previewUrls.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {previewUrls.map((url, index) => (
              <div key={index} className="relative group">
                <img
                  src={url}
                  alt={`Preview ${index + 1}`}
                  className="w-full h-64 object-cover rounded-lg border-2 border-gray-200"
                />

                {/* Top right buttons */}
                <div className="absolute top-2 right-2 flex space-x-2">
                  <button
                    onClick={() => setCroppingIndex(index)}
                    className="bg-blue-500 text-white rounded-full p-2 hover:bg-blue-600 transition-colors shadow-lg"
                    title="Crop image"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M14 10l-2 2m0 0l-2-2m2 2V6m0 4l2-2m-2 2l-2 2m6 4h4m-4 0a2 2 0 01-2-2m2 2a2 2 0 002 2m-2-2v-4m0 4v4m-6-4a2 2 0 01-2-2m2 2a2 2 0 002 2m-2-2v-4m0 4v4"
                      />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleRemoveImage(index)}
                    className="bg-red-500 text-white rounded-full p-2 hover:bg-red-600 transition-colors shadow-lg"
                    title="Remove image"
                  >
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>

                {/* Bottom left label with dimensions */}
                <div className="absolute bottom-2 left-2 space-y-1">
                  <div className="bg-black bg-opacity-60 text-white px-2 py-1 rounded text-sm">
                    Image {index + 1}
                  </div>
                  {imageDimensions[index] && (
                    <div className={`px-2 py-1 rounded text-xs font-medium ${
                      isOptimalSize(imageDimensions[index])
                        ? 'bg-green-500 bg-opacity-80 text-white'
                        : 'bg-yellow-500 bg-opacity-80 text-black'
                    }`}>
                      {imageDimensions[index].width} × {imageDimensions[index].height}
                      {!isOptimalSize(imageDimensions[index]) && ' ⚠️'}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Size Warning */}
        {selectedFiles.length > 0 && imageDimensions.some(dim => !isOptimalSize(dim)) && (
          <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-4">
            <div className="flex items-start">
              <svg
                className="w-5 h-5 text-yellow-600 mt-0.5 mr-2"
                fill="currentColor"
                viewBox="0 0 20 20"
              >
                <path
                  fillRule="evenodd"
                  d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                  clipRule="evenodd"
                />
              </svg>
              <div className="text-sm text-yellow-800">
                <p className="font-semibold mb-1">Image size outside optimal range</p>
                <p>For best results, use images between 512px and 4096px. Consider cropping to one of the optimal aspect ratios.</p>
              </div>
            </div>
          </div>
        )}

        {/* Info */}
        {selectedFiles.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
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
                {selectedFiles.length === 1 ? (
                  <>
                    <p className="mb-1">Single image selected. The model will edit this image based on your prompt.</p>
                    <p className="text-xs opacity-80">💡 Tip: Click the crop button to optimize image size and aspect ratio.</p>
                  </>
                ) : (
                  <>
                    <p className="mb-1">Two images selected. The model will combine them side-by-side before applying edits.</p>
                    <p className="text-xs opacity-80">💡 Tip: Crop images individually before combining for best results.</p>
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex justify-end space-x-4">
          <button
            onClick={handleNext}
            disabled={selectedFiles.length === 0}
            className="px-6 py-3 bg-purple-600 text-white rounded-lg font-semibold hover:bg-purple-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            Next: Configure Edit
          </button>
        </div>
      </div>
    </div>
  )
}
