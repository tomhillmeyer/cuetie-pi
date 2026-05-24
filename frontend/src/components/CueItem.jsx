import { useState, useEffect } from 'react'
import { Draggable } from '@hello-pangea/dnd'
import { playCue, stopPlayback, deleteCue, getStatus } from '../api'
import { MdDelete } from "react-icons/md";
import { FaPlay, FaStop } from "react-icons/fa";
import { FaDeleteLeft } from "react-icons/fa6";




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

  const getItemClass = () => {
    let className = 'cueItem'
    if (playing) className += ' cueItemPlaying'
    else if (isError) className += ' cueItemError'
    return className
  }

  return (
    <Draggable draggableId={cue.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={getItemClass()}
          style={provided.draggableProps.style}
        >
          <span className="cueHandle">☰</span>
          <span className="cueNumber">{index + 1}.</span>
          <span className="cueLabel" title={cue.label}>{cue.label}</span>
          <button
            className={playing ? 'stopBtn' : 'playBtn'}
            onClick={handlePlay}
            title={playing ? 'Stop' : 'Play'}
          >
            {playing ? <FaStop /> : <FaPlay />}
          </button>
          <button className="deleteBtn" onClick={handleDelete} title="Delete">
            <FaDeleteLeft />
          </button>
        </div>
      )}
    </Draggable>
  )
}

export default CueItem