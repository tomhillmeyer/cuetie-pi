import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone'
import CueList from './components/CueList'
import StatsPanel from './components/StatsPanel'
import { subscribeStatus } from './api'
import { FaStop } from "react-icons/fa";


function App() {
  const [status, setStatus] = useState({ status: 'idle', filename: null })
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => subscribeStatus(msg => {
    setStatus({ status: msg.status, filename: msg.filename })
  }), [])

  useEffect(() => {
    const handleKey = (e) => {
      if (e.key === 'Escape' && !e.target.closest('input, textarea')) {
        fetch('/api/stop', { method: 'POST' })
        setRefreshKey(k => k + 1)
      }
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [])

  const handleUpload = () => {
    setRefreshKey(k => k + 1)
  }

  const handleStop = async () => {
    await fetch('/api/stop', { method: 'POST' })
    setRefreshKey(k => k + 1)
  }

  const isPlaying = status.status === 'playing'

  return (
    <div className="container">
      <div className="header-row">
        <img src="/logo.png" alt="Cutie Pi" className="logo" />
        <UploadZone onUpload={handleUpload} />
        <button className={isPlaying ? 'stopButton stopButtonActive' : 'stopButton'} onClick={handleStop} disabled={!isPlaying}>
          <FaStop /> STOP
        </button>
      </div>
      <div className="stats-row">
        <StatsPanel />
      </div>
      <CueList refreshKey={refreshKey} />
    </div>
  )
}

export default App