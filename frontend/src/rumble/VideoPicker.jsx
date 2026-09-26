import { useEffect, useRef, useState } from 'react'
import { Search, Loader2 } from 'lucide-react'
import { getChannelVideos } from '../api/rumble'

export default function VideoPicker({ onSelect, onClear }) {
  const [videos, setVideos] = useState([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [count, setCount] = useState(0)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(false)
  const [highlightedIndex, setHighlightedIndex] = useState(-1)
  const inputRef = useRef(null)
  const listRef = useRef(null)
  const lastClick = useRef(0)
  const pastingRef = useRef(false)

  const handleInputClick = () => {
    const now = Date.now()
    if (now - lastClick.current < 400) {
      // Double-click / double-tap detected
      setQuery('')
      onClear?.()
      lastClick.current = 0
    } else {
      lastClick.current = now
    }
  }

  const selectVideo = (v) => {
    onSelect(v.url, v.title)
    setQuery(v.title || '')
    setOpen(false)
    inputRef.current?.blur()
  }

  const handlePaste = (e) => {
    const pasted = (e.clipboardData?.getData('text') || '').trim()
    if (!pasted || /^(https?:\/\/)?(www\.)?(rumble\.com|youtube\.com|youtu\.be)/i.test(pasted)) {
      return // let normal paste behavior handle URLs
    }

    const q = pasted.toLowerCase()
    const norm = (s) => s.replace(/s\s*(\d+)\s*e\s*(\d+)/gi, 's$1e$2')
    const match = videos.find((v) => {
      const title = (v.title || '').toLowerCase()
      return norm(title).includes(norm(q)) || title === q
    })

    if (match) {
      e.preventDefault()
      pastingRef.current = true
      selectVideo(match)
    }
  }

  useEffect(() => {
    let cancelled = false
    getChannelVideos(500)
      .then((data) => {
        if (cancelled) return
        if (data.videos) {
          setVideos(data.videos)
          setCount(data.videos.length)
        }
        if (data.error) setError(data.error)
      })
      .catch((e) => {
        if (!cancelled) setError(e.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [])

  const filtered = query.trim()
    ? videos.filter((v) => {
        const q = query.trim().toLowerCase()
        const title = (v.title || '').toLowerCase()
        // Normalize season/episode spacing so "S8 E11" matches "S8E11"
        const norm = (s) => s.replace(/s\s*(\d+)\s*e\s*(\d+)/g, 's$1e$2')
        return norm(title).includes(norm(q))
      })
    : videos

  return (
    <div className="relative">
      <label className="block text-xs font-medium text-gray-400 mb-1">Browse Channel Videos</label>
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            if (pastingRef.current) { pastingRef.current = false; return }
            setQuery(e.target.value); setOpen(true); setHighlightedIndex(-1)
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => setOpen(false)}
          onClick={handleInputClick}
          onPaste={handlePaste}
          onKeyDown={(e) => {
            if (e.key === 'ArrowDown') {
              e.preventDefault()
              setHighlightedIndex((prev) =>
                prev < filtered.length - 1 ? prev + 1 : 0
              )
            } else if (e.key === 'ArrowUp') {
              e.preventDefault()
              setHighlightedIndex((prev) =>
                prev > 0 ? prev - 1 : filtered.length - 1
              )
            } else if (e.key === 'Enter' && highlightedIndex >= 0 && filtered[highlightedIndex]) {
              e.preventDefault()
              selectVideo(filtered[highlightedIndex])
            }
          }}
          placeholder={loading ? `Loading all channel videos...` : `Search ${count} videos by title...`}
          className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-violet-500 transition"
        />
      </div>

      {open && (
        <div className="absolute z-20 mt-1 w-full bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-80 overflow-y-auto">
          {loading && (
            <div className="flex items-center gap-2 px-3 py-3 text-xs text-gray-400">
              <Loader2 className="animate-spin" size={14} />
              Loading all channel videos from Rumble...
            </div>
          )}
          {error && <div className="px-3 py-2 text-xs text-red-400">{error}</div>}
          {!loading && !error && filtered.length === 0 && (
            <div className="px-3 py-2 text-xs text-gray-500">No videos match your search.</div>
          )}
          {!loading && !error && count > 0 && (
            <div className="px-3 py-1.5 text-[10px] text-gray-600 border-b border-gray-700/50">
              {filtered.length} of {count} videos
            </div>
          )}
          {!loading &&
            filtered.map((v, i) => (
              <button
                key={v.url || i}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectVideo(v)}
                onMouseEnter={() => setHighlightedIndex(i)}
                className={`w-full text-left px-3 py-2 text-sm transition border-b border-gray-700/50 last:border-0 ${
                  i === highlightedIndex
                    ? 'bg-violet-600/30 text-white'
                    : 'text-gray-200 hover:bg-gray-700'
                }`}
                ref={(el) => {
                  if (i === highlightedIndex && el) {
                    el.scrollIntoView({ block: 'nearest' })
                  }
                }}
              >
                <div className="font-medium leading-snug">{v.title || 'Untitled'}</div>
                <div className="text-xs text-gray-500 mt-0.5">
                  {v.duration ? `${Math.floor(v.duration / 60)}:${String(v.duration % 60).padStart(2, '0')}` : ''}
                  {v.view_count != null ? ` · ${v.view_count.toLocaleString()} views` : ''}
                  {v.upload_date ? ` · ${v.upload_date}` : ''}
                </div>
              </button>
            ))}
        </div>
      )}

    </div>
  )
}