import { useState, useEffect } from 'react'
import ImageCrop from './ImageCrop'
import { listInputFolderImages } from '../utils/api'

export default function ImageUpload({ onImagesReady, maxImages = 2 }) {
  const [selectedFiles, setSelectedFiles] = useState([])
  const [previewUrls, setPreviewUrls] = useState([])
  const [croppingIndex, setCroppingIndex] = useState(null) // Track which image is being cropped
  const [imageDimensions, setImageDimensions] = useState([]) // Store dimensions for validation
  const [inputFolderImages, setInputFolderImages] = useState([])
  const [showInputFolder, setShowInputFolder] = useState(false)
  const [loadingInputFolder, setLoadingInputFolder] = useState(false)

  // Load input folder images on mount
  useEffect(() => {
    loadInputFolderImages()
  }, [])

  const loadInputFolderImages = async () => {
    try {
      setLoadingInputFolder(true)
      const response = await listInputFolderImages()
      setInputFolderImages(response.data.images || [])
    } catch (err) {
      console.error('Failed to load input folder:', err)
      setInputFolderImages([])
    } finally {
      setLoadingInputFolder(false)
    }
  }

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
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          Upload Images
        </h2>
        {selectedFiles.length > 0 && (
          <span className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm font-medium">
            {selectedFiles.length} / {maxImages} Selected
          </span>
        )}
      </div>

      <div className="space-y-6">
        {/* Input Folder Button */}
        {inputFolderImages.length > 0 && selectedFiles.length < maxImages && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                </svg>
                <div>
                  <p className="text-sm font-semibold text-blue-800">
                    {inputFolderImages.length} images found in ~/input
                  </p>
                  <p className="text-xs text-blue-600">
                    Drop images in ~/input folder for quick access
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowInputFolder(!showInputFolder)}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors"
              >
                {showInputFolder ? 'Hide' : 'Browse'} Folder
              </button>
            </div>

            {/* Input Folder Grid */}
            {showInputFolder && (
              <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3 max-h-96 overflow-y-auto">
                {inputFolderImages.map((img, index) => (
                  <div
                    key={index}
                    className="relative border-2 border-gray-200 rounded-lg p-2 hover:border-blue-500 cursor-pointer transition-all bg-white"
                    onClick={async () => {
                      if (selectedFiles.length >= maxImages) return

                      try {
                        // Fetch the image from backend API
                        const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:6001'
                        const response = await fetch(`${apiUrl}/api/input-folder/image/${img.filename}`)
                        if (!response.ok) throw new Error('Failed to fetch image')

                        const blob = await response.blob()
                        const ext = img.filename.split('.').pop().toLowerCase()
                        const mimeType = ext === 'png' ? 'image/png' :
                                        ext === 'webp' ? 'image/webp' :
                                        ext === 'bmp' ? 'image/bmp' : 'image/jpeg'
                        const file = new File([blob], img.filename, { type: mimeType })

                        const url = URL.createObjectURL(file)
                        const dimensions = await getImageDimensions(url)

                        setSelectedFiles(prev => [...prev, file])
                        setPreviewUrls(prev => [...prev, url])
                        setImageDimensions(prev => [...prev, dimensions])
                      } catch (err) {
                        console.error('Failed to load image from folder:', err)
                        alert('Failed to load image from ~/input folder. Check console for details.')
                      }
                    }}
                  >
                    <div className="aspect-square bg-gray-100 rounded overflow-hidden mb-2 relative">
                      <img
                        src={`${import.meta.env.VITE_API_URL || 'http://localhost:6001'}/api/input-folder/image/${img.filename}`}
                        alt={img.filename}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-10 transition-all flex items-center justify-center">
                        <div className="opacity-0 group-hover:opacity-100 transition-opacity bg-blue-600 text-white px-2 py-1 rounded text-xs font-semibold">
                          Click to add
                        </div>
                      </div>
                    </div>
                    <div className="text-xs text-gray-700 truncate" title={img.filename}>
                      {img.filename}
                    </div>
                    {img.width && img.height && (
                      <div className="text-xs text-gray-500">
                        {img.width}×{img.height}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

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
                  {maxImages === 1 ? 'One image' : `Up to ${maxImages} images`} • PNG, JPG, JPEG • WEBP
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Qwen models: 1-2 images • Seedream: 1-10 images
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
                    <p className="mb-1">Single image selected. All models support single image editing.</p>
                    <p className="text-xs opacity-80">💡 Tip: Click the crop button to optimize image size and aspect ratio.</p>
                  </>
                ) : selectedFiles.length === 2 ? (
                  <>
                    <p className="mb-1">Two images selected.</p>
                    <p className="text-xs opacity-80">• Qwen models: Combines side-by-side before editing</p>
                    <p className="text-xs opacity-80">• Seedream: Uses both as reference inputs</p>
                  </>
                ) : (
                  <>
                    <p className="mb-1">{selectedFiles.length} images selected.</p>
                    <p className="text-xs opacity-80">• Qwen models only support 1-2 images (will use first 2)</p>
                    <p className="text-xs opacity-80">• Seedream can use all {selectedFiles.length} as reference inputs</p>
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
            className="px-6 py-3 bg-gradient-to-r from-purple-600 to-blue-600 text-white rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 disabled:from-gray-300 disabled:to-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center gap-2"
          >
            Next: Configure Edit
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
