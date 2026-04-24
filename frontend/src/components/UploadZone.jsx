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
  const [progress, setProgress] = useState(null)
  const inputRef = useRef(null)

  const handleFiles = async (files) => {
    const valid = [...files].filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return ALLOWED.includes(ext)
    })
    if (valid.length === 0) return

    setUploading(true)
    setProgress(null)
    try {
      for (const file of valid) {
        await uploadMedia(file, (p) => setProgress(p))
      }
      onUpload?.()
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      setProgress(null)
    }
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
      onClick={handleClick}
      style={styles.zone}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ALLOWED.join(',')}
        onChange={handleChange}
        style={styles.input}
      />
      {uploading ? (
        <div style={styles.progressContainer}>
          <div style={styles.progressText}>
            {progress
              ? `${formatBytes(progress.loaded)} of ${formatBytes(progress.total)} uploaded`
              : 'Uploading...'}
          </div>
          <div style={styles.progressBar}>
            <div
              style={{
                ...styles.progressFill,
                width: progress ? `${progress.percent}%` : '0%',
              }}
            />
          </div>
        </div>
      ) : (
        'Drop files here / Browse'
      )}
    </div>
  )
}

const styles = {
  zone: {
    border: '2px dashed #ccc',
    borderRadius: '8px',
    padding: '40px 20px',
    textAlign: 'center',
    cursor: 'pointer',
    background: '#fafafa',
    transition: 'border-color 0.2s',
  },
  input: {
    display: 'none',
  },
  progressContainer: {
    width: '100%',
  },
  progressText: {
    fontSize: '14px',
    color: '#666',
    marginBottom: '8px',
  },
  progressBar: {
    width: '100%',
    height: '8px',
    background: '#e0e0e0',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: '#4CAF50',
    borderRadius: '4px',
    transition: 'width 0.2s',
  },
}

export default UploadZone