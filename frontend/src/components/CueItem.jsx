import { useState, useEffect } from 'react'
import { Draggable } from '@hello-pangea/dnd'
import { playCue, stopPlayback, deleteCue, getStatus } from '../api'

function CueItem({ cue, index, onUpdate }) {
  const [playing, setPlaying] = useState(false)
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
            <span style={styles.processing}>Processing...</span>
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