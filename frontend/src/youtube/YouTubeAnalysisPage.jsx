import { useState } from 'react'
import { MonitorPlay, Sparkles, AlertTriangle } from 'lucide-react'
import PatternSelector from '../components/PatternSelector'
import AnalysisRunner from '../components/AnalysisRunner'
import usePersistedState from '../hooks/usePersistedState'
import { useAuth } from '../context/AuthContext'
import { startYouTubeAnalysis, checkYouTubeResult } from '../api/youtube'

const TRIAL_LIMIT = 33

export default function YouTubeAnalysisPage() {
  const { isTrial, isSubscribed, trialUsesRemaining, applyTrialRemaining, refreshUser } = useAuth()
  const [url, setUrl] = usePersistedState('yt-url', '')
  const [pattern, setPattern] = usePersistedState('yt-pattern', 'create_micro_summary')
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [checkMessage, setCheckMessage] = useState('')

  const showCounter = isTrial && !isSubscribed
  const trialExhausted = showCounter && trialUsesRemaining <= 0
  const trialLow = showCounter && !trialExhausted && trialUsesRemaining <= 5

  const handleAnalyze = async () => {
    // Enter on a confirmed pattern calls this directly, bypassing the disabled button,
    // so the exhausted case needs handling here too rather than a silent 402.
    if (trialExhausted) {
      setError(
        'Your free trial is used up. Subscribe to analyze new videos — analyses you already ran are still in History.'
      )
      return
    }
    setSubmitting(true)
    setError('')
    setJobId('')
    setCheckMessage('')
    try {
      const data = await startYouTubeAnalysis({ video_url: url, pattern })
      // Tick the counter from the response — it is authoritative (a duplicate hit
      // returns the unchanged count, a subscriber is never charged).
      applyTrialRemaining(data.trial_uses_remaining)
      setJobId(data.job_id)
    } catch (e) {
      if (e.code === 'trial_exhausted') {
        // Re-read the account so the exhausted panel and badge appear, rather than
        // printing the raw error body.
        await refreshUser()
        setError('')
      } else {
        setError(e.message)
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleAutoCheck = async () => {
    setError('')
    setCheckMessage('')
    setJobId('')
    try {
      const data = await checkYouTubeResult(url, pattern)
      applyTrialRemaining(data.trial_uses_remaining)
      if (data.found) {
        setJobId(data.job.id)
      } else {
        setCheckMessage('not_found')
      }
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">YouTube Analysis</h1>

      {showCounter && (
        <div
          className={`mb-4 rounded-lg px-3 py-2 text-sm flex items-center gap-2 border ${
            trialExhausted
              ? 'bg-amber-900/20 border-amber-800/40 text-amber-200'
              : trialLow
                ? 'bg-amber-900/10 border-amber-800/30 text-amber-300'
                : 'bg-violet-900/20 border-violet-800/40 text-violet-200'
          }`}
        >
          {trialExhausted ? <AlertTriangle size={16} /> : <Sparkles size={16} />}
          {trialExhausted ? (
            <span>
              Your free trial is used up ({TRIAL_LIMIT} of {TRIAL_LIMIT} used). Subscribe for
              $7/month to keep analyzing — analyses you already ran are still available in
              History.
            </span>
          ) : (
            <span>
              Free trial: <strong>{trialUsesRemaining}</strong> of {TRIAL_LIMIT} analyses left
            </span>
          )}
        </div>
      )}

      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">YouTube URL</label>
          <input
            type="text"
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
        </div>

        <PatternSelector
          value={pattern}
          onChange={setPattern}
          onEnter={handleAnalyze}
          onConfirm={handleAutoCheck}
          storageKey="youtube"
        />

        <button
          onClick={handleAnalyze}
          disabled={!url || !pattern || trialExhausted}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition focus:outline-none focus:ring-2 focus:ring-violet-400"
        >
          <MonitorPlay size={18} />
          {trialExhausted ? 'Free trial used up' : 'Analyze YouTube Video'}
        </button>

        {checkMessage === 'not_found' && (
          <div className="inline-block px-3 py-1.5 bg-red-900/50 border border-red-700 rounded text-xs text-red-300">
            No prior analysis found — just click the button or press the Enter key.
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300 text-sm">{error}</div>
        )}

        {submitting && (
          <div className="text-sm text-blue-400">Starting analysis...</div>
        )}
      </div>

      <AnalysisRunner jobId={jobId} />
    </div>
  )
}