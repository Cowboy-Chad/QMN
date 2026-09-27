import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { request } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'))
  const [loading, setLoading] = useState(true)

  // On mount: validate stored token
  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    request('/auth/me')
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem('auth_token')
        setToken(null)
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const login = useCallback(async (displayId, firstName) => {
    const data = await request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ display_id: displayId, first_name: firstName }),
    })
    localStorage.setItem('auth_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const register = useCallback(async (firstName) => {
    const data = await request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ first_name: firstName }),
    })
    localStorage.setItem('auth_token', data.access_token)
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }, [])

  const mockSubscribe = useCallback(async () => {
    const data = await request('/payments/mock-subscribe', {
      method: 'POST',
    })
    // Update user with new subscription status
    if (data.success && user) {
      setUser((prev) => ({
        ...prev,
        subscription_status: data.subscription_status,
        subscription_expires_at: data.subscription_expires_at,
      }))
    }
    return data
  }, [user])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setToken(null)
    setUser(null)
  }, [])

  const isAuthenticated = !!token && !!user
  const isSubscribed = isAuthenticated && user.subscription_status === 'active'

  return (
    <AuthContext.Provider value={{ user, token, loading, isAuthenticated, isSubscribed, login, register, mockSubscribe, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}