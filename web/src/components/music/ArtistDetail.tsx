import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { api, MusicTrack } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { ArrowLeft, Verified } from 'lucide-react'
import { useSEO } from '../../hooks/useSEO'

export default function ArtistDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { setQueue } = useMusicStore()
  const qc = useQueryClient()
  const [downloading, setDownloading] = useState<number | null>(null)
  useSEO({
    title: artist?.name || 'Artist',
    description: artist?.bio || 'Browse artist tracks',
    type: 'music_group',
    image: artist?.avatar_url,
  })

  const { data: artist, isLoading } = useQuery({
    queryKey: ['artist', id],
    queryFn: async () => (await api.get(`/v1/music/artists/${id}`)).data,
    enabled: !!id,
  })

  const tracks: MusicTrack[] = artist?.tracks || []

  const playAll = () => {
    if (tracks.length > 0) setQueue(tracks, 0)
  }

  const handleLike = async (track: MusicTrack) => {
    try {
      await api.post(`/v1/music/likes/${track.id}`)
      await qc.invalidateQueries({ queryKey: ['artist', id] })
    } catch {}
  }

  const download = async (id: number) => {
    setDownloading(id)
    try { await api.post('/v1/music/downloads', { track_id: id }) } catch {}
    setDownloading(null)
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Header */}
      <div className="px-6 py-6 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-white/60 hover:text-white mb-4 transition-colors">
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <div className="flex items-end gap-6">
          <div className="w-40 h-40 rounded-full bg-[#282828] flex items-center justify-center shadow-2xl overflow-hidden">
            {artist?.avatar_url ? (
              <img src={artist.avatar_url} alt={artist?.name} className="w-full h-full object-cover" />
            ) : artist?.verified ? (
              <div className="relative">
                <span className="text-5xl">🎤</span>
                <Verified className="w-6 h-6 text-[#1DB954] absolute -bottom-1 -right-1 fill-current" />
              </div>
            ) : (
              <span className="text-5xl">🎤</span>
            )}
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1">Artist</p>
            <h1 className="text-5xl font-bold mb-2 flex items-center gap-2">
              {artist?.name || 'Loading...'}
              {artist?.verified && <Verified className="w-7 h-7 text-[#1DB954] fill-current" />}
            </h1>
            {artist?.bio && <p className="text-white/60 max-w-lg">{artist.bio}</p>}
            <p className="text-white/50 mt-2">{tracks.length} tracks</p>
            <button onClick={playAll} disabled={tracks.length === 0} className="mt-3 px-6 py-2.5 bg-[#1DB954] text-black font-semibold rounded-full hover:bg-[#1ed760] transition-all disabled:opacity-50 disabled:cursor-not-allowed">
              Play All
            </button>
          </div>
        </div>
      </div>

      {/* Tracks */}
      <div className="p-6">
        {isLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="space-y-2.5">
                <div className="skeleton-spotify aspect-square rounded-md" />
                <div className="skeleton-spotify h-3.5 w-3/4 rounded" />
                <div className="skeleton-spotify h-3 w-1/2 rounded" />
              </div>
            ))}
          </div>
        ) : tracks.length === 0 ? (
          <div className="text-center py-16 text-white/40">
            <p className="text-lg font-medium text-white/60">No tracks yet</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {tracks.map((t) => (
              <TrackCard
                key={t.id}
                track={t}
                isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                onPlay={() => setQueue(tracks, tracks.findIndex((tr) => tr.id === t.id))}
                onLike={() => handleLike(t)}
                downloading={downloading === t.id}
                onDownload={() => download(t.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
