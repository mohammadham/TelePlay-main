import { useQuery } from '@tanstack/react-query'
import { api, MusicTrack } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { Clock } from 'lucide-react'
import { useSEO } from '../../hooks/useSEO'

export default function HistoryView() {
  useSEO({ title: 'Recently Played', description: 'Your music listening history' })
  const { data: history, isLoading } = useQuery({
    queryKey: ['music-history'],
    queryFn: async () => (await api.get<any[]>('/v1/music/history', { params: { limit: 50 } })).data,
    staleTime: 30_000,
  })
  const { setQueue } = useMusicStore()

  const list: MusicTrack[] = Array.isArray(history) ? history.map((t: any) => t).filter(Boolean) : []

  const playTrack = (_track: MusicTrack, index: number) => {
    setQueue(list, index)
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      <div className="px-6 py-8 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <h1 className="text-4xl font-bold mb-2 animate-fade-in-up flex items-center gap-3">
          <Clock className="w-8 h-8 text-[#1DB954]" />
          Recently Played
        </h1>
        <p className="text-white/60 animate-fade-in-up">Your listening history</p>
      </div>

      <div className="p-6">
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 animate-fade-in-up">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="skeleton-spotify aspect-square rounded-md" />
                <div className="skeleton-spotify h-4 w-3/4 rounded" />
                <div className="skeleton-spotify h-3 w-1/2 rounded" />
              </div>
            ))}
          </div>
        ) : list.length === 0 ? (
          <div className="text-center py-16 text-white/40 animate-fade-in-up">
            <Clock className="w-16 h-16 mx-auto mb-4 opacity-40" />
            <p className="text-lg font-medium text-white/60">No listening history</p>
            <p className="text-sm mt-2">Start playing some music to see it here</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 animate-fade-in-up">
            {list.map((t, idx) => (
              <TrackCard
                key={t.id}
                track={t}
                isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                onPlay={() => playTrack(t, idx)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
