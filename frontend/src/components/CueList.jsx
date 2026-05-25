import { useState, useEffect } from 'react'
import { DragDropContext, Droppable } from '@hello-pangea/dnd'
import { getCues, reorderCues } from '../api'
import CueItem from './CueItem'

function CueList({ refreshKey }) {
  const [cues, setCues] = useState([])

  useEffect(() => {
    getCues().then(setCues)
  }, [refreshKey])

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
    <div className="cueListContainer">
      <h2 className="cueListHeading">CUE LIST</h2>
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="cues">
          {(provided) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              className="cueList"
            >
              {cues.map((cue, index) => (
                <CueItem key={cue.id} cue={cue} index={index} onUpdate={() => getCues().then(setCues)} onToggleLoop={handleToggleLoop} />
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