import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useState } from 'react'

export default function AdsPanel(){
  const qc = useQueryClient()
  const { data: ads } = useQuery({ queryKey: ['admin-ads'], queryFn: async()=>(await api.get('/admin/ads')).data })
  const { data: cfg } = useQuery({ queryKey: ['admin-ads-cfg'], queryFn: async()=>(await api.get('/admin/ads/config')).data })
  const [title,setTitle]=useState('')
  const create = useMutation({ mutationFn: async()=>(await api.post('/admin/ads',{ title, duration:15 })).data, onSuccess: ()=>{ setTitle(''); qc.invalidateQueries({queryKey:['admin-ads']}) } })
  const saveCfg = useMutation({ mutationFn: async(p:any)=>(await api.put('/admin/ads/config',p)).data, onSuccess: ()=>qc.invalidateQueries({queryKey:['admin-ads-cfg']}) })
  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Ads Management</h2>
      {cfg && <div className="glass-card p-4 space-y-2">
        <label className="flex items-center gap-2"><input type="checkbox" checked={cfg.enabled} onChange={e=>saveCfg.mutate({enabled:e.target.checked})}/> Enabled</label>
        <label className="flex gap-2">Every N tracks <input type="number" value={cfg.every_n_tracks} onChange={e=>saveCfg.mutate({every_n_tracks:parseInt(e.target.value)})} className="input w-20"/></label>
        <label className="flex gap-2">Max/hour <input type="number" value={cfg.max_per_hour} onChange={e=>saveCfg.mutate({max_per_hour:parseInt(e.target.value)})} className="input w-20"/></label>
      </div>}
      <div className="flex gap-2"><input value={title} onChange={e=>setTitle(e.target.value)} placeholder="Ad title" className="input flex-1"/><button onClick={()=>create.mutate()} className="btn-primary">Add</button></div>
      <div className="space-y-2">{(ads||[]).map((a:any)=><div key={a.id} className="glass-card p-3 flex justify-between"><span>{a.title} ({a.duration}s)</span><span className={a.enabled?'text-emerald-400':'text-dark-400'}>{a.enabled?'enabled':'disabled'}</span></div>)}</div>
    </div>
  )
}
