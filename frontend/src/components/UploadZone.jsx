import { useState, useRef } from 'react'
import { uploadMedia } from '../api'

const ALLOWED = ['.jpg', '.jpeg', '.png', '.gif', '.mp4', '.mov', '.webm']

function UploadZone({ onUpload }) {
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef(null)

  const handleFiles = async (files) => {
    const valid = [...files].filter(f => {
      const ext = '.' + f.name.split('.').pop().toLowerCase()
      return ALLOWED.includes(ext)
    })
    if (valid.length === 0) return

    setUploading(true)
    try {
      for (const file of valid) {
        await uploadMedia(file)
      }
      onUpload?.()
    } finally {
      setUploading(false)
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
      {uploading ? 'Uploading...' : 'Drop files here / Browse'}
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
}

export default UploadZone