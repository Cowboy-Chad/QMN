import { useState } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield, AlertTriangle } from 'lucide-react'

const inputClass =
  'w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent'

export default function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  if (isAuthenticated) return <Navigate to="/analysis/youtube" replace />

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError('Enter your email and password')
      return
    }
    setError('')
    setBusy(true)
    try {
      await login(email.trim(), password)
    } catch (err) {
      // The server returns one message for both "no such email" and "wrong password".
      setError(err.message || 'Login failed — check your email and password')
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
            <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
              placeholder="you@example.com"
              autoComplete="email"
              autoFocus
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
              placeholder="Your password"
              autoComplete="current-password"
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

        {/* Static, not a link: there is no reset flow and no email is ever sent, so
            offering a link would be a dead end. */}
        <div className="mt-4 flex items-start gap-2 text-xs text-gray-400 bg-gray-900 border border-gray-800 rounded-lg px-3 py-2">
          <AlertTriangle size={14} className="mt-0.5 shrink-0 text-amber-400/80" />
          <span>
            <span className="text-gray-300">Forgot your password?</span> Accounts cannot be
            recovered — there is no reset and nothing is emailed. If you have lost it, create
            a new account.
          </span>
        </div>

        <p className="text-center text-gray-400 text-sm mt-6">
          New here?{' '}
          <Link to="/register" className="text-violet-400 hover:text-violet-300 underline">
            Get YouTube access
          </Link>
        </p>
      </div>
    </div>
  )
}
