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

export function startYouTubeAnalysis(data) {
  return request('/youtube/analyze', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export function checkYouTubeResult(url, pattern) {
  const params = new URLSearchParams({ url, pattern })
  return request(`/youtube/check-result?${params.toString()}`)
}