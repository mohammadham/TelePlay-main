import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useState, useEffect } from 'react'

export default function SettingsPanel(){
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey:['admin-settings'], queryFn: async()=>(await api.get('/admin/settings')).data })
  const [values, setValues] = useState<Record<string,string>>({})
  useEffect(()=>{ if(data){ const m:Record<string,string>={}; data.forEach((r:any)=>m[r.key]=r.value); setValues(m)} },[data])
  const save = useMutation({ mutationFn: async()=>(await api.put('/admin/settings', values)).data, onSuccess: ()=>qc.invalidateQueries({queryKey:['admin-settings']}) })
  const seed = useMutation({ mutationFn: async()=>(await api.post('/admin/settings/seed')).data, onSuccess: ()=>qc.invalidateQueries({queryKey:['admin-settings']}) })
  const exp = useQuery({ queryKey:['admin-settings-export'], queryFn: async()=>(await api.get('/admin/settings/export')).data, enabled:false })
  if(!data) return <div className="p-6">Loading settings...</div>
  return (
    <div className="p-6 space-y-4 max-w-3xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Environment Template (Admin)</h2>
        <div className="flex gap-2">
          <button onClick={()=>seed.mutate()} className="btn-secondary text-sm">Seed template</button>
          <button onClick={()=>exp.refetch().then(r=>navigator.clipboard.writeText(r.data?.env || ''))} className="btn-secondary text-sm">Copy .env</button>
        </div>
      </div>
      <p className="text-xs text-dark-400">این مقادیر فعلاً template در DB هستند — برای اعمال واقعی باید هاست ENV را هم ست کنید (یا بعداً auto-reload اضافه می‌شود). فعلاً یک مقدار تمپلیت دارد.</p>
      <div className="space-y-3">
        {data.map((row:any)=>(
          <label key={row.key} className="flex flex-col gap-1">
            <span className="text-sm font-medium">{row.key} <span className="text-xs text-dark-500">— {row.description}</span></span>
            <input value={values[row.key]||''} onChange={e=>setValues({...values, [row.key]: e.target.value})} className="input" placeholder={row.key} />
          </label>
        ))}
      </div>
      <button onClick={()=>save.mutate()} className="btn-primary">Save</button>
      {exp.data?.env && <pre className="glass-card p-3 text-xs overflow-auto max-h-60">{exp.data.env}</pre>}
    </div>
  )
}
