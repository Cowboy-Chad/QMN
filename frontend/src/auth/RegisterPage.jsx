import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield, CheckCircle, CreditCard, Sparkles, AlertTriangle } from 'lucide-react'

const TRIAL_LIMIT = 33
const MIN_PASSWORD = 8
// bcrypt silently ignores anything past 72 bytes, so the server rejects longer
// passwords instead. Checked here too so the user finds out before submitting.
const MAX_PASSWORD_BYTES = 72

const inputClass =
  'w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent'

export default function RegisterPage() {
  const { register, mockSubscribe, isAuthenticated, user } = useAuth()
  const navigate = useNavigate()
  // form → choose → payment → done
  const [step, setStep] = useState('form')
  // Set once registration succeeds. Without it the isAuthenticated guard below would
  // immediately bounce the brand-new user away from the trial-or-pay choice.
  const [justRegistered, setJustRegistered] = useState(false)
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)


  // A logged-in user cannot create a second account. Previously this only bounced
  // *subscribed* users, so a logged-in free user could register again.
  if (isAuthenticated && !justRegistered) return <Navigate to="/analysis/youtube" replace />

  const byteLength = (s) => new TextEncoder().encode(s).length

  const handleRegister = async (e) => {
    e.preventDefault()
    if (!fullName.trim()) return setError('Enter your full name')
    if (!email.trim()) return setError('Enter your email address')
    if (password.length < MIN_PASSWORD) {
      return setError(`Password must be at least ${MIN_PASSWORD} characters`)
    }
    if (byteLength(password) > MAX_PASSWORD_BYTES) {
      return setError(`Password must be at most ${MAX_PASSWORD_BYTES} bytes`)
    }
    setError('')
    setBusy(true)
    try {
      await register(fullName.trim(), email.trim(), password)
      setJustRegistered(true)
      setStep('choose')
    } catch (err) {
      setError(
        err.code === 'email_taken'
          ? 'That email is already registered — try signing in instead.'
          : err.message || 'Registration failed'
      )
    } finally {
      setBusy(false)
    }
  }

  const handlePayment = async () => {
    setError('')
    setBusy(true)
    try {
      await mockSubscribe()
      setStep('done')
    } catch (err) {
      setError(err.message || 'Payment failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Shield className="text-violet-400 mx-auto mb-3" size={40} />
          <h1 className="text-2xl font-bold text-gray-100">Get YouTube Access</h1>
          <p className="text-gray-400 mt-1">
            {TRIAL_LIMIT} free analyses, or $7/month for unlimited
          </p>
        </div>

        {step === 'form' && (
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Full name</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className={inputClass}
                placeholder="Ada Lovelace"
                autoFocus
                autoComplete="name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={inputClass}
                placeholder="you@example.com"
                autoComplete="email"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={inputClass}
                placeholder={`At least ${MIN_PASSWORD} characters`}
                autoComplete="new-password"
              />
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            {/* There is no password reset — no email is ever sent — so a forgotten
                password permanently costs the account and its private history. */}
            <div className="flex items-start gap-2 text-xs text-amber-300/90 bg-amber-900/10 border border-amber-800/30 rounded-lg px-3 py-2">
              <AlertTriangle size={14} className="mt-0.5 shrink-0" />
              <span>
                There is no password reset — nothing is sent to your email. Choose a
                password you will remember; if you lose it, the account and its YouTube
                history cannot be recovered.
              </span>
            </div>

            <button
              type="submit"
              disabled={busy}
              className="w-full py-2.5 bg-violet-600 hover:bg-violet-700 disabled:bg-violet-800/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition"
            >
              {busy ? 'Creating account…' : 'Create account'}
            </button>

            <p className="text-center text-gray-400 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-violet-400 hover:text-violet-300 underline">
                Sign in
              </Link>
            </p>
          </form>
        )}

        {step === 'choose' && (
          <div className="space-y-4">
            <div className="text-center text-gray-300 text-sm">
              Welcome, <span className="text-violet-300 font-medium">{user?.full_name || user?.first_name}</span>!
              You're <span className="text-violet-300 font-medium">#{user?.display_id}</span>.
            </div>

            <button
              onClick={() => navigate('/analysis/youtube', { replace: true })}
              className="w-full text-left bg-gray-800 hover:bg-gray-700 border border-violet-700/50 hover:border-violet-600 rounded-xl p-4 transition"
            >
              <div className="flex items-center gap-2 mb-1">
                <Sparkles className="text-violet-400" size={18} />
                <span className="font-semibold text-gray-100">Start your free trial</span>
              </div>
              <p className="text-sm text-gray-400">
                {TRIAL_LIMIT} analyses, no card required. Active immediately.
              </p>
            </button>

            <button
              onClick={() => setStep('payment')}
              className="w-full text-left bg-gray-800 hover:bg-gray-700 border border-gray-700 hover:border-gray-600 rounded-xl p-4 transition"
            >
              <div className="flex items-center gap-2 mb-1">
                <CreditCard className="text-blue-400" size={18} />
                <span className="font-semibold text-gray-100">Subscribe — $7/month</span>
              </div>
              <p className="text-sm text-gray-400">
                Unlimited analyses and private YouTube history. Cancel anytime.
              </p>
            </button>

            <p className="text-center text-gray-500 text-xs">
              Both options are available later — you can subscribe whenever the trial runs out.
            </p>
          </div>
        )}

        {step === 'payment' && (
          <div className="space-y-4">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6">
              <div className="flex items-center justify-center mb-4">
                <CreditCard className="text-blue-400" size={32} />
              </div>
              <div className="text-center mb-4">
                <div className="text-lg font-semibold text-gray-100">PayPal</div>
                <div className="text-sm text-gray-400 mt-1">Subscription: $7.00/month</div>
              </div>
              <div className="bg-gray-900 rounded-lg p-3 mb-4 text-xs text-gray-400 font-mono">
                <div className="flex justify-between mb-1">
                  <span>Marina's Wisdom</span>
                  <span>$7.00/mo</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span>Next billing</span>
                  <span>30 days</span>
                </div>
                <div className="border-t border-gray-700 pt-1 mt-1 flex justify-between font-semibold text-gray-200">
                  <span>Total</span>
                  <span>$7.00/month</span>
                </div>
              </div>

              <button
                onClick={handlePayment}
                disabled={busy}
                className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800/50 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
              >
                <CreditCard size={18} />
                {busy ? 'Processing…' : 'Confirm $7/month'}
              </button>
            </div>

            {error && (
              <div className="text-red-400 text-sm bg-red-900/20 border border-red-800/40 rounded-lg px-3 py-2">
                {error}
              </div>
            )}

            <button
              onClick={() => setStep('choose')}
              className="w-full py-2 text-gray-400 hover:text-gray-300 text-sm transition"
            >
              Back
            </button>

            <p className="text-center text-gray-500 text-xs">
              This is a mock payment for development. No real charges.
            </p>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center space-y-4">
            <CheckCircle className="text-green-400 mx-auto" size={48} />
            <h2 className="text-xl font-semibold text-gray-100">Subscription Active!</h2>
            <button
              onClick={() => navigate('/analysis/youtube', { replace: true })}
              className="w-full py-2.5 bg-violet-600 hover:bg-violet-700 text-white font-medium rounded-lg transition"
            >
              Go to YouTube analysis
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
