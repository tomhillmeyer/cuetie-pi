const BASE = '/api'

export async function getCues() {
  const res = await fetch(`${BASE}/cues`)
  return res.json()
}

export function uploadMedia(file, onProgress, transcoded = false) {
  const xhr = new XMLHttpRequest()
  xhr.open('POST', '/api/upload')

  xhr.upload.onprogress = (e) => {
    if (e.lengthComputable && onProgress) {
      const percent = Math.round((e.loaded / e.total) * 100)
      onProgress({ loaded: e.loaded, total: e.total, percent })
    }
  }

  const promise = new Promise((resolve, reject) => {
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        reject(new Error('Upload failed'))
      }
    }
    xhr.onerror = () => reject(new Error('Upload failed'))
    xhr.onabort = () => reject(new Error('Upload cancelled'))
    const formData = new FormData()
    formData.append('file', file)
    formData.append('transcoded', transcoded)
    xhr.send(formData)
  })

  return { promise, abort: () => xhr.abort() }
}

export async function reorderCues(cueIds) {
  const res = await fetch(`${BASE}/cues/reorder`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cueIds }),
  })
  return res.json()
}

export async function deleteCue(cueId) {
  const res = await fetch(`${BASE}/cues/${cueId}`, { method: 'DELETE' })
  return res.json()
}

export async function toggleLoop(cueId) {
  const res = await fetch(`${BASE}/cues/${cueId}/loop`, { method: 'POST' })
  return res.json()
}

export async function playCue(cueId) {
  const res = await fetch(`${BASE}/cues/${cueId}/play`, { method: 'POST' })
  return res.json()
}

export async function stopPlayback() {
  const res = await fetch(`${BASE}/stop`, { method: 'POST' })
  return res.json()
}

export async function getStatus() {
  const res = await fetch(`${BASE}/status`)
  return res.json()
}

export async function getStats() {
  const res = await fetch(`${BASE}/stats`)
  return res.json()
}

export async function getDebug() {
  const res = await fetch(`${BASE}/debug`)
  return res.json()
}

export async function getServerInfo() {
  const res = await fetch(`${BASE}/info`)
  return res.json()
}

export async function setName(name) {
  const res = await fetch(`${BASE}/name`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  return res.json()
}

let ws = null
const statusListeners = new Set()
const statsListeners = new Set()
const cuesUpdatedListeners = new Set()
const connectionListeners = new Set()
let _connected = null
let reconnectTimer = null
let heartbeatTimer = null
let lastMsgTime = 0
let disconnectPending = null

function notifyConnection(connected) {
  _connected = connected
  connectionListeners.forEach(f => f(connected))
}

function startHeartbeat() {
  clearInterval(heartbeatTimer)
  lastMsgTime = Date.now()
  heartbeatTimer = setInterval(() => {
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      clearInterval(heartbeatTimer)
      return
    }
    if (Date.now() - lastMsgTime > 6000) {
      if (!disconnectPending) {
        disconnectPending = setTimeout(() => {
          disconnectPending = null
          notifyConnection(false)
          ws.close()
          clearInterval(heartbeatTimer)
        }, 3000)
      }
      return
    }
    try {
      ws.send("ping")
    } catch {
      ws.close()
      clearInterval(heartbeatTimer)
    }
  }, 3000)
}

function connectStatusWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${proto}//${location.host}/ws/status`)
  ws.onopen = () => {
    if (disconnectPending) {
      clearTimeout(disconnectPending)
      disconnectPending = null
    }
    notifyConnection(true)
    startHeartbeat()
  }
  ws.onmessage = e => {
    lastMsgTime = Date.now()
    if (disconnectPending) {
      clearTimeout(disconnectPending)
      disconnectPending = null
    }
    if (e.data === "pong") return
    const msg = JSON.parse(e.data)
    if (msg.type === 'stats') {
      statsListeners.forEach(f => f(msg))
    } else if (msg.type === 'status') {
      statusListeners.forEach(f => f(msg))
    } else if (msg.type === 'cues_updated') {
      cuesUpdatedListeners.forEach(f => f())
    }
  }
  ws.onerror = () => notifyConnection(false)
  ws.onclose = () => {
    notifyConnection(false)
    ws = null
    clearTimeout(reconnectTimer)
    clearInterval(heartbeatTimer)
    reconnectTimer = setTimeout(connectStatusWS, 1000)
  }
}

function ensureConnected() {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    ws?.close()
    connectStatusWS()
  }
}

function maybeDisconnect() {
  if (statusListeners.size === 0 && statsListeners.size === 0 && cuesUpdatedListeners.size === 0 && connectionListeners.size === 0) {
    ws?.close()
    ws = null
    clearTimeout(reconnectTimer)
  }
}

export function subscribeStatus(fn) {
  statusListeners.add(fn)
  ensureConnected()
  return () => {
    statusListeners.delete(fn)
    maybeDisconnect()
  }
}

export function subscribeStats(fn) {
  statsListeners.add(fn)
  ensureConnected()
  return () => {
    statsListeners.delete(fn)
    maybeDisconnect()
  }
}

export function subscribeCuesUpdated(fn) {
  cuesUpdatedListeners.add(fn)
  ensureConnected()
  return () => {
    cuesUpdatedListeners.delete(fn)
    maybeDisconnect()
  }
}

export function subscribeConnection(fn) {
  fn(_connected)
  connectionListeners.add(fn)
  ensureConnected()
  return () => {
    connectionListeners.delete(fn)
    maybeDisconnect()
  }
}