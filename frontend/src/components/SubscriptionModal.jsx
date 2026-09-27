import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { CreditCard, X, LogIn, CheckCircle } from 'lucide-react'

export default function SubscriptionModal({ onClose }) {
  const { isAuthenticated, user, mockSubscribe } = useAuth()
  const navigate = useNavigate()
  const [showMockPay, setShowMockPay] = useState(false)
  const [paying, setPaying] = useState(false)
  const [done, setDone] = useState(false)
  const [error, setError] = useState('')

  const handleSubscribe = () => {
    if (!isAuthenticated) {
      navigate('/register')
      return
    }
    // Logged in but not subscribed — show inline mock PayPal
    setShowMockPay(true)
  }

  const handleMockPayment = async () => {
    setError('')
    setPaying(true)
    try {
      await mockSubscribe()
      setDone(true)
      // Redirect to YouTube after a moment
      setTimeout(() => navigate('/analysis/youtube', { replace: true }), 1500)
    } catch (err) {
      setError(err.message || 'Payment failed')
    } finally {
      setPaying(false)
    }
  }

  const handleLogin = () => {
    navigate('/login')
  }

  if (done) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
        <div className="bg-gray-900 border border-gray-700 rounded-xl p-8 max-w-sm w-full mx-4 text-center" onClick={(e) => e.stopPropagation()}>
          <CheckCircle className="text-green-400 mx-auto mb-3" size={48} />
          <h2 className="text-xl font-semibold text-gray-100 mb-2">Subscription Active!</h2>
          <p className="text-gray-400">Redirecting to YouTube analysis…</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-gray-900 border border-gray-700 rounded-xl p-6 max-w-sm w-full mx-4 relative" onClick={(e) => e.stopPropagation()}>
        <button
          onClick={onClose}
          className="absolute top-3 right-3 p-1 rounded-lg text-gray-400 hover:text-gray-200 hover:bg-gray-800 transition"
        >
          <X size={20} />
        </button>

        <div className="text-center mb-5">
          <CreditCard className="text-violet-400 mx-auto mb-3" size={36} />
          <h2 className="text-lg font-bold text-gray-100">YouTube Analysis</h2>
          <p className="text-gray-400 text-sm mt-1">Requires a paid subscription</p>
        </div>

        {!showMockPay ? (
          <>
            <div className="bg-gray-800 rounded-lg p-4 mb-5">
              <div className="flex justify-between items-center mb-2">
                <span className="text-gray-300">YouTube Access</span>
                <span className="text-violet-300 font-semibold">$7.00/mo</span>
              </div>
              <ul className="text-sm text-gray-400 space-y-1">
                <li>• Analyze any YouTube video</li>
                <li>• Full analysis history</li>
                <li>• Cancel anytime via PayPal</li>
              </ul>
            </div>

            <div className="space-y-3">
              <button
                onClick={handleSubscribe}
                className="w-full py-2.5 bg-violet-600 hover:bg-violet-700 text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
              >
                <CreditCard size={18} />
                {isAuthenticated ? 'Activate $7/month' : 'Subscribe $7/month'}
              </button>

              <button
                onClick={handleLogin}
                className="w-full py-2.5 bg-gray-800 hover:bg-gray-700 text-gray-300 font-medium rounded-lg transition flex items-center justify-center gap-2"
              >
                <LogIn size={18} />
                {isAuthenticated ? 'Log out and switch account' : "I'm already a subscriber"}
              </button>
            </div>
          </>
        ) : (
          <div className="space-y-4">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4">
              <div className="text-center mb-3">
                <div className="text-sm font-medium text-gray-200">PayPal Mock Payment</div>
                <div className="text-xs text-gray-400 mt-1">
                  {user?.first_name}, you'll be charged $7.00/month
                </div>
              </div>
              <div className="bg-gray-900 rounded p-3 mb-3 text-xs text-gray-400 font-mono">
                <div className="flex justify-between mb-1">
                  <span>Plan</span>
                  <span>YouTube Access</span>
                </div>
                <div className="flex justify-between mb-1">
                  <span>Amount</span>
                  <span>$7.00/month</span>
                </div>
                <div className="flex justify-between">
                  <span>Next billing</span>
                  <span>In 30 days</span>
                </div>
              </div>

              {error && (
                <div className="text-red-400 text-xs mb-3 bg-red-900/20 border border-red-800/40 rounded px-2 py-1">
                  {error}
                </div>
              )}

              <button
                onClick={handleMockPayment}
                disabled={paying}
                className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800/50 disabled:cursor-not-allowed text-white font-medium rounded-lg transition flex items-center justify-center gap-2"
              >
                <CreditCard size={16} />
                {paying ? 'Processing…' : 'Confirm Payment'}
              </button>
            </div>
            <p className="text-center text-gray-500 text-xs">
              Mock payment for development — no real charges.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}