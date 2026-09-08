import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../lib/api'
import { useSEO } from '../../hooks/useSEO'

export default function PlaylistView() {
  useSEO({ title: 'My Playlists', description: 'Manage your music playlists' })
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: ['playlists'],
    queryFn: async () => (await api.get('/v1/music/playlists')).data,
    staleTime: 60000,
  })
  const [title, setTitle] = useState('')
  const create = useMutation({
    mutationFn: async () => (await api.post('/v1/music/playlists', { title })).data,
    onSuccess: () => {
      setTitle('')
      qc.invalidateQueries({ queryKey: ['playlists'] })
    },
  })

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Header */}
      <div className="px-6 py-8 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <h1 className="text-4xl font-bold mb-2 animate-fade-in-up">My Playlists</h1>
        <p className="text-white/60 animate-fade-in-up">Create and manage your playlists</p>
      </div>

      <div className="p-6 space-y-6">
        {/* Create playlist */}
        <div className="glass-card p-4 animate-fade-in-up">
          <div className="flex gap-3">
            <input
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="Playlist name..."
              className="input flex-1 bg-[#282828] border-white/10 text-white placeholder-white/40"
            />
            <button
              onClick={() => create.mutate()}
              disabled={create.isPending || !title.trim()}
              className="btn-spotify disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {create.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>

        {/* Playlists grid */}
        {isLoading ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 animate-fade-in-up">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="skeleton-spotify aspect-square rounded-lg" />
                <div className="skeleton-spotify h-4 w-3/4 rounded" />
                <div className="skeleton-spotify h-3 w-1/2 rounded" />
              </div>
            ))}
          </div>
        ) : (data || []).length === 0 ? (
          <div className="text-center py-12 text-white/40 animate-fade-in-up">
            <p className="text-4xl mb-4">🎵</p>
            <p className="text-lg">No playlists yet</p>
            <p className="text-sm mt-2">Create your first playlist above</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 animate-fade-in-up">
            {(data || []).map((p: any) => (
              <div key={p.id} className="card-spotify p-4 group cursor-pointer" onClick={() => navigate(`/music/playlists/${p.id}`)}>
                <div className="aspect-square rounded-md bg-[#282828] flex items-center justify-center text-4xl mb-3 group-hover:scale-105 transition-transform">
                  🎵
                </div>
                <p className="font-semibold text-white truncate">{p.title}</p>
                <p className="text-xs text-white/60 mt-1">{p.tracks?.length || 0} tracks</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}