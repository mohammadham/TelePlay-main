import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { api, MusicTrack, useToggleLike, useMusicHistory } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'
import { Play, Shuffle, Clock, Filter } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useSEO } from '../../hooks/useSEO'

type MediaType = 'all' | 'music_video' | 'reel'

const MEDIA_TABS: { key: MediaType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'music_video', label: 'Music Videos' },
  { key: 'reel', label: 'Reels' },
]

export default function MusicHome() {
  useSEO({ title: 'Music Home', description: 'Browse and listen to your music library' })
  const [mediaType, setMediaType] = useState<MediaType>('all')
  const [genre, setGenre] = useState<string>('')
  const navigate = useNavigate()
  const { data: tracks, isLoading } = useQuery({
    queryKey: ['music-tracks', mediaType, genre],
    queryFn: async () => {
      const params: Record<string, string | number> = { per_page: 50 }
      if (mediaType !== 'all') params.media_type = mediaType
      if (genre) params.genre = genre
      return (await api.get<MusicTrack[]>('/v1/music/tracks', { params })).data
    },
    staleTime: 60000,
  })
  const { data: artists, isLoading: artistsLoading } = useQuery({
    queryKey: ['music-artists'],
    queryFn: async () => (await api.get<any[]>('/v1/music/artists')).data,
    staleTime: 120000,
  })
  const { setQueue, setShuffle } = useMusicStore()
  const { setPreviewFile } = useAppStore()
  const qc = useQueryClient()
  const [downloading, setDownloading] = useState<number | null>(null)
  const toggleLike = useToggleLike()
  const { data: history, isLoading: historyLoading } = useMusicHistory(50)

  const list: MusicTrack[] = Array.isArray(tracks) ? tracks : []

  const handleLike = async (track: MusicTrack) => {
    try {
      await toggleLike.mutateAsync({ trackId: track.id, liked: track.is_liked })
      await qc.invalidateQueries({ queryKey: ['music-tracks', mediaType] })
    } catch (e) {
      console.error('Like failed:', e)
    }
  }

  const download = async (id: number) => {
    setDownloading(id)
    try { await api.post('/v1/music/downloads', { track_id: id }) }
    catch (e) {
      console.error('Download failed:', e)
    }
    setDownloading(null)
  }

  const playTrack = (track: MusicTrack) => {
    if (track.media_type === 'music_video' || track.media_type === 'reel') {
      api.get(`/files/${track.file_id}`).then(r => {
        const file = r.data
        setPreviewFile(file as any)
      }).catch(console.error)
    } else {
      setQueue(list, list.findIndex((t) => t.id === track.id))
    }
  }

  const handleShuffle = () => {
    setShuffle(true)
    setQueue(list, Math.floor(Math.random() * list.length))
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Hero section */}
      <div className="relative h-72 bg-gradient-to-b from-[#1DB954] via-[#1DB954]/40 to-[#121212] flex items-end px-6 pb-6">
        <div className="animate-fade-in-up w-full max-w-xl">
          <p className="text-xs font-medium text-white/70 uppercase tracking-[0.2em] mb-2">Your Library</p>
          <h1 className="text-5xl font-bold mb-5 leading-tight">
            Good Evening
          </h1>
          <div className="flex items-center gap-4">
            <button className="w-14 h-14 rounded-full bg-[#1DB954] flex items-center justify-center hover:scale-105 hover:bg-[#1ed760] transition-all shadow-xl" onClick={() => setQueue(list, 0)}>
              <Play className="w-7 h-7 fill-black text-black ml-1" />
            </button>
            <button className="w-14 h-14 rounded-full bg-[#1DB954] flex items-center justify-center hover:scale-105 hover:bg-[#1ed760] transition-all shadow-xl" onClick={handleShuffle}>
              <Shuffle className="w-7 h-7 fill-black text-black" />
            </button>
            <button className="border border-white/30 text-white px-6 py-2.5 rounded-full text-sm font-semibold hover:bg-white/10 transition-all" onClick={() => navigate('/music/search')}>
              Explore More
            </button>
          </div>
        </div>
      </div>

      {/* Media type tabs + genre filter */}
      <div className="px-6 py-4 flex gap-3 flex-wrap items-center">
        {MEDIA_TABS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setMediaType(key)}
            className={`px-5 py-2 rounded-full text-sm font-semibold transition-all duration-200 ${
              mediaType === key
                ? 'bg-[#1DB954] text-black'
                : 'bg-white/10 text-white/70 hover:bg-white/15 hover:text-white'
            }`}
          >
            {label}
          </button>
        ))}
        <div className="ml-auto relative">
          <select
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            className="appearance-none bg-white/10 text-white/70 px-4 py-2 rounded-full text-sm font-semibold pr-8 hover:bg-white/15 hover:text-white transition-all cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
          >
            <option value="" className="bg-[#121212]">All Genres</option>
            <option value="pop" className="bg-[#121212]">Pop</option>
            <option value="rock" className="bg-[#121212]">Rock</option>
            <option value="hip-hop" className="bg-[#121212]">Hip Hop</option>
            <option value="jazz" className="bg-[#121212]">Jazz</option>
            <option value="classical" className="bg-[#121212]">Classical</option>
            <option value="electronic" className="bg-[#121212]">Electronic</option>
            <option value="indie" className="bg-[#121212]">Indie</option>
            <option value="rnb" className="bg-[#121212]">R&B</option>
          </select>
          <Filter className="w-4 h-4 text-white/40 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      <div className="px-6 space-y-10">
        {/* Featured Artists */}
        <section className="animate-fade-in-up">
          <h2 className="text-xl font-bold mb-5">Featured Artists</h2>
          {artistsLoading ? (
            <div className="flex gap-5 overflow-x-auto no-scrollbar pb-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="min-w-[110px] text-center space-y-3">
                  <div className="skeleton-spotify w-28 h-28 rounded-full mx-auto" />
                  <div className="skeleton-spotify h-3.5 w-20 mx-auto rounded" />
                </div>
              ))}
            </div>
          ) : (
            <div className="flex gap-5 overflow-x-auto no-scrollbar pb-2">
              {(artists || []).map((a: any) => (
                <div key={a.id} onClick={() => navigate(`/music/artists/${a.id}`)} className="min-w-[110px] text-center cursor-pointer group flex flex-col items-center">
                  <div className="w-28 h-28 rounded-full overflow-hidden bg-[#282828] flex items-center justify-center group-hover:ring-2 ring-[#1DB954] transition-all duration-200">
                    {a.avatar_url ? (
                      <img
                        src={a.avatar_url}
                        alt={a.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <span className="text-3xl opacity-50">🎤</span>
                    )}
                  </div>
                  <p className="text-sm font-semibold mt-3 text-white truncate w-full px-1 group-hover:text-[#1DB954] transition-colors">
                    {a.name}
                  </p>
                  <p className="text-xs text-white/50">Artist</p>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Recently Added / filtered tracks */}
        <section className="animate-fade-in-up">
          <h2 className="text-xl font-bold mb-5">
            {mediaType === 'all' ? 'Recently Added' : mediaType === 'music_video' ? 'Music Videos' : 'Reels'}
          </h2>
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
          ) : list.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-white/30">
              <div className="text-6xl mb-4">🎵</div>
              <p className="text-lg font-medium text-white/50">
                No {mediaType === 'all' ? 'tracks' : mediaType === 'music_video' ? 'music videos' : 'reels'} yet
              </p>
              <p className="text-sm mt-2 text-white/30">Ask admin to upload via bot</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {list.map((t) => (
                <TrackCard
                  key={t.id}
                  track={t}
                  isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                  onPlay={() => playTrack(t)}
                  onLike={() => handleLike(t)}
                  downloading={downloading === t.id}
                  onDownload={() => download(t.id)}
                />
              ))}
            </div>
          )}
        </section>

        {/* Continue Listening */}
        <section className="animate-fade-in-up">
          <h2 className="text-xl font-bold mb-5 flex items-center gap-2">
            <Clock className="w-5 h-5 text-[#1DB954]" />
            Continue Listening
          </h2>
          {historyLoading ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="space-y-2.5">
                  <div className="skeleton-spotify aspect-square rounded-md" />
                  <div className="skeleton-spotify h-3.5 w-3/4 rounded" />
                  <div className="skeleton-spotify h-3 w-1/2 rounded" />
                </div>
              ))}
            </div>
          ) : Array.isArray(history) && history.length > 0 ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
              {history.slice(0, 8).map((item: any) => (
                <TrackCard
                  key={item.track_id ?? item.id}
                  track={item}
                  isVideo={item.media_type === 'music_video' || item.media_type === 'reel'}
                  onPlay={() => playTrack(item)}
                  onLike={() => item.is_liked && handleLike(item)}
                />
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-white/30">
              <p className="text-lg font-medium text-white/50">Nothing played yet</p>
              <p className="text-sm mt-2">Start listening to see your history</p>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
