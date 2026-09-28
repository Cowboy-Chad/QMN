import { useState, useEffect } from 'react'
import { useAuth } from '../context/AuthContext'
import Layout from '../components/Layout'
import SubscriptionModal from '../components/SubscriptionModal'
import { Lock, Sparkles } from 'lucide-react'

function Loading() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-gray-400 text-lg animate-pulse">Loading…</div>
    </div>
  )
}

/**
 * Gate for the YouTube page. Renders the page for a subscriber or a trial account;
 * otherwise it renders a locked panel *with* the nav bar, with the upsell modal on top.
 *
 * An exhausted trial (0 uses left) still gets the page, not the locked panel: the
 * backend deliberately admits those users so they can re-open an analysis they already
 * paid for. The page shows the upsell for anything new, and the modal reopens on top.
 *
 * The panel matters: this used to `return null` once the modal was dismissed, which
 * left a blank page with no way to navigate anywhere.
 *
 * The guard owns Layout, so both states stay inside the app chrome.
 */
export default function SubscriptionGuard({ children }) {
  const { hasYouTubeAccess, isSubscribed, isTrial, loading } = useAuth()
  const [showModal, setShowModal] = useState(true)

  // Reopen the modal when access is lost while standing on this page — e.g. the last
  // free-trial use is spent by an analysis running right here.
  useEffect(() => {
    if (!hasYouTubeAccess) setShowModal(true)
  }, [hasYouTubeAccess])

  if (loading) return <Loading />

  // "Has an entitlement" rather than "has uses left" — see the note above.
  const canUsePage = isSubscribed || isTrial

  if (canUsePage) {
    return (
      <Layout>
        {children}
        {/* Only ever overlaid when access is actually missing — showModal defaults to
            true, which must not put an upsell in front of a subscriber. */}
        {!hasYouTubeAccess && showModal && (
          <SubscriptionModal onClose={() => setShowModal(false)} />
        )}
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-lg mx-auto mt-16 text-center">
        <Lock className="text-gray-600 mx-auto mb-4" size={40} />
        <h1 className="text-xl font-semibold text-gray-100 mb-2">YouTube access required</h1>
        <p className="text-gray-400 mb-6">
          Start with 33 free analyses, or subscribe for $7/month. Rumble analysis stays free.
        </p>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-violet-600 hover:bg-violet-700 text-white font-medium rounded-lg transition"
        >
          <Sparkles size={18} />
          See your options
        </button>
      </div>

      {showModal && <SubscriptionModal onClose={() => setShowModal(false)} />}
    </Layout>
  )
}
