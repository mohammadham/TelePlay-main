import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { Download, CheckCircle, Clock, Loader } from 'lucide-react'

const STATUS_CONFIG = {
  queued: { icon: Clock, color: 'text-purple-400', bg: 'bg-purple-500/20' },
  downloading: { icon: Loader, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  done: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' },
  error: { icon: Download, color: 'text-red-400', bg: 'bg-red-500/20' },
}

export default function Downloads() {
  const { data, isLoading } = useQuery({
    queryKey: ['downloads'],
    queryFn: async () => (await api.get('/v1/music/downloads')).data.catch(() => []),
    staleTime: 60000,
  })
  const list = Array.isArray(data) ? data : []

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
              <div key={i} className="glass-card p-4 flex items-center gap-4">
                <div className="skeleton-spotify w-12 h-12 rounded" />
                <div className="flex-1 space-y-2">
                  <div className="skeleton-spotify h-4 w-1/3 rounded" />
                  <div className="skeleton-spotify h-3 w-1/4 rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : list.length === 0 ? (
          <div className="text-center py-12 text-white/40 animate-fade-in-up">
            <Download className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p className="text-lg font-medium text-white/60">No downloads yet</p>
            <p className="text-sm mt-2">Tap Download on any track to start</p>
          </div>
        ) : (
          <div className="space-y-3 animate-fade-in-up">
            {list.map((d: any) => {
              const config = STATUS_CONFIG[d.status] || STATUS_CONFIG.queued
              const Icon = config.icon
              return (
                <div key={d.id} className="glass-card p-4 flex items-center gap-4 hover:bg-[#282828] transition-colors">
                  <div className="w-12 h-12 rounded bg-[#282828] flex items-center justify-center text-xl shrink-0">
                    🎵
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-white truncate">{d.track?.title || 'Unknown Track'}</p>
                    <p className="text-sm text-white/60">
                      {new Date(d.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className={`px-3 py-1 rounded-full ${config.bg} ${config.color} text-sm font-medium`}>
                      <Icon className="w-4 h-4 inline mr-1" />
                      {d.status}
                    </div>
                    {d.status === 'downloading' && (
                      <div className="w-24 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#1DB954] rounded-full transition-all"
                          style={{ width: `${d.progress || 0}%` }}
                        />
                      </div>
                    )}
                    <span className="text-sm text-white/60 w-12 text-right">
                      {d.progress || 0}%
                    </span>
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
