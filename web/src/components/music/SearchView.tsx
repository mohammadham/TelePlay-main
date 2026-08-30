import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'

export default function SearchView(){
  const [q,setQ]=useState('')
  const { data } = useQuery({ queryKey:['music-search',q], queryFn: async()=>(await api.get('/v1/music/search',{ params:{ q }})).data, enabled: q.length>=2 })
  const { setQueue } = useMusicStore()
  const tracks = data?.tracks || []
  return (
    <div className="p-6">
      <input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search tracks, artists, albums..." className="input w-full mb-4" dir="auto" />
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {tracks.map((t:any,idx:number)=><TrackCard key={t.id} track={t} onPlay={()=>setQueue(tracks,idx)} />)}
      </div>
      {q && tracks.length===0 && <p className="text-dark-400 mt-4">No results</p>}
    </div>
  )
}
