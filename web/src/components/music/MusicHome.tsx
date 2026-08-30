import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'

export default function MusicHome() {
  const { data: tracks } = useQuery({ queryKey: ['music-tracks'], queryFn: async () => (await api.get('/v1/music/tracks?per_page=20')).data })
  const { data: artists } = useQuery({ queryKey: ['music-artists'], queryFn: async () => (await api.get('/v1/music/artists')).data })
  const { setQueue, setCurrent } = useMusicStore()

  const list: any[] = Array.isArray(tracks) ? tracks : []
  const like = async (id: number) => { try{ await api.post(`/v1/music/likes/${id}`)}catch{} }

  return (
    <div className="p-6 pb-28 space-y-8">
      <section>
        <h2 className="text-2xl font-bold mb-4">Recently Added</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {list.map((t, idx) => (
            <TrackCard key={t.id} track={t} onPlay={()=>setQueue(list, idx)} onLike={()=>like(t.id)} />
          ))}
          {list.length===0 && <p className="text-dark-400 col-span-full">No tracks yet — ask admin to upload via bot.</p>}
        </div>
      </section>
      <section>
        <h2 className="text-xl font-bold mb-3">Popular Artists</h2>
        <div className="flex gap-4 overflow-x-auto no-scrollbar pb-2">
          {(artists||[]).map((a:any)=>(
            <div key={a.id} className="min-w-[120px] text-center">
              <div className="w-28 h-28 rounded-full bg-dark-800 flex items-center justify-center text-2xl mx-auto">🎤</div>
              <p className="text-sm mt-2 truncate">{a.name}</p>
            </div>
          ))}
        </div>
      </section>
      {/* Ad banner placeholder */}
      <div className="glass-card p-4 text-center text-sm text-dark-400">Ad slot — banner (یک تانت / AdMob) — will show when ADS_ENABLED</div>
    </div>
  )
}
