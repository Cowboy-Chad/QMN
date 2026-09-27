import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield } from 'lucide-react'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const [displayId, setDisplayId] = useState('')
  const [firstName, setFirstName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) return <Navigate to="/analysis/youtube" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    const id = parseInt(displayId, 10)
    if (!displayId || isNaN(id) || id < 1) {
      setError('Enter your User ID number')
      return
    }
    if (!firstName.trim()) {
      setError('Enter your first name')
      return
    }
    setError('')
    setBusy(true)
    try {
      await login(id, firstName.trim())
    } catch (err) {
      setError(err.message || 'Login failed — check your ID and name')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Shield className="text-violet-400 mx-auto mb-3" size={40} />
          <h1 className="text-2xl font-bold text-gray-100">Marina's Wisdom</h1>
          <p className="text-gray-400 mt-1">Sign in to your account</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">User ID</label>
            <input
              type="number"
              min="1"
              value={displayId}
              onChange={(e) => setDisplayId(e.target.value)}
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              placeholder="e.g. 7"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">First Name</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
              placeholder="Your first name"
            />
          </div>

          {error && (
            <div className="text-red-400 text-sm bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            className="w-full py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-800/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition"
          >
            {busy ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="text-center text-gray-400 text-sm mt-6">
          New here?{' '}
          <Link to="/register" className="text-violet-400 hover:text-violet-300 underline">
            Subscribe for $7/month
          </Link>
        </p>
      </div>
    </div>
  )
}