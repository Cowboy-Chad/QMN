import { useEffect, useMemo, useState } from 'react'
import { getHistory } from '../api/history'
import { useAuth } from '../context/AuthContext'
import { Clock, MonitorPlay, Video, Copy, ExternalLink, ChevronDown, ChevronUp, Search, X, Lock } from 'lucide-react'
import MarkdownResult from '../components/MarkdownResult'
import { formatMetadataLines } from '../utils/metadata'

const SOURCE_ICONS = {
  youtube: MonitorPlay,
  rumble: Video,
}

const SOURCE_COLORS = {
  youtube: 'text-red-400',
  rumble: 'text-green-400',
}

export default function HistoryPage() {
  const { isAuthenticated, user } = useAuth()
  const [jobs, setJobs] = useState([])
  const [source, setSource] = useState('')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [copiedResult, setCopiedResult] = useState(null)

  // `user?.id` and `isAuthenticated` are dependencies because the server scopes the
  // result to the caller: without them this list would stay stale across a login or
  // logout (it does not re-fetch today).
  useEffect(() => {
    let cancelled = false
    setLoading(true)
    getHistory(source ? { source } : {})
      .then((data) => { if (!cancelled) setJobs(data) })
      .catch(() => { if (!cancelled) setJobs([]) })
      .finally(() => { if (!cancelled) setLoading(false) })
    return () => { cancelled = true }
  }, [source, isAuthenticated, user?.id])

  // Normalize season/episode spacing so "S3E5" matches "S3 E5" and vice versa
  const norm = (s) => s.replace(/s\s*(\d+)\s*e\s*(\d+)/gi, 's$1e$2')

  const filteredJobs = useMemo(() => {
    const q = norm(query.trim().toLowerCase())
    if (!q) return jobs
    return jobs.filter((job) => {
      const m = job.metadata_json || {}
      // Format the UTC date for searchability
      const utcDate = (() => {
        const d = new Date(job.created_at.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(job.created_at) ? job.created_at : job.created_at + 'Z');
        return d.toLocaleString('en-US', { timeZone: 'UTC' });
      })()
      const haystack = [
        job.video_url,
        job.file_path,
        job.video_id,
        job.channel_id,
        job.channel_title,
        job.video_title,
        job.analyst_name,
        job.pattern,
        job.source,
        job.status,
        job.error,
        job.result,
        job.transcript,
        utcDate,
        m.title,
        m.channel,
        m.channel_url,
        m.webpage_url,
      ]
        .filter(Boolean)
        .map(norm)
        .join('\n')
        .toLowerCase()
      return haystack.includes(q)
    })
  }, [jobs, query])

  const handleCopy = (text, id) => {
    navigator.clipboard.writeText(text)
    setCopiedResult(id)
    setTimeout(() => setCopiedResult(null), 5000)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">History</h1>

      <div className="flex gap-2 mb-6">
        {['', 'youtube', 'rumble'].map((s) => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition ${
              source === s
                ? 'bg-violet-600 text-white'
                : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
            }`}
          >
            {s ? s.charAt(0).toUpperCase() + s.slice(1) : 'All'}
          </button>
        ))}
      </div>

      <div className="relative mb-6">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by URL, title, channel, pattern, result..."
          className="w-full pl-9 pr-8 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500 transition"
        />
        {query && (
          <button onClick={() => setQuery('')} className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-gray-700 rounded transition">
            <X size={14} className="text-gray-500" />
          </button>
        )}
      </div>

      {loading && <div className="text-gray-400">Loading...</div>}

      {!loading && filteredJobs.length === 0 && (
        <div className="text-gray-500 text-center py-12">
          {query ? (
            'No matches for your search.'
          ) : source === 'youtube' && !isAuthenticated ? (
            // YouTube history is per-user, so a logged-out visitor sees none of it.
            // Saying "no results yet" here would be misleading.
            <span className="inline-flex flex-col items-center gap-2">
              <Lock size={20} className="text-gray-600" />
              YouTube history is private. Sign in to see your own analyses.
            </span>
          ) : (
            'No results yet. Run an analysis first.'
          )}
        </div>
      )}

      <div className="space-y-3">
        {filteredJobs.map((job) => {
          const Icon = SOURCE_ICONS[job.source] || Clock
          const color = SOURCE_COLORS[job.source] || 'text-gray-400'
          const expanded = expandedId === job.id

          return (
            <div key={job.id} className="bg-gray-900/50 border border-gray-800 rounded-lg overflow-hidden">
              <div
                onClick={() => setExpandedId(expanded ? null : job.id)}
                className="flex items-center gap-3 p-4 cursor-pointer hover:bg-gray-800/50 transition"
              >
                <Icon className={color} size={20} />
                <div className="flex-1 min-w-0">
                  {job.metadata_json?.title && (
                    <div className="text-sm font-medium truncate text-gray-200">
                      <span className="text-violet-400">Title:</span> {job.metadata_json.title}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium truncate"><span className="text-violet-400">Video URL:</span> {job.video_url ? (
                      <a href={job.video_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 hover:underline">{job.video_url}</a>
                    ) : (job.file_path || '—')}</span>
                    {job.status === 'failed' && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-red-900/50 text-red-300">Failed</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-200 mt-0.5 leading-relaxed">
                    <div><span className="text-violet-400">Analyst:</span> {job.analyst_name}{job.analyst_display_id ? <span className="text-gray-500"> (#{job.analyst_display_id})</span> : ''}</div>
                    <div><span className="text-violet-400">Source:</span> {job.source === 'rumble' ? "Marina Jacobi's Rumble Channel" : (job.source || '—')}</div>
                    <div><span className="text-violet-400">Pattern Used:</span> {job.pattern}</div>
                    <div><span className="text-violet-400">At UTC Time:</span> {(function() {
                      const d = new Date(job.created_at.endsWith('Z') || /[+-]\d{2}:\d{2}$/.test(job.created_at) ? job.created_at : job.created_at + 'Z');
                      return d.toLocaleString('en-US', { timeZone: 'UTC' });
                    })()}</div>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {expanded ? <ChevronUp size={18} className="text-gray-500" /> : <ChevronDown size={18} className="text-gray-500" />}
                </div>
              </div>

              {expanded && (
                <div className="px-4 pb-4 border-t border-gray-800 pt-3 space-y-3">
                  {job.result && (
                    <div>
                      <div className="text-xs font-medium text-gray-400 mb-1">Result</div>
                      <div className="bg-gray-800/50 rounded p-3">
                        {(() => {
                          const meta = job.metadata_json || {};
                          const lines = formatMetadataLines(meta);
                          const metaText = lines.length > 0 ? lines.join('\n') : null;
                          return (
                            <>
                              {metaText && <pre className="text-xs text-gray-400 whitespace-pre-wrap mb-3 pb-3 border-b border-gray-700">{metaText}</pre>}
                              <MarkdownResult content={job.result} />
                            </>
                          );
                        })()}
                      </div>
                    </div>
                  )}
                  {job.transcript && (
                    <div>
                      <div className="text-xs font-medium text-gray-400 mb-1">Transcript</div>
                      <div className="bg-gray-800/30 rounded p-3 text-xs text-gray-400 whitespace-pre-wrap max-h-40 overflow-y-auto">{job.transcript}</div>
                    </div>
                  )}
                  {job.error && (
                    <div>
                      <div className="text-xs font-medium text-red-400 mb-1">Failed</div>
                      <div className="bg-red-900/20 border border-red-800/50 rounded p-3 text-xs text-red-300">{job.error}</div>
                    </div>
                  )}
                  <div className="flex gap-2">
                    {job.result && (
                      <button onClick={() => {
                        const meta = job.metadata_json || {};
                        const prefix = formatMetadataLines(meta).join('\n');
                        const full = prefix ? prefix + '\n\n' + job.result : job.result;
                        handleCopy(full, `result-${job.id}`);
                      }} className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${copiedResult === `result-${job.id}` ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-700 hover:bg-gray-600'}`}>
                        <Copy size={12} /> Copy Result
                      </button>
                    )}
                    {job.transcript && (
                      <button onClick={() => handleCopy(job.transcript, `transcript-${job.id}`)} className={`flex items-center gap-1 text-xs px-2 py-1 rounded ${copiedResult === `transcript-${job.id}` ? 'bg-green-600 hover:bg-green-500' : 'bg-gray-700 hover:bg-gray-600'}`}>
                        <Copy size={12} /> Copy Transcript
                      </button>
                    )}
                    {job.video_url && (
                      <a href={job.video_url} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-xs px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded">
                        <ExternalLink size={12} /> Open This Video
                      </a>
                    )}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}