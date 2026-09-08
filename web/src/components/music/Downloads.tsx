import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { Download, CheckCircle, Clock, Loader, X } from 'lucide-react'
import { useSEO } from '../../hooks/useSEO'

interface DownloadItem {
  id: number
  track?: { title: string }
  created_at: string
  status: 'queued' | 'downloading' | 'done' | 'error'
  progress: number
}

const STATUS_CONFIG = {
  queued: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Queued' },
  downloading: { icon: Loader, color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Downloading' },
  done: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20', label: 'Done' },
  error: { icon: Download, color: 'text-red-400', bg: 'bg-red-500/20', label: 'Error' },
}

export default function Downloads() {
  useSEO({ title: 'Downloads', description: 'Your music download queue' })
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: async () => (await api.get('/v1/music/downloads')).data,
    staleTime: 60000,
  })

  const cancel = useMutation({
    mutationFn: (dq_id: number) => api.delete(`/v1/music/downloads/${dq_id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['downloads'] }),
  })
  const list: DownloadItem[] = Array.isArray(data) ? data : []

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Header */}
      <div className="px-6 py-8 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <h1 className="text-4xl font-bold mb-2 animate-fade-in-up">Downloads</h1>
        <p className="text-white/60 animate-fade-in-up">Your downloaded tracks</p>
      </div>

      <div className="p-6 space-y-3">
        {isLoading ? (
          <div className="space-y-3 animate-fade-in-up">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="card-spotify p-3 flex items-center gap-4">
                <div className="skeleton-spotify w-12 h-12 rounded shrink-0" />
                <div className="flex-1 space-y-2 min-w-0">
                  <div className="skeleton-spotify h-4 w-2/3 rounded" />
                  <div className="skeleton-spotify h-3 w-1/3 rounded" />
                  <div className="skeleton-spotify h-1 w-full rounded mt-2" />
                </div>
                <div className="skeleton-spotify w-16 h-6 rounded-full shrink-0" />
              </div>
            ))}
          </div>
        ) : list.length === 0 ? (
          <div className="text-center py-16 text-white/40 animate-fade-in-up">
            <Download className="w-16 h-16 mx-auto mb-4 opacity-40" />
            <p className="text-lg font-medium text-white/60">No downloads yet</p>
            <p className="text-sm mt-2">Tap Download on any track to start</p>
          </div>
        ) : (
          <div className="space-y-3 animate-fade-in-up">
            {list.map((d) => {
              const config = STATUS_CONFIG[d.status] || STATUS_CONFIG.queued
              const Icon = config.icon
              return (
                <div key={d.id} className="card-spotify p-3 flex items-center gap-4">
                  <div className="w-12 h-12 rounded bg-[#282828] flex items-center justify-center shrink-0">
                    <span className="text-lg">🎵</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">{d.track?.title || 'Unknown Track'}</p>
                    <p className="text-sm text-white/60 mt-0.5">
                      {new Date(d.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    </p>
                    {d.status === 'downloading' && (
                      <div className="mt-2 h-1 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#1DB954] rounded-full transition-all duration-300"
                          style={{ width: `${d.progress || 0}%` }}
                        />
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col items-end gap-2 shrink-0">
                    <div className={`px-2.5 py-1 rounded-full ${config.bg} ${config.color} text-xs font-medium flex items-center gap-1`}>
                      <Icon className="w-3 h-3" />
                      {config.label}
                    </div>
                    {d.status === 'done' && (
                      <span className="text-xs text-white/40">{d.progress || 100}%</span>
                    )}
                    {(d.status === 'queued' || d.status === 'downloading') && (
                      <button
                        onClick={() => cancel.mutate(d.id)}
                        disabled={cancel.isPending}
                        className="ml-2 w-8 h-8 rounded-full flex items-center justify-center text-red-400 hover:text-red-300 transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
