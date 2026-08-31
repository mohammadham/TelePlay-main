import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function Downloads(){
  const { data } = useQuery({ queryKey:['downloads'], queryFn: async()=>(await api.get('/v1/music/downloads')).data.catch(()=>[]) })
  const list = Array.isArray(data)? data : []
  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Downloads</h2>
      {list.length===0 ? <p className="text-dark-400">No downloads yet. Tap Download on any track.</p> : list.map((d:any)=><div key={d.id} className="glass-card p-3 mb-2">{d.track?.title} — {d.status} {d.progress}%</div>)}
    </div>
  )
}
