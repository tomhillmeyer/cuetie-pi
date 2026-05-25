import { useState, useEffect } from 'react'
import { subscribeStats, subscribeStatus } from '../api'

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
  const [status, setStatus] = useState(null)
  const [stats, setStats] = useState(null)

  useEffect(() => {
    const unsubStats = subscribeStats(setStats)
    const unsubStatus = subscribeStatus(setStatus)
    return () => { unsubStats(); unsubStatus() }
  }, [])

   const filename = status?.filename || stats?.filename || null
   const isIdle = !status || status.status === 'idle'
   const isImage = !isIdle && /\.(png|jpe?g|gif)$/i.test(filename || '')

   const vp = stats?.['video-params'] || {}

   return (
     <div className="statsContainer">
       <div className="statsGrid">
         <div className="statsStat">
           <span className="statsLabel">File</span>
           <span className="statsValue">
             {isIdle ? 'Nothing playing' : (filename ? filename.split('/').pop() : '--')}
           </span>
         </div>
         {!isIdle && (
           <div className="statsStat">
             <span className="statsLabel">Resolution</span>
             <span className="statsValue">{`${vp.w || '?'} x ${vp.h || '?'}`}</span>
           </div>
         )}
         {!isIdle && !isImage && (
           <div className="statsStat">
             <span className="statsLabel">FPS</span>
             <span className="statsValue">{`${stats?.fps?.toFixed(1) || '--'} fps`}</span>
           </div>
         )}
         {!isIdle && !isImage && (
           <div className="statsStat">
             <span className="statsLabel">Dropped</span>
             <span className={`statsValue ${(stats?.['dropped-frames'] || 0) > 10 ? 'statsValueWarning' : ''}`}>
               {`${stats?.['dropped-frames'] ?? '--'} ${(stats?.['dropped-frames'] || 0) > 10 ? '⚠️' : ''}`}
             </span>
           </div>
         )}
         {!isIdle && !isImage && (
           <div className="statsStat">
             <span className="statsLabel">Decoder</span>
             <span className="statsValue">{stats?.decoder || stats?.hwdec || '--'}</span>
           </div>
         )}
       </div>
       {!isIdle && !isImage && (
         <div className="progressRow">
           <span className="positionValue">
             {`${formatTime(stats?.['playback-time'])} / ${formatTime(stats?.duration)}`}
           </span>
           <div className="progressBar">
             <div 
               className="progressFill" 
               style={{ width: `${Math.round(stats?.['percent-pos'] || 0)}%` }}
             />
           </div>
         </div>
       )}
     </div>
   )
 }

export default StatsPanel