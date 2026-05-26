import { useState, useEffect } from 'react'
import UploadZone from './components/UploadZone'
import CueList from './components/CueList'
import StatsPanel from './components/StatsPanel'
import { subscribeStatus, subscribeCuesUpdated, subscribeConnection } from './api'
import { FaStop } from "react-icons/fa";


function App() {
  const [status, setStatus] = useState({ status: 'idle', filename: null })
  const [refreshKey, setRefreshKey] = useState(0)
  const [connected, setConnected] = useState(null)

  useEffect(() => subscribeStatus(msg => {
    setStatus({ status: msg.status, filename: msg.filename })
  }), [])

  useEffect(() => subscribeConnection(setConnected), [])

  useEffect(() => subscribeCuesUpdated(() => {
    setRefreshKey(k => k + 1)
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
        <div className="logo-wrapper">
          <img src="/logo.png" alt="Cutie Pi" className="logo" />
          <span className="app-version">v{__APP_VERSION__}</span>
        </div>
        <UploadZone onUpload={handleUpload} />
        <button className={isPlaying ? 'stopButton stopButtonActive' : 'stopButton'} onClick={handleStop} disabled={!isPlaying}>
          <FaStop /> STOP
        </button>
      </div>
      <div className="stats-row">
        <StatsPanel />
      </div>
      <CueList refreshKey={refreshKey} />
      {connected === false && (
        <div className="disconnected-overlay">
          <div className="disconnected-modal">
            <h2>Disconnected</h2>
            <p>Reconnecting…</p>
            <div className="disconnected-spinner" />
          </div>
        </div>
      )}
    </div>
  )
}

export default App