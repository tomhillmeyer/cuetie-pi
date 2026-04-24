import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone'
import CueList from './components/CueList'
import StatsPanel from './components/StatsPanel'
import { getStatus } from './api'

function App() {
  const [status, setStatus] = useState({ status: 'stopped', filename: null })
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    const interval = setInterval(async () => {
      const s = await getStatus()
      setStatus(s)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  const handleUpload = () => {
    setRefreshKey(k => k + 1)
  }

  const handleStop = async () => {
    await fetch('/api/stop', { method: 'POST' })
    setRefreshKey(k => k + 1)
  }

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1 style={styles.title}>🎬 Cuetie Pi</h1>
        {status.status === 'playing' && (
          <span style={styles.nowPlaying}>Now playing: {status.filename}</span>
        )}
      </header>
      <StatsPanel />
      <UploadZone onUpload={handleUpload} />
      <CueList refreshKey={refreshKey} />
      <button style={styles.stopButton} onClick={handleStop}>
        ⏹ Stop Playback
      </button>
    </div>
  )
}

const styles = {
  container: {
    maxWidth: '600px',
    margin: '0 auto',
    padding: '20px',
    fontFamily: 'system-ui, sans-serif',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
  },
  title: {
    margin: 0,
    fontSize: '24px',
  },
  nowPlaying: {
    fontSize: '14px',
    color: '#666',
  },
  stopButton: {
    display: 'block',
    width: '100%',
    padding: '12px',
    fontSize: '16px',
    cursor: 'pointer',
    background: '#f5f5f5',
    border: '1px solid #ddd',
    borderRadius: '4px',
    marginTop: '20px',
  },
}

export default App