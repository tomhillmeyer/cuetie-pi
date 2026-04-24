import { useState, useEffect } from 'react'
import { DragDropContext, Droppable } from '@hello-pangea/dnd'
import { getCues, reorderCues } from '../api'
import CueItem from './CueItem'

function CueList({ refreshKey }) {
  const [cues, setCues] = useState([])

  useEffect(() => {
    getCues().then(setCues)
  }, [refreshKey])

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
    <div style={styles.container}>
      <h2 style={styles.heading}>Cue List</h2>
      <DragDropContext onDragEnd={handleDragEnd}>
        <Droppable droppableId="cues">
          {(provided) => (
            <div
              {...provided.droppableProps}
              ref={provided.innerRef}
              style={styles.list}
            >
              {cues.map((cue, index) => (
                <CueItem key={cue.id} cue={cue} index={index} onUpdate={() => getCues().then(setCues)} />
              ))}
              {provided.placeholder}
            </div>
          )}
        </Droppable>
      </DragDropContext>
    </div>
  )
}

const styles = {
  container: {
    marginTop: '20px',
  },
  heading: {
    fontSize: '16px',
    marginBottom: '12px',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
}

export default CueList