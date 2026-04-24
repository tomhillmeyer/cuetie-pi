const BASE = '/api'

export async function getCues() {
  const res = await fetch(`${BASE}/cues`)
  return res.json()
}

export async function uploadMedia(file) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error('Upload failed')
  return res.json()
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