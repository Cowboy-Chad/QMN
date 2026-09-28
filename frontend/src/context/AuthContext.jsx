import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { request } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'))
  const [loading, setLoading] = useState(true)

  /** Re-read the current user from the server. */
  const refreshUser = useCallback(async () => {
    if (!localStorage.getItem('auth_token')) {
      setUser(null)
      return null
    }
    try {
      const u = await request('/auth/me')
      setUser(u)
      return u
    } catch (e) {
      if (e.status === 401) {
        localStorage.removeItem('auth_token')
        setToken(null)
        setUser(null)
      }
      return null
    }
  }, [])

  // On mount: validate the stored token. Runs once — later token changes are handled
  // by login/register/logout and the cross-tab listener below.
  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    refreshUser().finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Keep the account state fresh. Both listeners exist because the trial counter and
  // the subscription status are server-side, so a stale tab would show a stale count:
  //  - focus: this tab was in the background while a job ran elsewhere
  //  - storage: another tab logged in/out (`storage` fires only in *other* tabs)
  useEffect(() => {
    const onFocus = () => {
      if (localStorage.getItem('auth_token')) refreshUser()
    }
    const onStorage = (e) => {
      if (e.key !== 'auth_token') return
      setToken(e.newValue)
      if (e.newValue) {
        refreshUser()
      } else {
        setUser(null) // another tab logged out
      }
    }
    window.addEventListener('focus', onFocus)
    window.addEventListener('storage', onStorage)
    return () => {
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('storage', onStorage)
    }
  }, [refreshUser])

  const adoptSession = useCallback((data) => {
    localStorage.setItem('auth_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    })
    return adoptSession(data)
  }, [adoptSession])

  const register = useCallback(async (fullName, email, password) => {
    const data = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ full_name: fullName, email, password }),
    })
    return adoptSession(data)
  }, [adoptSession])

  const mockSubscribe = useCallback(async () => {
    const data = await request('/payments/mock-subscribe', { method: 'POST' })
    // Re-read rather than patching fields by hand: /me is the source of truth and the
    // mock payment may change more than the two fields we know about here.
    await refreshUser()
    return data
  }, [refreshUser])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
  }, [])

  /**
   * Apply a trial count returned by an analyze call, so the UI ticks down without a
   * second /me round-trip. Ignores null (a duplicate hit or a subscriber: not charged).
   */
  const applyTrialRemaining = useCallback((n) => {
    if (n === null || n === undefined) return
    setUser((prev) => (prev ? { ...prev, trial_uses_remaining: n } : prev))
  }, [])

  const isAuthenticated = !!token && !!user
  const isSubscribed = isAuthenticated && user.subscription_status === 'active'
  const trialUsesRemaining = user?.trial_uses_remaining ?? null
  // Has a trial at all (as opposed to 0 = used up, or null = never granted).
  const isTrial = isAuthenticated && trialUsesRemaining !== null
  // Access is granted by a paid subscription, or by a trial that still has uses.
  const hasYouTubeAccess = isSubscribed || (isTrial && trialUsesRemaining > 0)

  return (
    <AuthContext.Provider value={{
      user, token, loading,
      isAuthenticated, isSubscribed, isTrial, trialUsesRemaining, hasYouTubeAccess,
      login, register, logout, mockSubscribe, refreshUser, applyTrialRemaining,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
