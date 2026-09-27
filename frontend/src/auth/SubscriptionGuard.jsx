import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import SubscriptionModal from '../components/SubscriptionModal'

export default function SubscriptionGuard({ children }) {
  const { isAuthenticated, isSubscribed, loading } = useAuth()
  const [showModal, setShowModal] = useState(true)

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400 text-lg animate-pulse">Loading…</div>
      </div>
    )
  }

  if (isAuthenticated && isSubscribed) {
    return children
  }

  // Show subscription modal for non-subscribers
  if (!showModal) return null

  return (
    <SubscriptionModal onClose={() => setShowModal(false)} />
  )
}