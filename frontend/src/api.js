const BASE = '/api'

export async function getCues() {
  const res = await fetch(`${BASE}/cues`)
  return res.json()
}

export async function uploadMedia(file, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', '/api/upload')
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100)
        onProgress({ loaded: e.loaded, total: e.total, percent })
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText))
      } else {
        reject(new Error('Upload failed'))
      }
    }
    xhr.onerror = () => reject(new Error('Upload failed'))
    const formData = new FormData()
    formData.append('file', file)
    xhr.send(formData)
  })
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