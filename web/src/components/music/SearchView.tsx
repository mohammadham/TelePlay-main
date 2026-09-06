import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api, MusicTrack } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'

export default function SearchView() {
  const [q, setQ] = useState('')
  const { setQueue } = useMusicStore()
  const { setPreviewFile } = useAppStore()

  const { data } = useQuery({
    queryKey: ['music-search', q],
    queryFn: async () => (await api.get<any>('/v1/music/search', { params: { q } })).data,
    enabled: q.length >= 2,
    staleTime: 30000,
  })

  const tracks: MusicTrack[] = data?.tracks || []

  const playTrack = (track: MusicTrack, index: number) => {
    if (track.media_type === 'music_video' || track.media_type === 'reel') {
      api.get(`/files/${track.file_id}`).then((r) => {
        setPreviewFile(r.data as any)
      }).catch(() => {})
    } else {
      setQueue(tracks, index)
    }
  }

  return (
    <div className="bg-[#121212] min-h-screen text-white p-6 pb-28">
      <input
        value={q}
        onChange={e => setQ(e.target.value)}
        placeholder="Search tracks, artists, albums..."
        className="input w-full mb-4"
        dir="auto"
      />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {tracks.map((t, idx) => (
          <TrackCard
            key={t.id}
            track={t}
            isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
            onPlay={() => playTrack(t, idx)}
          />
        ))}
      </div>
      {q && tracks.length === 0 && <p className="text-dark-400 mt-4">No results</p>}
    </div>
  )
}
