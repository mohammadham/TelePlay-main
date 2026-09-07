import { useMemo } from 'react'
import { X, Trash2, ChevronUp, ChevronDown, Play } from 'lucide-react'
import { useMusicStore } from '../../lib/musicStore'

interface Props {
  onClose: () => void
}

export default function QueuePanel({ onClose }: Props) {
  const { queue, queueIndex, currentTrack, setQueue, removeTrack } = useMusicStore()

  const trackCount = useMemo(() => queue.length, [queue])
  const currentIndex = queueIndex >= 0 ? queueIndex : -1

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-[#181818] rounded-t-2xl border border-white/10 max-h-[70vh] flex flex-col shadow-2xl animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <h2 className="text-lg font-bold">Queue <span className="text-white/40 text-sm font-normal">({trackCount} tracks)</span></h2>
          <button onClick={onClose} className="text-white/50 hover:text-white transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Current playing */}
        {currentTrack && (
          <div className="px-6 py-3 bg-[#1DB954]/10 border-b border-[#1DB954]/20">
            <p className="text-xs text-[#1DB954] font-medium uppercase tracking-wider mb-2">Now Playing</p>
            <div className="flex items-center gap-3">
              <Play className="w-5 h-5 text-[#1DB954]" />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-white truncate">{currentTrack.title}</p>
                <p className="text-xs text-white/60 truncate">{currentTrack.artist?.name}</p>
              </div>
            </div>
          </div>
        )}

        {/* Queue list */}
        <div className="flex-1 overflow-y-auto px-6 py-3 space-y-1">
          {queue.map((track: any, idx: number) => (
            <div
              key={`${track.id}-${idx}`}
              className={`flex items-center gap-3 p-3 rounded-lg transition-colors ${
                idx === currentIndex ? 'bg-[#1DB954]/20 border border-[#1DB954]/30' : 'hover:bg-[#282828]'
              }`}
            >
              <span className="text-white/30 text-sm w-6 text-center font-mono">{idx + 1}</span>
              <img
                src={track.cover_url || track.thumbnail_url || ''}
                alt=""
                className="w-10 h-10 rounded object-cover shrink-0"
              />
              <div className="min-w-0 flex-1">
                <p className="font-medium text-white truncate">{track.title}</p>
                <p className="text-xs text-white/50 truncate">{track.artist?.name || 'Unknown Artist'}</p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    if (idx > 0) {
                      const newQueue = [...queue]
                      ;[newQueue[idx - 1], newQueue[idx]] = [newQueue[idx], newQueue[idx - 1]]
                      setQueue(newQueue, idx - 1)
                    }
                  }}
                  disabled={idx === 0}
                  className="p-1.5 text-white/40 hover:text-white disabled:opacity-20 transition-colors"
                  title="Move up"
                >
                  <ChevronUp className="w-4 h-4" />
                </button>
                <button
                  onClick={() => {
                    if (idx < queue.length - 1) {
                      const newQueue = [...queue]
                      ;[newQueue[idx], newQueue[idx + 1]] = [newQueue[idx + 1], newQueue[idx]]
                      setQueue(newQueue, idx + 1)
                    }
                  }}
                  disabled={idx === queue.length - 1}
                  className="p-1.5 text-white/40 hover:text-white disabled:opacity-20 transition-colors"
                  title="Move down"
                >
                  <ChevronDown className="w-4 h-4" />
                </button>
                <button
                  onClick={() => removeTrack(idx)}
                  className="p-1.5 text-red-400/60 hover:text-red-400 transition-colors"
                  title="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
