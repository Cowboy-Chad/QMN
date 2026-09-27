import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Shield, CheckCircle, CreditCard } from 'lucide-react'

export default function RegisterPage() {
  const { register, mockSubscribe, isAuthenticated, isSubscribed } = useAuth()
  const navigate = useNavigate()
  const [step, setStep] = useState('name') // name → payment → done
  const [firstName, setFirstName] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [registeredUser, setRegisteredUser] = useState(null)

  if (isAuthenticated && isSubscribed) return <Navigate to="/analysis/youtube" replace />

  const handleNameSubmit = async (e) => {
    e.preventDefault()
    if (!firstName.trim()) {
      setError('Enter your first name')
      return
    }
    if (firstName.trim().length > 50) {
      setError('First name is too long (max 50 characters)')
      return
    }
    setError('')
    setBusy(true)
    try {
      const user = await register(firstName.trim())
      setRegisteredUser(user)
      setStep('payment')
    } catch (err) {
      setError(err.message || 'Registration failed')
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
      // Auto-redirect to YouTube after 2 seconds
      setTimeout(() => navigate('/analysis/youtube', { replace: true }), 2000)
    } catch (err) {
      setError(err.message || 'Payment failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <Shield className="text-violet-400 mx-auto mb-3" size={40} />
          <h1 className="text-2xl font-bold text-gray-100">Subscribe to YouTube Access</h1>
          <p className="text-gray-400 mt-1">$7/month — Cancel anytime</p>
        </div>

        {step === 'name' && (
          <form onSubmit={handleNameSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                What's your first name?
              </label>
              <input
                type="text"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent"
                placeholder="Enter your first name"
                autoFocus
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
              {busy ? 'Creating account…' : 'Continue to Payment'}
            </button>

            <p className="text-center text-gray-400 text-sm">
              Already have an account?{' '}
              <Link to="/login" className="text-violet-400 hover:text-violet-300 underline">
                Sign in
              </Link>
            </p>
          </form>
        )}

        {step === 'payment' && (
          <div className="space-y-4">
            {registeredUser && (
              <div className="text-center text-gray-300 text-sm mb-4">
                Welcome, <span className="text-violet-300 font-medium">{registeredUser.first_name}</span>!
                You'll be User <span className="text-violet-300 font-medium">#{registeredUser.display_id}</span>.
              </div>
            )}

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

            <p className="text-center text-gray-500 text-xs">
              This is a mock payment for development. No real charges.
            </p>
          </div>
        )}

        {step === 'done' && (
          <div className="text-center space-y-4">
            <CheckCircle className="text-green-400 mx-auto" size={48} />
            <h2 className="text-xl font-semibold text-gray-100">Subscription Active!</h2>
            <p className="text-gray-400">
              Welcome aboard! Redirecting you to YouTube analysis…
            </p>
          </div>
        )}
      </div>
    </div>
  )
}