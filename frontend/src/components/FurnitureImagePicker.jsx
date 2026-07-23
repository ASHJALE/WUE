import { useEffect, useRef, useState } from 'react'
import { FaImage, FaRotate, FaTrash } from 'react-icons/fa6'

export const FURNITURE_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp']
export const MAX_FURNITURE_IMAGE_BYTES = 5 * 1024 * 1024

export function validateFurnitureImage(file) {
  if (!FURNITURE_IMAGE_TYPES.includes(file.type)) {
    return 'Unsupported file type. Choose a JPEG, PNG, or WebP image.'
  }
  if (file.size > MAX_FURNITURE_IMAGE_BYTES) {
    return 'Image is larger than 5 MB. Choose a smaller file.'
  }
  return ''
}

export function formatImageSize(bytes) {
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

export default function FurnitureImagePicker({ disabled = false }) {
  const inputRef = useRef(null)
  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState('')
  const [validationMessage, setValidationMessage] = useState('')

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  function openFilePicker() {
    if (inputRef.current) inputRef.current.value = ''
    inputRef.current?.click()
  }

  function handleFileChange(event) {
    const file = event.target.files?.[0]
    if (!file) return

    const message = validateFurnitureImage(file)
    if (message) {
      setValidationMessage(message)
      event.target.value = ''
      return
    }

    setValidationMessage('')
    setSelectedFile(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  function removeImage() {
    setSelectedFile(null)
    setPreviewUrl('')
    setValidationMessage('')
    if (inputRef.current) inputRef.current.value = ''
  }

  return (
    <fieldset className="furniture-image-picker border rounded-3 p-3 p-md-4 mb-4" disabled={disabled}>
      <legend className="h5 float-none w-auto px-2 mb-2">Furniture Image</legend>
      <p className="text-secondary small mb-3" id="furniture-image-help">
        Choose one JPEG, PNG, or WebP image up to 5 MB. The image is previewed locally and is not uploaded yet.
      </p>

      <label className="visually-hidden" htmlFor="furniture-image">Choose a furniture image</label>
      <input
        accept="image/jpeg,image/png,image/webp"
        aria-describedby={`furniture-image-help${validationMessage ? ' furniture-image-error' : ''}`}
        className="visually-hidden"
        id="furniture-image"
        onChange={handleFileChange}
        ref={inputRef}
        type="file"
      />

      {validationMessage && (
        <div className="alert alert-danger py-2" id="furniture-image-error" role="alert">
          {validationMessage}
        </div>
      )}

      {selectedFile && previewUrl ? (
        <div className="row g-3 align-items-center">
          <div className="col-md-5">
            <img
              alt={`Preview of selected furniture file ${selectedFile.name}`}
              className="furniture-image-preview img-fluid rounded-3 border"
              src={previewUrl}
            />
          </div>
          <div className="col-md-7">
            <p className="fw-semibold text-break mb-1">{selectedFile.name}</p>
            <p className="text-secondary small mb-3">{formatImageSize(selectedFile.size)}</p>
            <div className="d-flex flex-column flex-sm-row gap-2">
              <button className="btn btn-outline-success" onClick={openFilePicker} type="button">
                <FaRotate className="me-2" aria-hidden="true" />Change Image
              </button>
              <button className="btn btn-outline-danger" onClick={removeImage} type="button">
                <FaTrash className="me-2" aria-hidden="true" />Remove Image
              </button>
            </div>
          </div>
        </div>
      ) : (
        <div className="furniture-image-empty text-center p-4 rounded-3">
          <FaImage className="text-success mb-3" size="2.25rem" aria-hidden="true" />
          <p className="mb-3">No furniture image selected</p>
          <button className="btn btn-success" onClick={openFilePicker} type="button">Choose Image</button>
        </div>
      )}
    </fieldset>
  )
}
