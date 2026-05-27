import { useState, useEffect, useCallback, useRef } from 'react'
import { DragDropContext, Droppable } from '@hello-pangea/dnd'
import { getCues, reorderCues, playCue } from '../api'
import CueItem from './CueItem'

function CueList({ refreshKey }) {
  const [cues, setCues] = useState([])
  const [selectedCueId, setSelectedCueId] = useState(null)
  const containerRef = useRef(null)

  useEffect(() => {
    getCues().then(setCues)
  }, [refreshKey])

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.target.closest('input, textarea, button')) return
      if (e.key === 'Enter' && selectedCueId) {
        playCue(selectedCueId)
        const idx = cues.findIndex(c => c.id === selectedCueId)
        if (idx !== -1) {
          setSelectedCueId(cues[(idx + 1) % cues.length].id)
        }
        return
      }
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault()
        if (cues.length === 0) return
        if (!selectedCueId) {
          setSelectedCueId(e.key === 'ArrowDown' ? cues[0].id : cues[cues.length - 1].id)
          return
        }
        const idx = cues.findIndex(c => c.id === selectedCueId)
        if (idx === -1) return
        const next = e.key === 'ArrowDown'
          ? (idx + 1) % cues.length
          : (idx - 1 + cues.length) % cues.length
        setSelectedCueId(cues[next].id)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [selectedCueId, cues])

  useEffect(() => {
    const handleDocumentClick = (e) => {
      if (!selectedCueId) return
      if (!e.target.closest('[data-cue-item]')) {
        setSelectedCueId(null)
      }
    }
    document.addEventListener('click', handleDocumentClick)
    return () => document.removeEventListener('click', handleDocumentClick)
  }, [selectedCueId])

  const handleSelect = useCallback((cueId) => setSelectedCueId(cueId), [])

  const handleToggleLoop = (cueId, newLoop) => {
    setCues(prev => prev.map(c => c.id === cueId ? { ...c, loop: newLoop } : c))
  }

  const handleDragEnd = async (result) => {
    if (!result.destination) return
    const newOrder = [...cues.map(c => c.id)]
    const [removed] = newOrder.splice(result.source.index, 1)
    newOrder.splice(result.destination.index, 0, removed)
    setCues(
      cues.map((c, i) => ({ ...c, order: i })).sort((a, b) =>
        newOrder.indexOf(a.id) - newOrder.indexOf(b.id)
      )
    )
    await reorderCues(newOrder)
  }

  return (
    <div className="cueListContainer" ref={containerRef}>
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="cues">
          {(provided) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className="cueList"
            >
              {cues.map((cue, index) => (
                <CueItem key={cue.id} cue={cue} index={index} onUpdate={() => getCues().then(setCues)} onToggleLoop={handleToggleLoop} selected={selectedCueId === cue.id} onSelect={handleSelect} />
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>
    </div>
  )
}

export default CueList