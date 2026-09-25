const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text || `Request failed: ${resp.status}`)
  }
  return resp.json()
}

export function startRumbleAnalysis(data) {
  return request('/rumble/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function checkRumbleResult(videoUrl, pattern) {
  const params = new URLSearchParams({ video_url: videoUrl, pattern })
  return request(`/rumble/check-result?${params.toString()}`)
}

export function getChannelVideos(limit = 100) {
  return request(`/channel/videos?limit=${limit}`)
}