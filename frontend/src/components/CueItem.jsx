import { useState, useEffect } from 'react'
import { Draggable } from '@hello-pangea/dnd'
import { playCue, stopPlayback, deleteCue, getStatus, getTranscodeStatus } from '../api'

function CueItem({ cue, index, onUpdate }) {
  const [playing, setPlaying] = useState(false)
  const [transcodeProgress, setTranscodeProgress] = useState(null)
  const isProcessing = cue.status === 'processing'
  const isError = cue.status === 'error'

  useEffect(() => {
    const check = async () => {
      const status = await getStatus()
      setPlaying(status.cueId === cue.id)
    }
    check()
    const interval = setInterval(check, 2000)
    return () => clearInterval(interval)
  }, [cue.id])

  useEffect(() => {
    if (!isProcessing) {
      setTranscodeProgress(null)
      return
    }

    const checkProgress = async () => {
      try {
        const progress = await getTranscodeStatus(cue.id)
        setTranscodeProgress(progress)
      } catch (e) {
        console.error('Failed to get transcode status:', e)
      }
    }

    checkProgress()
    const interval = setInterval(checkProgress, 1000)
    return () => clearInterval(interval)
  }, [cue.id, isProcessing])

  const handlePlay = async () => {
    if (playing) {
      await stopPlayback()
    } else {
      await playCue(cue.id)
    }
  }

  const handleDelete = async () => {
    await deleteCue(cue.id)
    onUpdate?.()
  }

  return (
    <Draggable draggableId={cue.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          style={{
            ...styles.item,
            ...provided.draggableProps.style,
            background: playing ? '#e6f7ff' : isError ? '#ffebee' : '#fff',
            boxShadow: snapshot.isDragging ? '0 2px 8px rgba(0,0,0,0.15)' : '0 1px 3px rgba(0,0,0,0.1)',
          }}
        >
          <span style={styles.handle}>☰</span>
          <span style={styles.number}>{index + 1}.</span>
          <span style={styles.label} title={cue.label}>{cue.label}</span>
          {isProcessing && (
            <span style={styles.progressContainer}>
              <span style={styles.progressBar}>
                <span style={{ ...styles.progressFill, width: `${transcodeProgress?.progress || 0}%` }} />
              </span>
              <span style={styles.progressText}>
                {transcodeProgress?.progress || 0}% • {transcodeProgress?.time || '00:00:00'} • ~{transcodeProgress?.eta || '...'} left
              </span>
            </span>
          )}
          {isError && (
            <span style={styles.error} title={cue.error_message}>Error</span>
          )}
          <button 
            style={playing ? styles.stopBtn : isProcessing || isError ? styles.disabledBtn : styles.playBtn} 
            onClick={handlePlay} 
            title={playing ? 'Stop' : isProcessing ? 'Processing' : isError ? 'Error' : 'Play'}
            disabled={isProcessing || isError}
          >
            {playing ? '⏹' : '▶'}
          </button>
          <button style={styles.deleteBtn} onClick={handleDelete} title="Delete">
            🗑
          </button>
        </div>
      )}
    </Draggable>
  )
}

const styles = {
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 12px',
    border: '1px solid #e0e0e0',
    borderRadius: '4px',
    background: '#fff',
  },
  handle: {
    cursor: 'grab',
    color: '#999',
  },
  number: {
    width: '24px',
    color: '#666',
  },
  label: {
    flex: 1,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  playBtn: {
    padding: '4px 10px',
    fontSize: '14px',
    cursor: 'pointer',
    background: '#f0f0f0',
    border: '1px solid #ddd',
    borderRadius: '4px',
  },
  stopBtn: {
    padding: '4px 10px',
    fontSize: '14px',
    cursor: 'pointer',
    background: '#ffebee',
    border: '1px solid #ef5350',
    borderRadius: '4px',
    color: '#c62828',
  },
  disabledBtn: {
    padding: '4px 10px',
    fontSize: '14px',
    cursor: 'not-allowed',
    background: '#e0e0e0',
    border: '1px solid #ccc',
    borderRadius: '4px',
    color: '#999',
  },
  progressContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    minWidth: '200px',
  },
  progressBar: {
    width: '80px',
    height: '8px',
    background: '#e0e0e0',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: '#1976d2',
    transition: 'width 0.3s ease',
  },
  progressText: {
    fontSize: '11px',
    color: '#1976d2',
    whiteSpace: 'nowrap',
  },
  processing: {
    fontSize: '12px',
    color: '#1976d2',
    fontWeight: 'bold',
  },
  error: {
    fontSize: '12px',
    color: '#d32f2f',
    fontWeight: 'bold',
  },
  deleteBtn: {
    padding: '4px 8px',
    fontSize: '14px',
    cursor: 'pointer',
    background: '#f0f0f0',
    border: '1px solid #ddd',
    borderRadius: '4px',
  },
}

export default CueItem