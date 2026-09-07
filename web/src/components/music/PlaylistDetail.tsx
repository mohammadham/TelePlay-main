import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useParams, useNavigate } from 'react-router-dom'
import { api, MusicTrack } from '../../lib/api'
import { useMusicStore } from '../../lib/musicStore'
import { ArrowLeft, Plus, Trash2, Play } from 'lucide-react'

export default function PlaylistDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { setQueue } = useMusicStore()
  const [showAdd, setShowAdd] = useState(false)
  const [searchQ, setSearchQ] = useState('')

  const { data: playlist, isLoading } = useQuery({
    queryKey: ['playlist', id],
    queryFn: async () => (await api.get(`/v1/music/playlists/${id}`)).data,
    enabled: !!id,
  })

  const { data: searchResults } = useQuery({
    queryKey: ['music-search', searchQ],
    queryFn: async () => (await api.get<any>('/v1/music/search', { params: { q: searchQ } })).data,
    enabled: showAdd && searchQ.length >= 2,
    staleTime: 30_000,
  })

  const addToPlaylist = useMutation({
    mutationFn: async (trackId: number) => {
      await api.post(`/v1/music/playlists/${id}/tracks/${trackId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['playlist', id] })
      setShowAdd(false)
      setSearchQ('')
    },
  })

  const removeFromPlaylist = useMutation({
    mutationFn: async (trackId: number) => {
      await api.delete(`/v1/music/playlists/${id}/tracks/${trackId}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['playlist', id] })
    },
  })

  const tracks: MusicTrack[] = playlist?.tracks || []

  const playAll = () => {
    if (tracks.length > 0) setQueue(tracks, 0)
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Header */}
      <div className="px-6 py-6 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <button onClick={() => navigate('/music/playlists')} className="flex items-center gap-2 text-white/60 hover:text-white mb-4 transition-colors">
          <ArrowLeft className="w-5 h-5" />
          Back
        </button>
        <div className="flex items-end gap-6">
          <div className="w-40 h-40 rounded-lg bg-[#282828] flex items-center justify-center text-6xl shadow-2xl">
            🎵
          </div>
          <div className="flex-1">
            <p className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1">Playlist</p>
            <h1 className="text-5xl font-bold mb-3">{playlist?.title || 'Loading...'}</h1>
            <p className="text-white/60 mb-4">{tracks.length} tracks</p>
            <button onClick={playAll} disabled={tracks.length === 0} className="w-14 h-14 rounded-full bg-[#1DB954] flex items-center justify-center hover:scale-105 hover:bg-[#1ed760] transition-all shadow-xl disabled:opacity-50 disabled:cursor-not-allowed">
              <Play className="w-7 h-7 fill-black text-black ml-1" />
            </button>
          </div>
        </div>
      </div>

      <div className="p-6 space-y-4">
        {/* Add track button */}
        <div className="flex justify-end">
          <button onClick={() => setShowAdd(!showAdd)} className="flex items-center gap-2 px-4 py-2 bg-[#282828] hover:bg-[#303030] rounded-full text-sm font-medium transition-colors">
            <Plus className="w-4 h-4" />
            Add Track
          </button>
        </div>

        {/* Search for tracks to add */}
        {showAdd && (
          <div className="max-w-xl">
            <input
              value={searchQ}
              onChange={(e) => setSearchQ(e.target.value)}
              placeholder="Search tracks to add..."
              className="w-full bg-[#282828] border border-white/10 rounded-full px-6 py-3 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
              autoFocus
            />
            {searchResults?.tracks && searchResults.tracks.length > 0 && (
              <div className="mt-2 space-y-1 max-h-60 overflow-y-auto">
                {searchResults.tracks.slice(0, 10).map((t: MusicTrack) => (
                  <button
                    key={t.id}
                    onClick={() => addToPlaylist.mutate(t.id)}
                    disabled={addToPlaylist.isPending}
                    className="w-full flex items-center gap-3 p-2 rounded hover:bg-[#282828] text-left transition-colors"
                  >
                    <img src={t.cover_url ?? ''} alt="" className="w-10 h-10 rounded object-cover" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{t.title}</p>
                      <p className="text-xs text-white/50 truncate">{t.artist?.name}</p>
                    </div>
                    <Plus className="w-4 h-4 text-[#1DB954]" />
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Track list */}
        {isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 p-3 rounded-lg bg-[#181818] animate-pulse">
                <div className="w-10 h-10 bg-[#282828] rounded" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-[#282828] rounded w-1/3" />
                  <div className="h-3 bg-[#282828] rounded w-1/4" />
                </div>
              </div>
            ))}
          </div>
        ) : tracks.length === 0 ? (
          <div className="text-center py-12 text-white/40">
            <p className="text-4xl mb-3">🎵</p>
            <p className="text-lg font-medium text-white/60">This playlist is empty</p>
            <p className="text-sm mt-1">Add some tracks to get started</p>
          </div>
        ) : (
          <div className="space-y-1">
            {tracks.map((t, idx) => (
              <div key={t.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-[#181818] group transition-colors">
                <span className="text-white/40 text-sm w-6 text-center">{idx + 1}</span>
                <img src={t.cover_url ?? ''} alt="" className="w-10 h-10 rounded object-cover" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{t.title}</p>
                  <p className="text-sm text-white/50 truncate">{t.artist?.name}</p>
                </div>
                <button
                  onClick={() => setQueue(tracks, idx)}
                  className="opacity-0 group-hover:opacity-100 text-[#1DB954] hover:scale-110 transition-all"
                >
                  <Play className="w-5 h-5 fill-current" />
                </button>
                <button
                  onClick={() => removeFromPlaylist.mutate(t.id)}
                  className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300 transition-colors"
                  title="Remove"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
