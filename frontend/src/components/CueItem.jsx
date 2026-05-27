import { useState, useEffect } from 'react'
import { Draggable } from '@hello-pangea/dnd'
import { playCue, stopPlayback, deleteCue, toggleLoop, subscribeStatus } from '../api'
import { MdDelete } from "react-icons/md";
import { FaPlay, FaStop } from "react-icons/fa";
import { FaDeleteLeft, FaRepeat } from "react-icons/fa6";
import { RxDragHandleDots2 } from "react-icons/rx";


function CueItem({ cue, index, onUpdate, onToggleLoop, selected, onSelect }) {
  const [playing, setPlaying] = useState(false)
  const isProcessing = cue.status === 'processing'
  const isError = cue.status === 'error'

  useEffect(() => subscribeStatus(status => {
    setPlaying(status.cueId === cue.id)
  }), [cue.id])

  const handlePlay = async () => {
    if (playing) {
      await stopPlayback()
    } else {
      await playCue(cue.id)
    }
  }

  const handleDelete = async () => {
    if (!window.confirm(`Delete "${cue.label}"?`)) return
    await deleteCue(cue.id)
    onUpdate?.()
  }

  const handleToggleLoop = async () => {
    const res = await toggleLoop(cue.id)
    onToggleLoop?.(cue.id, res.loop)
  }

  const getItemClass = () => {
    let className = 'cueItem'
    if (playing) className += ' cueItemPlaying'
    else if (isError) className += ' cueItemError'
    if (selected) className += ' cueItemSelected'
    return className
  }

  const handleClick = (e) => {
    if (e.target.closest('button')) return
    onSelect?.(cue.id)
  }

  return (
    <Draggable draggableId={cue.id} index={index}>
      {(provided, snapshot) => (
        <div
          ref={provided.innerRef}
          {...provided.draggableProps}
          className={getItemClass()}
          style={provided.draggableProps.style}
          onClick={handleClick}
          data-cue-item={cue.id}
        >
          <span className="cueHandle" {...provided.dragHandleProps}><RxDragHandleDots2 /></span>
          <span className="cueNumber">{index + 1}</span>
          <span className="cueLabel" title={cue.label}>{cue.label}</span>
          {cue.type === 'video' && (
            <button
              className={cue.loop ? 'loopBtn active' : 'loopBtn'}
              onClick={handleToggleLoop}
              title={cue.loop ? 'Looping' : 'Loop'}
            >
              <FaRepeat size={18} />
            </button>
          )}
          <button
            className={playing ? 'stopBtn' : 'playBtn'}
            onClick={handlePlay}
            title={playing ? 'Stop' : 'Play'}
          >
            {playing ? <FaStop size={18} /> : <FaPlay size={18} />}
          </button>
          <button className="deleteBtn" onClick={handleDelete} title="Delete">
            <MdDelete size={18} />
          </button>
        </div>
      )}
    </Draggable>
  )
}

export default CueItem