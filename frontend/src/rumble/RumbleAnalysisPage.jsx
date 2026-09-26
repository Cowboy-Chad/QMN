import { useState } from 'react'
import { Video } from 'lucide-react'
import PatternSelector from '../components/PatternSelector'
import AnalysisRunner from '../components/AnalysisRunner'
import VideoPicker from '../rumble/VideoPicker'
import usePersistedState from '../hooks/usePersistedState'
import { startRumbleAnalysis, checkRumbleResult } from '../api/rumble'
import { useJob } from '../context/JobContext'

export default function RumbleAnalysisPage() {
  const { isJobRunning } = useJob()
  const [url, setUrl] = usePersistedState('rumble-url', '')
  const [pattern, setPattern] = usePersistedState('rumble-pattern', 'create_micro_summary')
  const [jobId, setJobId] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [checkMessage, setCheckMessage] = useState('')

  const handleAnalyze = async () => {
    setSubmitting(true)
    setError('')
    setJobId('')
    setCheckMessage('')
    try {
      const data = await startRumbleAnalysis({ video_url: url, pattern })
      setJobId(data.job_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleAutoCheck = async () => {
    setError('')
    setCheckMessage('')
    setJobId('')
    try {
      const data = await checkRumbleResult(url, pattern)
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
      <h1 className="text-2xl font-bold mb-6">Freely Analyze</h1>

      <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-6 space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">Rumble URL</label>
          <input
            type="text"
            placeholder="https://rumble.com/v..."
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onDoubleClick={() => setUrl('')}
            className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-violet-500"
          />
          <p className="mt-1 text-xs text-gray-500">
            Only videos from channel <strong>MarinaJacobi</strong> are supported.
          </p>
        </div>

        <VideoPicker onSelect={(videoUrl) => setUrl(videoUrl)} onClear={() => setUrl('')} />

        <PatternSelector
          value={pattern}
          onChange={setPattern}
          onEnter={handleAnalyze}
          onConfirm={handleAutoCheck}
          storageKey="rumble"
        />

        <button
          onClick={handleAnalyze}
          disabled={!url || !pattern || isJobRunning}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-gray-700 disabled:text-gray-500 rounded-lg font-medium transition"
        >
          <Video size={18} /> Analyze Rumble Video
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