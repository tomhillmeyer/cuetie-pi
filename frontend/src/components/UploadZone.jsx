import { useState, useRef } from 'react'
import { uploadMedia } from '../api'
import { useTranscode } from '../hooks/useTranscode'
import { isWebCodecsSupported } from '../utils/browserSupport'

const ALLOWED = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm']
const VIDEO_EXTENSIONS = ['.mp4', '.mov', '.webm']

function isVideo(filename) {
  const ext = '.' + filename.split('.').pop().toLowerCase()
  return VIDEO_EXTENSIONS.includes(ext)
}

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
  const [transcodeEnabled, setTranscodeEnabled] = useState(false)
  const [currentFile, setCurrentFile] = useState(null)
  const inputRef = useRef(null)
  const supported = isWebCodecsSupported()
  const { transcode, abort, progress, status, message } = useTranscode()

  const handleFiles = async (files) => {
    const valid = [...files].filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return ALLOWED.includes(ext)
    })
    if (valid.length === 0) return

    setUploading(true)
    setUploadProgress(null)

    try {
      for (const file of valid) {
        setCurrentFile(file.name)

        if (isVideo(file.name) && transcodeEnabled && status !== 'unsupported') {
          setUploadProgress({ type: 'transcoding' })

          const transcoded = await transcode(file)
          if (!transcoded) {
            setUploading(false)
            setUploadProgress(null)
            setCurrentFile(null)
            continue
          }

          setUploadProgress({ type: 'uploading' })
          const cue = await uploadMedia(transcoded, (p) => {
            setUploadProgress({ type: 'uploading', ...p })
          }, true)
          onUpload?.({ ...cue, transcoded: true })
        } else {
          setUploadProgress({ type: 'uploading' })
          await uploadMedia(file, (p) => {
            setUploadProgress({ type: 'uploading', ...p })
          }, false)
          const cuesRes = await fetch('/api/cues')
          const cues = await cuesRes.json()
          const cue = cues[cues.length - 1]
          onUpload?.({ ...cue, transcoded: false })
        }
      }
    } catch (err) {
      console.error('Upload failed:', err)
    } finally {
      setUploading(false)
      setUploadProgress(null)
      setCurrentFile(null)
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

  const handleTranscodeToggle = (e) => {
    setTranscodeEnabled(e.target.checked)
  }

  return (
    <div>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onClick={uploading ? undefined : handleClick}
        style={{
          ...styles.zone,
          cursor: uploading ? 'default' : 'pointer',
        }}
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
              {uploadProgress?.type === 'transcoding'
                ? message || 'Transcoding...'
                : uploadProgress
                  ? `${formatBytes(uploadProgress.loaded)} of ${formatBytes(uploadProgress.total)} uploaded`
                  : 'Processing...'}
            </div>
            <div style={styles.progressBar}>
              <div
                style={{
                  ...styles.progressFill,
                  width: `${progress}%`,
                  background: uploadProgress?.type === 'transcoding' ? '#1976d2' : '#4CAF50',
                }}
              />
            </div>
            {uploadProgress?.type === 'transcoding' && (
              <div style={styles.progressSubtext}>
                {progress}% complete
                <button onClick={(e) => { e.stopPropagation(); abort() }} style={styles.cancelBtn}>
                  Cancel
                </button>
              </div>
            )}
          </div>
        ) : (
          'Drop files here / Browse'
        )}
      </div>

      <div style={styles.optionsContainer}>
        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={transcodeEnabled}
            onChange={handleTranscodeToggle}
            disabled={!supported}
            style={styles.checkbox}
          />
          Transcode video for optimal playback
        </label>
        {!supported && (
          <div style={styles.unsupportedWarning}>
            Video transcoding requires Chrome or Edge browser
          </div>
        )}
      </div>
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
    borderRadius: '4px',
    transition: 'width 0.2s',
  },
  progressSubtext: {
    marginTop: '8px',
    fontSize: '12px',
    color: '#999',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  cancelBtn: {
    padding: '4px 8px',
    fontSize: '12px',
    background: '#ffebee',
    border: '1px solid #ef5350',
    borderRadius: '4px',
    color: '#c62828',
    cursor: 'pointer',
  },
  optionsContainer: {
    marginTop: '12px',
    padding: '0 4px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#666',
    cursor: 'pointer',
  },
  checkbox: {
    width: '16px',
    height: '16px',
    cursor: 'pointer',
  },
  unsupportedWarning: {
    marginTop: '8px',
    fontSize: '12px',
    color: '#d32f2f',
  },
}

export default UploadZone