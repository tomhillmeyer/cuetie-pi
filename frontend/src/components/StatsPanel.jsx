import { useState, useEffect } from 'react'
import { getStats } from '../api'

function formatTime(seconds) {
  if (seconds === null || seconds === undefined || isNaN(seconds)) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
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
    const interval = setInterval(fetchStats, 1000)
    return () => clearInterval(interval)
  }, [])

  if (!stats || stats.status === 'stopped') {
    return (
      <div style={styles.container}>
        <div style={styles.title}>Stats</div>
        <div style={styles.noMedia}>No media playing</div>
      </div>
    )
  }

  const vp = stats['video-params'] || {}
  const ap = stats['audio-params'] || {}

  return (
    <div style={styles.container}>
      <div style={styles.title}>Stats</div>
      <div style={styles.grid}>
        <div style={styles.stat}>
          <span style={styles.label}>Position</span>
          <span style={styles.value}>
            {formatTime(stats['playback-time'])} / {formatTime(stats.duration)}
          </span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Progress</span>
          <span style={styles.value}>{Math.round(stats['percent-pos'] || 0)}%</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Resolution</span>
          <span style={styles.value}>{vp.w || '?'} x {vp.h || '?'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Framerate</span>
          <span style={styles.value}>{stats.fps ? `${stats.fps.toFixed(2)} fps` : '--'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Video Codec</span>
          <span style={styles.value}>{stats['video-codec'] || '--'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Audio Codec</span>
          <span style={styles.value}>{stats['audio-codec'] || '--'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Sample Rate</span>
          <span style={styles.value}>{ap['samplerate'] ? `${ap.samplerate} Hz` : '--'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>File</span>
          <span style={styles.value} title={stats.filename}>
            {stats.filename ? stats.filename.split('/').pop() : '--'}
          </span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Paused</span>
          <span style={styles.value}>{stats.paused ? 'Yes' : 'No'}</span>
        </div>
        <div style={styles.stat}>
          <span style={styles.label}>Pixel Format</span>
          <span style={styles.value}>{vp.pixelformat || '--'}</span>
        </div>
      </div>
    </div>
  )
}

const styles = {
  container: {
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    padding: '12px',
    marginBottom: '16px',
    background: '#fafafa',
  },
  title: {
    fontSize: '14px',
    fontWeight: '600',
    marginBottom: '8px',
    color: '#333',
  },
  noMedia: {
    fontSize: '13px',
    color: '#999',
    fontStyle: 'italic',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '8px',
  },
  stat: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  label: {
    fontSize: '11px',
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  value: {
    fontSize: '13px',
    color: '#333',
    fontFamily: 'monospace',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
}

export default StatsPanel