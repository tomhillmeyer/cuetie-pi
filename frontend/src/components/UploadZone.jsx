import { useState, useRef } from 'react'
import { uploadMedia } from '../api'

const ALLOWED = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm']

function formatBytes(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function UploadZone({ onUpload }) {
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(null)
  const [currentFile, setCurrentFile] = useState(null)
  const [cancelled, setCancelled] = useState(false)
  const abortRef = useRef(null)
  const inputRef = useRef(null)

  const handleFiles = async (files) => {
    const valid = [...files].filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return ALLOWED.includes(ext)
    })
    if (valid.length === 0) return

    setUploading(true)
    setUploadProgress(null)
    setCancelled(false)

    try {
      for (const file of valid) {
        setCurrentFile(file.name)
        setUploadProgress({ type: 'uploading' })
        const { promise, abort } = uploadMedia(file, (p) => {
          setUploadProgress({ type: 'uploading', ...p })
        })
        abortRef.current = abort
        await promise
        abortRef.current = null
        const cuesRes = await fetch('/api/cues')
        const cues = await cuesRes.json()
        const cue = cues[cues.length - 1]
        onUpload?.(cue)
      }
    } catch (err) {
      if (err.message === 'Upload cancelled') {
        setCancelled(true)
      } else {
        console.error('Upload failed:', err)
      }
    } finally {
      setUploading(false)
      setUploadProgress(null)
      setCurrentFile(null)
      abortRef.current = null
    }
  }

  const handleCancel = () => {
    abortRef.current?.()
  }

  const handleDrop = (e) => {
    e.preventDefault()
    handleFiles(e.dataTransfer.files)
  }

  const handleDragOver = (e) => {
    e.preventDefault()
  }

  const handleClick = () => {
    inputRef.current?.click()
  }

  const handleChange = (e) => {
    handleFiles(e.target.files)
  }

  return (
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={uploading ? undefined : handleClick}
        className="uploadZone"
        style={{ cursor: uploading ? 'default' : 'pointer' }}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ALLOWED.join(',')}
          onChange={handleChange}
          className="uploadZoneInput"
        />
        {uploading ? (
          <div className="uploadProgressRow">
            <div className="uploadProgressLeft">
              <span className="progressFilename">
                {cancelled ? 'Cancelled' : currentFile}
              </span>
              <div className="progressBar">
                <div
                  className="progressFill"
                  style={{ width: `${cancelled ? 0 : uploadProgress?.percent || 0}%` }}
                />
              </div>
            </div>
            {!cancelled && (
              <button className="cancelBtn" onClick={handleCancel}>
                Cancel
              </button>
            )}
          </div>
        ) : (
          <><span className="desktop-only">Drop files here / </span>Browse</>
        )}
      </div>
  )
}

export default UploadZone
