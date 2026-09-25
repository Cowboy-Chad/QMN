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

/**
 * Shared API functions — used by multiple feature pages.
 */
export function pollJob(jobId) {
  return request(`/jobs/${jobId}`)
}

export function getPatterns() {
  return request('/patterns')
}