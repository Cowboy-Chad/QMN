const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api'

/**
 * Turn a failed response into an Error that is useful to both callers and users.
 *
 * The backend sends structured errors as {"detail": {"code", "message", ...}}. Without
 * this, `new Error(await resp.text())` put that raw JSON on the page verbatim.
 * The Error keeps `message` a human string (so every existing `setError(e.message)`
 * still works) and adds `status`, `code` and `data` for callers that need to branch —
 * e.g. `trial_exhausted` vs `email_taken`.
 */
async function toApiError(resp) {
  const text = await resp.text()
  let body = null
  try {
    body = text ? JSON.parse(text) : null
  } catch {
    // Not JSON (a proxy error page, say) — fall back to the raw text.
  }

  const detail = body?.detail
  let code
  let message

  if (Array.isArray(detail)) {
    // FastAPI request-validation errors: detail is a list of {loc, msg, type}.
    message = detail.map((d) => d?.msg).filter(Boolean).join('; ')
  } else if (detail && typeof detail === 'object') {
    code = detail.code
    message = detail.message
  } else if (typeof detail === 'string') {
    message = detail
  }

  const err = new Error(message || text || `Request failed: ${resp.status}`)
  err.status = resp.status
  err.code = code
  err.data = detail && typeof detail === 'object' ? detail : body
  return err
}

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

  // A 401 from the login/register endpoints means "wrong credentials", not "your
  // session expired" — there is no session yet to expire, and clearing the token and
  // bouncing here would replace the real message with "Session expired".
  //
  // /auth/me is a background *probe* (AuthContext validates a stored token with it on
  // mount). Treating its 401 as an expiry would bounce a visitor off the free Rumble
  // page and onto /login just for having an old token in localStorage. AuthContext
  // clears the token itself when this probe fails.
  const isAuthEndpoint = path.startsWith('/auth/login')
    || path.startsWith('/auth/register')
    || path.startsWith('/auth/me')

  if (resp.status === 401 && !isAuthEndpoint) {
    const hadToken = !!token
    localStorage.removeItem('auth_token')
    // Only redirect if not already on an auth page, and only if we actually had a
    // token to expire — a logged-out visitor hitting a protected endpoint should see
    // the page's own message, not a silent bounce.
    if (hadToken && !window.location.pathname.startsWith('/login') && !window.location.pathname.startsWith('/register')) {
      window.location.href = '/login'
    }
    const err = await toApiError(resp)
    err.code = err.code || 'session_expired'
    throw err
  }

  if (!resp.ok) {
    throw await toApiError(resp)
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
