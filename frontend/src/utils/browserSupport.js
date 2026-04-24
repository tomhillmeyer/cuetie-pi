export function isWebCodecsSupported() {
  return 'VideoEncoder' in window && 'VideoDecoder' in window
}

export function getBrowserName() {
  const ua = navigator.userAgent
  if (ua.includes('Edg/')) return 'Edge'
  if (ua.includes('Chrome')) return 'Chrome'
  return 'Other'
}