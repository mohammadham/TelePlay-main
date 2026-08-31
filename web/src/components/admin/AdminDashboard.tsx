import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import CachePanel from './CachePanel'
import AdsPanel from './AdsPanel'

function StatCard({ label, value }: { label: string; value: any }) {
  return <div className="glass-card p-4 text-center"><div className="text-2xl font-bold">{value}</div><div className="text-xs text-dark-400">{label}</div></div>
}

export default function AdminDashboard() {
  const [tab, setTab] = useState<'overview'|'users'|'files'|'cache'|'ads'|'system'>('overview')
  const { data: stats } = useQuery({ queryKey: ['admin-stats'], queryFn: async()=>(await api.get('/admin/stats')).data, enabled: tab==='overview' })
  const { data: users } = useQuery({ queryKey: ['admin-users'], queryFn: async()=>(await api.get('/admin/users')).data, enabled: tab==='users' })
  const { data: files } = useQuery({ queryKey: ['admin-files'], queryFn: async()=>(await api.get('/admin/files')).data, enabled: tab==='files' })
  const { data: system } = useQuery({ queryKey: ['admin-system'], queryFn: async()=>(await api.get('/admin/system')).data, enabled: tab==='system' })

  return (
    <div className="min-h-screen bg-dark-950 text-white">
      <div className="border-b border-white/[0.06] bg-dark-900/50 backdrop-blur sticky top-0 z-10">
        <div className="px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold">Admin Panel</h1>
          <span className="text-xs text-dark-400">/admin — admin-only (ADMIN_TELEGRAM_IDS)</span>
        </div>
        <div className="flex gap-1 px-6 pb-3 overflow-x-auto">
          {(['overview','users','files','cache','ads','system'] as const).map(t=>(
            <button key={t} onClick={()=>setTab(t)} className={`px-3 py-1.5 rounded text-sm capitalize ${tab===t?'bg-primary-600 text-white':'bg-white/[0.06] hover:bg-white/[0.10]'}`}>{t}</button>
          ))}
        </div>
      </div>

      <div className="p-6">
        {tab==='overview' && (
          !stats ? <div>Loading...</div> : <div className="space-y-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Users" value={stats.users} />
              <StatCard label="Files" value={stats.files} />
              <StatCard label="Tracks" value={stats.tracks} />
              <StatCard label="Movies" value={stats.movies} />
              <StatCard label="Audio files" value={stats.files_audio} />
              <StatCard label="Video files" value={stats.files_video} />
              <StatCard label="Ads" value={stats.ads} />
              <StatCard label="Uptime (s)" value={stats.uptime_seconds} />
            </div>
            <div className="glass-card p-4 text-sm space-y-1">
              <div>Storage: {(stats.storage_bytes/1024/1024).toFixed(1)} MB</div>
              <div>Cache: {stats.cache.used_mb} / {stats.cache.max_mb} MB + Video {stats.cache.video_used_mb ?? 0}/{stats.cache.video_max_mb ?? 0} MB</div>
              <div>Python {stats.python} — {stats.platform}</div>
            </div>
          </div>
        )}
        {tab==='users' && (
          <div className="space-y-2">
            <h2 className="font-bold">Users ({users?.total ?? 0})</h2>
            {(users?.users || []).map((u:any)=><div key={u.id} className="glass-card p-3 flex justify-between text-sm"><span>{u.first_name || ''} @{u.username || ''} ({u.telegram_id})</span><span className="text-dark-400">{new Date(u.created_at).toLocaleDateString()}</span></div>)}
          </div>
        )}
        {tab==='files' && (
          <div className="space-y-2">
            <h2 className="font-bold">Files ({files?.total ?? 0})</h2>
            {(files?.files || []).map((f:any)=><div key={f.id} className="glass-card p-3 text-sm flex justify-between"><span>{f.file_name} [{f.file_type}]</span><span>{(f.file_size/1024/1024).toFixed(1)} MB</span></div>)}
          </div>
        )}
        {tab==='cache' && <CachePanel />}
        {tab==='ads' && <AdsPanel />}
        {tab==='system' && (
          !system ? <div>Loading...</div> : <div className="glass-card p-4 text-sm space-y-1 font-mono">
            <div>Disk total: {(system.disk_total/1024/1024/1024).toFixed(1)} GB</div>
            <div>Disk used: {(system.disk_used/1024/1024/1024).toFixed(1)} GB</div>
            <div>Disk free: {(system.disk_free/1024/1024/1024).toFixed(1)} GB</div>
            <div>Uptime: {Math.floor(system.uptime_seconds/60)} min</div>
            <div className="text-xs break-all">{system.python}</div>
          </div>
        )}
      </div>
    </div>
  )
}
