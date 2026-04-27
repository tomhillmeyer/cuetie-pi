import { useState, useEffect } from 'react'
import { getStats, getDebug } from '../api'

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
  const [debug, setDebug] = useState(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const s = await getStats()
        setStats(s)
      } catch (err) {
        console.error('Failed to fetch stats:', err)
      }
    }

    const fetchDebug = async () => {
      try {
        const d = await getDebug()
        setDebug(d)
      } catch (err) {
        console.error('Failed to fetch debug:', err)
      }
    }

    fetchStats()
    fetchDebug()
    const interval = setInterval(() => {
      fetchStats()
      fetchDebug()
    }, 500)
    return () => clearInterval(interval)
  }, [])

  const vp = stats?.['video-params'] || {}
  const ap = stats?.['audio-params'] || {}
  const isIdle = !stats || stats.status === 'idle'

  return (
    <div className="statsContainer">
      <div className="statsTitle">Stats</div>
      {isIdle ? (
        <div className="statsNoMedia">No media playing</div>
      ) : (
        <div className="statsGrid">
          <div className="statsStat">
            <span className="statsLabel">Position</span>
            <span className="statsValue">
              {formatTime(stats['playback-time'])} / {formatTime(stats.duration)}
            </span>
          </div>
        <div className="statsStat">
          <span className="statsLabel">Progress</span>
          <span className="statsValue">{Math.round(stats['percent-pos'] || 0)}%</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Resolution</span>
          <span className="statsValue">{vp.w || '?'} x {vp.h || '?'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Render FPS</span>
          <span className="statsValue">{stats.fps ? `${stats.fps.toFixed(1)} fps` : '--'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Dropped</span>
          <span className={`statsValue ${(stats['dropped-frames'] || 0) > 10 ? 'statsValueWarning' : ''}`}>
            {stats['dropped-frames'] !== null ? stats['dropped-frames'] : '--'}
            {(stats['dropped-frames'] || 0) > 10 && ' ⚠️'}
          </span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Decoder</span>
          <span className="statsValue">{stats.decoder || stats.hwdec || '--'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Video Codec</span>
          <span className="statsValue">{stats['video-codec'] || '--'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Audio Codec</span>
          <span className="statsValue">{stats['audio-codec'] || '--'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">Sample Rate</span>
          <span className="statsValue">{ap['samplerate'] ? `${ap.samplerate} Hz` : '--'}</span>
        </div>
        <div className="statsStat">
          <span className="statsLabel">File</span>
          <span className="statsValue" title={stats.filename}>
            {stats.filename ? stats.filename.split('/').pop() : '--'}
          </span>
        </div>
        </div>
      )}
      
      {debug && (
        <div className="debugPanel">
          <div className="debugTitle">Loadfile Result</div>
          <pre className="debugOutput">
            {JSON.stringify({
              last_black_path: debug.last_black_path,
              last_black_exists: debug.last_black_exists,
              last_loadfile_result: debug.last_loadfile_result,
              current_mpv_filename: debug.current_mpv_filename
            }, null, 2)}
          </pre>
        </div>
      )}
      
      {debug && (
        <div className="debugPanel">
          <div className="debugTitle">Startup Logs</div>
          <pre className="debugOutput">
            {debug.startup_logs || 'No startup logs captured'}
          </pre>
        </div>
      )}
      
      {debug && (
        <div className="debugPanel">
          <div className="debugTitle">Debug Info</div>
          <pre className="debugOutput">
            {JSON.stringify(debug.test_properties || {}, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}

export default StatsPanel