import { useState, useEffect } from 'react'
import { getStats } from '../api'

function formatTime(totalSeconds) {
  if (totalSeconds === null || totalSeconds === undefined || isNaN(totalSeconds)) return '--:--'
  const hours = Math.floor(totalSeconds / 3600)
  const mins = Math.floor((totalSeconds % 3600) / 60)
  const secs = Math.floor(totalSeconds % 60)
  if (hours > 0) {
    return `${hours}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function StatsPanel() {
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const s = await getStats()
        setStats(s)
      } catch (err) {
        console.error('Failed to fetch stats:', err)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 500)
    return () => clearInterval(interval)
  }, [])

  const vp = stats?.['video-params'] || {}
  const ap = stats?.['audio-params'] || {}
  const isIdle = !stats || stats.status === 'idle'

  return (
    <div className="statsContainer">
      <div className="statsGrid">
        <div className="statsStat">
          <span className="statsLabel">File</span>
          <span className="statsValue" title={stats?.filename || ''}>
            {isIdle ? '--' : (stats.filename ? stats.filename.split('/').pop() : '--')}
          </span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Position</span>
          <span className="statsValue">
            {isIdle ? '-- / --' : `${formatTime(stats['playback-time'])} / ${formatTime(stats.duration)}`}
          </span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Progress</span>
          <span className="statsValue">{isIdle ? '--' : `${Math.round(stats['percent-pos'] || 0)}%`}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Resolution</span>
          <span className="statsValue">{isIdle ? '-- x --' : `${vp.w || '?'} x ${vp.h || '?'}`}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">FPS</span>
          <span className="statsValue">{isIdle ? '--' : `${stats.fps?.toFixed(1) || '--'} fps`}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Dropped</span>
          <span className={`statsValue ${!isIdle && (stats['dropped-frames'] || 0) > 10 ? 'statsValueWarning' : ''}`}>
            {isIdle ? '--' : `${stats['dropped-frames'] ?? '--'} ${(stats['dropped-frames'] || 0) > 10 ? '⚠️' : ''}`}
          </span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Decoder</span>
          <span className="statsValue">{isIdle ? '--' : (stats.decoder || stats.hwdec || '--')}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Video</span>
          <span className="statsValue">{isIdle ? '--' : (stats['video-codec'] || '--')}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Audio</span>
          <span className="statsValue">{isIdle ? '--' : (stats['audio-codec'] || '--')}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Sample</span>
          <span className="statsValue">{isIdle ? '--' : (ap['samplerate'] ? `${ap.samplerate} Hz` : '--')}</span>
        </div>
      </div>
    </div>
  )
}

export default StatsPanel