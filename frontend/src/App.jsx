import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone'
import CueList from './components/CueList'
import StatsPanel from './components/StatsPanel'
import { getStatus } from './api'

function App() {
  const [status, setStatus] = useState({ status: 'idle', filename: null })
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
    <div className="container">
      <div className="left-column">
        <header className="header">
          <img src="/logo.png" alt="Cutie Pi" className="logo" />
          {status.status === 'playing' && (
            <span className="nowPlaying">Now playing: {status.filename}</span>
          )}
        </header>
        <CueList refreshKey={refreshKey} />
      </div>
      <div className="right-column">
        <UploadZone onUpload={handleUpload} />
        <StatsPanel />
        <button className="stopButton" onClick={handleStop}>
          ⏹ Stop Playback
        </button>
      </div>
    </div>
  )
}

export default App