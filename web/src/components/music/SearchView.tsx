import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, MusicTrack, useToggleLike } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'
import { useSEO } from '../../hooks/useSEO'

export default function SearchView() {
  useSEO({ title: 'Search Music', description: 'Find your favorite tracks and artists' })
  const [q, setQ] = useState('')
  const { setQueue } = useMusicStore()
  const { setPreviewFile } = useAppStore()
  const qc = useQueryClient()
  const toggleLike = useToggleLike()
  const [downloading, setDownloading] = useState<number | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['music-search', q],
    queryFn: async () => (await api.get<any>('/v1/music/search', { params: { q } })).data,
    enabled: q.length >= 2,
    staleTime: 30000,
  })

  const tracks: MusicTrack[] = data?.tracks || []

  const handleLike = async (track: MusicTrack) => {
    try {
      await toggleLike.mutateAsync({ trackId: track.id, liked: track.is_liked })
      await qc.invalidateQueries({ queryKey: ['music-search', q] })
    } catch {}
  }

  const download = async (id: number) => {
    setDownloading(id)
    try { await api.post('/v1/music/downloads', { track_id: id }) } catch {}
    setDownloading(null)
  }

  const playTrack = (track: MusicTrack, index: number) => {
    if (track.media_type === 'music_video' || track.media_type === 'reel') {
      api.get(`/files/${track.file_id}`).then(r => {
        setPreviewFile(r.data as any)
      }).catch(console.error)
    } else {
      setQueue(tracks, index)
    }
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Sticky search header */}
      <div className="sticky top-0 z-10 bg-[#121212]/95 backdrop-blur-sm px-6 py-4 border-b border-white/10">
        <div className="max-w-xl mx-auto relative">
          <input
            value={q}
            onChange={e => setQ(e.target.value)}
            placeholder="What do you want to listen to?"
            className="w-full bg-white/10 border-none rounded-full px-6 py-3 pl-12 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 transition-all"
            dir="auto"
          />
          <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-white/40 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <div className="p-6">
        {q && (
          <h2 className="text-2xl font-bold mb-4">Search Results</h2>
        )}

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
        ) : tracks.length > 0 ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4 animate-fade-in-up">
            {tracks.map((t, idx) => (
              <TrackCard
                key={t.id}
                track={t}
                isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                onPlay={() => playTrack(t, idx)}
                onLike={() => handleLike(t)}
                downloading={downloading === t.id}
                onDownload={() => download(t.id)}
              />
            ))}
          </div>
        ) : q ? (
          <div className="text-center py-12 text-white/40 animate-fade-in-up">
            <p className="text-4xl mb-4">🔍</p>
            <p className="text-lg">No results found</p>
            <p className="text-sm mt-2">Try different keywords</p>
          </div>
        ) : null}
      </div>
    </div>
  )
}
