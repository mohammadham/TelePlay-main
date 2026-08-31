import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function CachePanel() {
  const qc = useQueryClient()
  const { data: cfg } = useQuery({ queryKey: ['admin-cache-cfg'], queryFn: async()=>(await api.get('/admin/cache/config')).data })
  const { data: stats } = useQuery({ queryKey: ['admin-cache-stats'], queryFn: async()=>(await api.get('/admin/cache/stats')).data })
  const mut = useMutation({ mutationFn: async (p:any)=>(await api.put('/admin/cache/config', p)).data, onSuccess: ()=>qc.invalidateQueries({ queryKey: ['admin-cache-cfg'] }) })
  const purge = useMutation({ mutationFn: async ()=>(await api.post('/admin/cache/purge', { scope: 'all' })).data, onSuccess: ()=>qc.invalidateQueries({ queryKey: ['admin-cache-stats'] }) })

  if (!cfg) return <div className="p-6">Loading cache config...</div>
  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h2 className="text-2xl font-bold">Cache Management</h2>
      <div className="glass-card p-4 grid grid-cols-2 gap-4 text-sm">
        <div>Used: <b>{stats?.used_mb ?? 0} / {stats?.max_mb ?? cfg.max_size_mb} MB</b></div>
        <div>Chunks: {stats?.cached_chunks ?? 0}</div>
        <div>Strategy: {cfg.strategy}</div>
        <div>Enabled: {cfg.enabled? 'Yes':'No'}</div>
      </div>
      <div className="glass-card p-4 space-y-3">
        <label className="flex flex-col gap-1">Max Size (MB)<input type="number" value={cfg.max_size_mb} onChange={e=>mut.mutate({ max_size_mb: parseInt(e.target.value) })} className="input" /></label>
        <label className="flex flex-col gap-1">Max File Size (MB)<input type="number" value={cfg.max_file_size_mb} onChange={e=>mut.mutate({ max_file_size_mb: parseInt(e.target.value) })} className="input" /></label>
        <label className="flex flex-col gap-1">Strategy<select value={cfg.strategy} onChange={e=>mut.mutate({ strategy: e.target.value })} className="input"><option value="lru">LRU</option><option value="lfu">LFU</option><option value="hybrid">Hybrid</option></select></label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={cfg.enabled} onChange={e=>mut.mutate({ enabled: e.target.checked })} /> Enabled</label>
      </div>
      <button onClick={()=>purge.mutate()} className="btn-secondary">Purge All Cache</button>
    </div>
  )
}
