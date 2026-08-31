import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function AdminManager() {
  const qc = useQueryClient()
  const { data: admins, isLoading } = useQuery({
    queryKey: ['admin-admins'],
    queryFn: async () => (await api.get('/admin/admins')).data,
  })
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ telegram_id: '', role: 'ADMIN', can_manage_bots: false, can_manage_accounts: false, can_manage_admins: false, is_active: true })
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ role: 'ADMIN', can_manage_bots: false, can_manage_accounts: false, can_manage_admins: false, is_active: true })
  const [verifyId, setVerifyId] = useState('')

  const roles = ['SUPER_ADMIN', 'ADMIN', 'MODERATOR']

  const createMut = useMutation({
    mutationFn: async (d: any) => (await api.post('/admin/admins', d)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-admins'] }); setShowAdd(false); setForm({ telegram_id: '', role: 'ADMIN', can_manage_bots: false, can_manage_accounts: false, can_manage_admins: false, is_active: true }) }
  })

  const updateMut = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => (await api.put(`/admin/admins/${id}`, data)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-admins'] }); setEditingId(null) }
  })

  const deleteMut = useMutation({
    mutationFn: async (id: number) => (await api.delete(`/admin/admins/${id}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-admins'] })
  })

  const verifyMut = useMutation({
    mutationFn: async (id: number) => (await api.post('/admin/admins/verify-telegram-id', { telegram_id: id })).data,
    onSuccess: (res) => {
      if (res.valid) {
        setForm(prev => ({ ...prev, telegram_id: res.telegram_id.toString() }))
        alert(`✅ Verified: @${res.username || 'N/A'} (${res.first_name || ''} ${res.last_name || ''})`)
      } else {
        alert(`❌ Not found: ${res.error}`)
      }
    }
  })

  if (isLoading) return <div className="p-6">Loading admins...</div>

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Admin Manager</h2>
        <button onClick={() => setShowAdd(true)} className="btn-primary">+ Add Admin</button>
      </div>

      {showAdd && (
        <div className="glass-card p-4 space-y-3">
          <h3 className="font-bold">Add New Admin</h3>
          <label className="flex flex-col gap-1"><span className="text-sm">Telegram ID *</span><input type="number" value={form.telegram_id} onChange={e => setForm({...form, telegram_id: e.target.value})} placeholder="123456789" className="input" /></label>
          <div className="flex gap-2">
            <button onClick={() => verifyMut.mutate(parseInt(form.telegram_id))} disabled={verifyMut.isPending || !form.telegram_id} className="btn-secondary">{verifyMut.isPending ? 'Verifying...' : 'Verify ID'}</button>
            <button onClick={() => setVerifyId(form.telegram_id)} disabled={!form.telegram_id} className="btn-secondary" style={{opacity: verifyId === form.telegram_id ? 0.5 : 1}}>Verified: {verifyId === form.telegram_id ? '✅' : '❌'}</button>
          </div>
          <label className="flex flex-col gap-1"><span className="text-sm">Role</span><select value={form.role} onChange={e => setForm({...form, role: e.target.value})} className="input">{roles.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
          <div className="space-y-2">
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_bots} onChange={e => setForm({...form, can_manage_bots: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> Manage Bots</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_accounts} onChange={e => setForm({...form, can_manage_accounts: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> Manage Accounts</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_admins} onChange={e => setForm({...form, can_manage_admins: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> Manage Admins (SUPER_ADMIN only)</label>
          </div>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={e => setForm({...form, is_active: e.target.checked})} /> Active</label>
          <div className="flex gap-2">
            <button onClick={() => { if (verifyId !== form.telegram_id) return alert('Please verify Telegram ID first'); createMut.mutate({ ...form, telegram_id: parseInt(form.telegram_id) }) }} disabled={createMut.isPending || verifyId !== form.telegram_id} className="btn-primary">{createMut.isPending ? 'Adding...' : 'Add Admin'}</button>
            <button onClick={() => { setShowAdd(false); setForm({ telegram_id: '', role: 'ADMIN', can_manage_bots: false, can_manage_accounts: false, can_manage_admins: false, is_active: true }); setVerifyId('') }} className="btn-secondary">Cancel</button>
          </div>
          {createMut.isError && <div className="text-red-400 text-sm">Error: {createMut.error?.response?.data?.detail || createMut.error?.message}</div>}
        </div>
      )}

      <div className="space-y-3">
        {admins?.map((admin: any) => (
          <div key={admin.id} className="glass-card p-4 space-y-3">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <span className="font-mono text-lg">
                  {admin.first_name || ''} {admin.last_name || ''}
                  {admin.username && <span className="ml-2 text-primary-400">@{admin.username}</span>}
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-xs font-bold 
                  {admin.role === 'SUPER_ADMIN' ? 'bg-purple-500/20 text-purple-400' : 
                   admin.role === 'ADMIN' ? 'bg-blue-500/20 text-blue-400' : 
                   'bg-gray-500/20 text-gray-400'}">
                  {admin.role}
                </span>
                <span className={`ml-2 px-2 py-0.5 rounded text-xs ${admin.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {admin.is_active ? 'Active' : 'Inactive'}
                </span>
                {admin.id === admin.id && admin.role === 'SUPER_ADMIN' && admin.can_manage_admins && (
                  <span className="ml-2 px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-400">👑 Owner</span>
                )}
              </div>
              {editingId === admin.id ? (
                <div className="flex gap-2">
                  <button onClick={() => updateMut.mutate({ id: admin.id, data: editForm })} disabled={updateMut.isPending} className="btn-primary btn-sm">{updateMut.isPending ? 'Saving...' : 'Save'}</button>
                  <button onClick={() => setEditingId(null)} className="btn-secondary btn-sm">Cancel</button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button onClick={() => { setEditForm({ role: admin.role, can_manage_bots: admin.can_manage_bots, can_manage_accounts: admin.can_manage_accounts, can_manage_admins: admin.can_manage_admins, is_active: admin.is_active }); setEditingId(admin.id) }} className="btn-secondary btn-sm" disabled={admin.id === admin.id && admin.role === 'SUPER_ADMIN' && admin.can_manage_admins}>Edit</button>
                  <button onClick={() => { if (admin.id === admin.id && admin.role === 'SUPER_ADMIN' && admin.can_manage_admins) return alert('Cannot delete yourself'); if (confirm(`Delete admin ${admin.telegram_id}?`)) deleteMut.mutate(admin.id) }} className="btn-secondary btn-sm text-red-400 hover:bg-red-500/10" disabled={admin.id === admin.id && admin.role === 'SUPER_ADMIN' && admin.can_manage_admins}>Delete</button>
                </div>
              )}
            </div>

            {editingId === admin.id && (
              <div className="space-y-2 pt-2 border-t border-white/10">
                <label className="flex flex-col gap-1"><span className="text-sm">Role</span><select value={editForm.role} onChange={e => setEditForm({...editForm, role: e.target.value})} className="input" disabled={admin.role === 'SUPER_ADMIN' && admin.can_manage_admins && admin.id === admin.id}>{roles.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
                <div className="space-y-1">
                  <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_bots} onChange={e => setEditForm({...editForm, can_manage_bots: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> Manage Bots</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_accounts} onChange={e => setEditForm({...editForm, can_manage_accounts: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> Manage Accounts</label>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_admins} onChange={e => setEditForm({...editForm, can_manage_admins: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> Manage Admins</label>
                </div>
                <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.is_active} onChange={e => setEditForm({...editForm, is_active: e.target.checked})} /> Active</label>
              </div>
            )}

            {!editingId && (
              <div className="text-xs text-dark-400 space-y-1">
                <div>Telegram ID: {admin.telegram_id}</div>
                <div>Permissions: {admin.can_manage_bots ? '🤖 Bots' : ''} {admin.can_manage_accounts ? ' 👤 Accounts' : ''} {admin.can_manage_admins ? ' 👑 Admins' : ''}</div>
                <div>Created by: {admin.created_by || 'N/A'}</div>
                <div>Created: {new Date(admin.created_at).toLocaleString()}</div>
                <div>Last login: {admin.last_login ? new Date(admin.last_login).toLocaleString() : 'Never'}</div>
              </div>
            )}
          </div>
        ))}
        {!admins?.length && <div className="glass-card p-6 text-center text-dark-400">No admins configured.</div>}
      </div>
    </div>
  )
}