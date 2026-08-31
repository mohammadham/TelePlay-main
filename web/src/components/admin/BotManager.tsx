import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function BotManager() {
  const qc = useQueryClient()
  const { data: bots, isLoading } = useQuery({
    queryKey: ['admin-bots'],
    queryFn: async () => (await api.get('/admin/bots')).data,
  })
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', token: '', purpose: 'HELPER', is_active: true })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ name: '', token: '', purpose: 'HELPER', is_active: true })

  const createMut = useMutation({
    mutationFn: async (d: any) => (await api.post('/admin/bots', d)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-bots'] }); setShowAdd(false); setForm({ name: '', token: '', purpose: 'HELPER', is_active: true }) }
  })

  const updateMut = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => (await api.put(`/admin/bots/${id}`, data)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-bots'] }); setEditingId(null) }
  })

  const deleteMut = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/admin/bots/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-bots'] })
  })

  const testMut = useMutation({
    mutationFn: async (id: number) => (await api.post(`/admin/bots/${id}/test`)).data,
    onSuccess: (res) => alert(res.message || 'Test sent!')
  })

  if (isLoading) return <div className="p-6">Loading bots...</div>

  const purposes = ['MAIN', 'HELPER', 'ADS', 'STORAGE']

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Bot Manager</h2>
        <button onClick={() => setShowAdd(true)} className="btn-primary">+ Add Bot</button>
      </div>

      {showAdd && (
        <div className="glass-card p-4 space-y-3">
          <h3 className="font-bold">Add New Bot</h3>
          <label className="flex flex-col gap-1"><span className="text-sm">Name *</span><input value={form.name} onChange={e => setForm({...form, name: e.target.value})} placeholder="main, helper_1, ads_bot" className="input" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">Token *</span><input type="password" value={form.token} onChange={e => setForm({...form, token: e.target.value})} placeholder="123456:ABC-DEF..." className="input" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">Purpose</span><select value={form.purpose} onChange={e => setForm({...form, purpose: e.target.value})} className="input">{purposes.map(p => <option key={p} value={p}>{p}</option>)}</select></label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={e => setForm({...form, is_active: e.target.checked})} /> Active</label>
          <div className="flex gap-2">
            <button onClick={() => createMut.mutate(form)} disabled={createMut.isPending} className="btn-primary">{createMut.isPending ? 'Adding...' : 'Add Bot'}</button>
            <button onClick={() => { setShowAdd(false); setForm({ name: '', token: '', purpose: 'HELPER', is_active: true }) }} className="btn-secondary">Cancel</button>
          </div>
          {createMut.isError && <div className="text-red-400 text-sm">Error: {createMut.error?.response?.data?.detail || createMut.error?.message}</div>}
        </div>
      )}

      <div className="space-y-3">
        {bots?.map((bot: any) => (
          <div key={bot.id} className="glass-card p-4 space-y-3">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <span className="font-mono text-lg">{bot.name}</span>
                <span className={`ml-2 px-2 py-0.5 rounded text-xs ${bot.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {bot.is_active ? 'Active' : 'Inactive'}
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-xs bg-primary-500/20 text-primary-400">{bot.purpose}</span>
                {bot.username && <span className="ml-2 text-dark-400">@{bot.username}</span>}
              </div>
              {editingId === bot.id ? (
                <div className="flex gap-2">
                  <button onClick={() => updateMut.mutate({ id: bot.id, data: editForm })} disabled={updateMut.isPending} className="btn-primary btn-sm">{updateMut.isPending ? 'Saving...' : 'Save'}</button>
                  <button onClick={() => setEditingId(null)} className="btn-secondary btn-sm">Cancel</button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button onClick={() => { setEditForm({ name: bot.name, token: '', purpose: bot.purpose, is_active: bot.is_active }); setEditingId(bot.id) }} className="btn-secondary btn-sm">Edit</button>
                  <button onClick={() => testMut.mutate(bot.id)} disabled={testMut.isPending} className="btn-primary btn-sm">{testMut.isPending ? 'Testing...' : 'Test'}</button>
                  <button onClick={() => { if (confirm(`Delete bot "${bot.name}"?`)) deleteMut.mutate(bot.id) }} className="btn-secondary btn-sm text-red-400 hover:bg-red-500/10">Delete</button>
                </div>
              )}
            </div>

            {editingId === bot.id && (
              <div className="space-y-2 pt-2 border-t border-white/10">
                <label className="flex flex-col gap-1"><span className="text-sm">Name</span><input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">New Token (leave empty to keep)</span><input type="password" value={editForm.token} onChange={e => setEditForm({...editForm, token: e.target.value})} placeholder="Optional: new token" className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">Purpose</span><select value={editForm.purpose} onChange={e => setEditForm({...editForm, purpose: e.target.value})} className="input">{purposes.map(p => <option key={p} value={p}>{p}</option>)}</select></label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.is_active} onChange={e => setEditForm({...editForm, is_active: e.target.checked})} /> Active</label>
              </div>
            )}

            {!editingId && bot.id && (
              <div className="text-xs text-dark-400 space-y-1">
                <div>Bot ID: {bot.bot_user_id}</div>
                <div>Rate limit: {bot.rate_limit_remaining}/sec</div>
                <div>Last used: {bot.last_used ? new Date(bot.last_used).toLocaleString() : 'Never'}</div>
                <div>Created: {new Date(bot.created_at).toLocaleString()}</div>
              </div>
            )}
          </div>
        ))}
        {!bots?.length && <div className="glass-card p-6 text-center text-dark-400">No bots configured yet. Click "Add Bot" to start.</div>}
      </div>
    </div>
  )
}