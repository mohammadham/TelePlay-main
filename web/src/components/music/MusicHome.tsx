import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, getMusicTracks, getMusicArtists, MusicTrack } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'

type MediaType = 'all' | 'music_video' | 'reel'

const MEDIA_TABS: { key: MediaType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'music_video', label: 'Music Videos' },
  { key: 'reel', label: 'Reels' },
]

export default function MusicHome() {
  const [mediaType, setMediaType] = useState<MediaType>('all')
  const { data: tracks, isLoading } = useQuery({
    queryKey: ['music-tracks', mediaType],
    queryFn: async () => {
      const params: Record<string, string | number> = { per_page: 60 }
      if (mediaType !== 'all') params.media_type = mediaType
      return (await api.get<MusicTrack[]>('/v1/music/tracks', { params })).data
    },
    staleTime: 60000,
  })
  const { data: artists, isLoading: artistsLoading } = useQuery({
    queryKey: ['music-artists'],
    queryFn: async () => (await api.get<any[]>('/v1/music/artists')).data,
    staleTime: 120000,
  })
  const { setQueue } = useMusicStore()
  const { setPreviewFile } = useAppStore()
  const [downloading, setDownloading] = useState<number | null>(null)

  const list: MusicTrack[] = Array.isArray(tracks) ? tracks : []

  const like = async (id: number) => {
    try { await api.post(`/v1/music/likes/${id}`) } catch {}
  }

  const download = async (id: number) => {
    setDownloading(id)
    try { await api.post('/v1/music/downloads', { track_id: id }) } catch {}
    setDownloading(null)
  }

  const playTrack = (track: MusicTrack) => {
    if (track.media_type === 'music_video' || track.media_type === 'reel') {
      api.get(`/files/${track.file_id}`).then(r => {
        const file = r.data
        setPreviewFile(file as any)
      }).catch(() => {})
    } else {
      setQueue(list, list.findIndex((t) => t.id === track.id))
    }
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Hero section */}
      <div className="relative h-64 bg-gradient-to-b from-[#1DB954]/30 to-[#121212] flex items-end p-6">
        <div className="animate-fade-in-up">
          <p className="text-sm font-medium text-white/80 uppercase tracking-wider mb-2">Playlist</p>
          <h1 className="text-5xl font-bold mb-4">Good Evening</h1>
          <div className="flex gap-4">
            <button className="btn-spotify px-8 py-3 text-lg">
              Shuffle Play
            </button>
            <button className="btn-spotify-ghost px-6 py-3 text-lg">
              Explore More
            </button>
          </div>
        </div>
      </div>

      {/* Media type tabs */}
      <div className="flex gap-6 px-6 py-4 border-b border-white/10">
        {MEDIA_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setMediaType(key)}
            className={`text-sm font-medium transition-colors ${
              mediaType === key ? 'tab-active' : 'tab-inactive'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="p-6 space-y-10">
        {/* Recently Added */}
        <section className="animate-fade-in-up">
          <h2 className="section-title">{mediaType === 'all' ? 'Recently Added' : mediaType === 'music_video' ? 'Music Videos' : 'Reels'}</h2>
          {isLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="space-y-2">
                  <div className="skeleton-spotify aspect-square rounded-md" />
                  <div className="skeleton-spotify h-4 w-3/4 rounded" />
                  <div className="skeleton-spotify h-3 w-1/2 rounded" />
                </div>
              ))}
            </div>
          ) : list.length === 0 ? (
            <div className="text-center py-12 text-white/40">
              <p className="text-4xl mb-4">🎵</p>
              <p>No {mediaType === 'all' ? 'tracks' : mediaType === 'music_video' ? 'music videos' : 'reels'} yet</p>
              <p className="text-sm mt-2">Ask admin to upload via bot</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {list.map((t) => (
                <TrackCard
                  key={t.id}
                  track={t}
                  isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                  onPlay={() => playTrack(t)}
                  onLike={() => like(t.id)}
                  downloading={downloading === t.id}
                  onDownload={() => download(t.id)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Popular Artists */}
        <section>
          <h2 className="section-title">Popular Artists</h2>
          {artistsLoading ? (
            <div className="flex gap-6 overflow-x-auto no-scrollbar pb-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="min-w-[120px] text-center space-y-2">
                  <div className="skeleton-spotify w-28 h-28 rounded-full" />
                  <div className="skeleton-spotify h-4 w-20 mx-auto rounded" />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex gap-6 overflow-x-auto no-scrollbar pb-2">
              {(artists || []).map((a: any) => (
                <div key={a.id} className="min-w-[120px] text-center cursor-pointer group">
                  <div className="w-28 h-28 rounded-full bg-[#282828] flex items-center justify-center text-3xl mx-auto group-hover:bg-[#383838] transition-colors">
                    🎤
                  </div>
                  <p className="text-sm font-medium mt-3 text-white group-hover:text-white transition-colors">{a.name}</p>
                  <p className="text-xs text-white/60 mt-1">Artist</p>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
