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
      <div className="header-row">
        <img src="/logo.png" alt="Cutie Pi" className="logo" />
        <UploadZone onUpload={handleUpload} />
        <button className="stopButton" onClick={handleStop}>
          ⏹ Stop
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