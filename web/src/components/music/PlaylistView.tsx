import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useState } from 'react'

export default function PlaylistView(){
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey:['playlists'], queryFn: async()=>(await api.get('/v1/music/playlists')).data })
  const [title,setTitle]=useState('')
  const create = useMutation({ mutationFn: async()=>(await api.post('/v1/music/playlists',{ title })).data, onSuccess: ()=>{ setTitle(''); qc.invalidateQueries({queryKey:['playlists']}) } })
  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-bold">Playlists</h2>
      <div className="flex gap-2"><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="New playlist" className="input flex-1"/><button onClick={()=>create.mutate()} className="btn-primary">Create</button></div>
      {(data||[]).map((p:any)=><div key={p.id} className="glass-card p-3"><p className="font-medium">{p.title}</p><p className="text-xs text-dark-400">{p.tracks?.length||0} tracks</p></div>)}
    </div>
  )
}
