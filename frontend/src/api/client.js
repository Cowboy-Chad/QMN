const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

export async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = localStorage.getItem('auth_token')
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const resp = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options,
  })

  if (resp.status === 401) {
    localStorage.removeItem('auth_token')
    // Only redirect if not already on an auth page
    if (!window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
      window.location.href = '/login'
    }
    throw new Error('Session expired')
  }

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