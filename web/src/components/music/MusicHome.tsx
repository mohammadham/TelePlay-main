import { useQuery } from '@tanstack/react-query'
import { api, getMusicTracks, getMusicArtists, MusicTrack } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useState } from 'react'
import { Play } from 'lucide-react'
import { useAppStore } from '../../lib/store'

type MediaType = 'all' | 'music_video' | 'reel'

const MEDIA_TABS: { key: MediaType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'music_video', label: 'Music Videos' },
  { key: 'reel', label: 'Reels' },
]

export default function MusicHome() {
  const [mediaType, setMediaType] = useState<MediaType>('all')
  const { data: tracks } = useQuery({
    queryKey: ['music-tracks', mediaType],
    queryFn: async () => {
      const params: Record<string, string | number> = { per_page: 60 }
      if (mediaType !== 'all') params.media_type = mediaType
      return (await api.get<MusicTrack[]>('/v1/music/tracks', { params })).data
    },
    staleTime: 60000,
  })
  const { data: artists } = useQuery({
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
      // Open video in MediaPlayer via file lookup
      api.get(`/files/${track.file_id}`).then((r) => {
        const file = r.data
        setPreviewFile(file as any)
      }).catch(() => {})
    } else {
      setQueue(list, list.findIndex((t) => t.id === track.id))
    }
  }

  return (
    <div className="bg-[#121212] min-h-screen text-white pb-28">
      {/* Media type tabs */}
      <div className="flex gap-2 px-6 pt-4 pb-2 border-b border-white/5">
        {MEDIA_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setMediaType(key)}
            className={`px-4 py-1.5 rounded-full text-sm font-medium transition-colors ${
              mediaType === key
                ? 'bg-[#1DB954] text-black'
                : 'bg-white/10 text-white/70 hover:bg-white/20 hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="p-6 space-y-8">
        <section>
          <h2 className="text-2xl font-bold mb-4">
            {mediaType === 'all' ? 'Recently Added' : mediaType === 'music_video' ? 'Music Videos' : 'Reels'}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {list.map((t, idx) => (
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
            {list.length === 0 && (
              <p className="text-dark-400 col-span-full">
                No {mediaType === 'all' ? 'tracks' : mediaType === 'music_video' ? 'music videos' : 'reels'} yet — ask admin to upload via bot.
              </p>
            )}
          </div>
        </section>

        <section>
          <h2 className="text-xl font-bold mb-3">Popular Artists</h2>
          <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
            {(artists || []).map((a: any) => (
              <div key={a.id} className="min-w-[120px] text-center">
                <div className="w-28 h-28 rounded-full bg-dark-800 flex items-center justify-center text-2xl mx-auto">🎤</div>
                <p className="text-sm mt-2 truncate">{a.name}</p>
              </div>
            ))}
          </div>
        </section>

        <div className="glass-card p-4 text-center text-sm text-dark-400">
          Ad slot — banner (یک تانت / AdMob) — will show when ADS_ENABLED
        </div>
      </div>
    </div>
  )
}
