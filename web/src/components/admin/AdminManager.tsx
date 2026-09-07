import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

function SkeletonRow() {
  return (
    <div className="glass-card p-4 animate-pulse">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex-1 min-w-[200px] space-y-2">
          <div className="skeleton h-5 w-48" />
          <div className="flex gap-2">
            <div className="skeleton h-5 w-16 rounded-full" />
            <div className="skeleton h-5 w-12 rounded-full" />
          </div>
        </div>
        <div className="flex gap-2">
          <div className="skeleton h-8 w-16 rounded" />
          <div className="skeleton h-8 w-16 rounded" />
        </div>
      </div>
    </div>
  )
}

export default function AdminManager() {
  const qc = useQueryClient()
  const { data: admins, isLoading } = useQuery({
    queryKey: ['admin-admins'],
    queryFn: async () => (await api.get('/admin/admins')).data,
    staleTime: 10_000,
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

  return (
    <div className="space-y-6 max-w-4xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold text-white/90">مدیران</h2>
        <button onClick={() => setShowAdd(true)} className="btn-primary text-sm py-1.5 px-4">
          + افزودن مدیر
        </button>
      </div>

      {showAdd && (
        <div className="glass-card p-4 space-y-3">
          <h3 className="font-bold text-white/90">افزودن مدیر جدید</h3>
          <label className="flex flex-col gap-1"><span className="text-sm text-dark-400">شناسه تلگرام *</span><input type="number" value={form.telegram_id} onChange={e => setForm({...form, telegram_id: e.target.value})} placeholder="123456789" className="input" /></label>
          <div className="flex gap-2">
            <button onClick={() => verifyMut.mutate(parseInt(form.telegram_id))} disabled={verifyMut.isPending || !form.telegram_id} className="btn-secondary text-sm">{verifyMut.isPending ? 'در حال بررسی...' : 'بررسی هویت'}</button>
            <button onClick={() => setVerifyId(form.telegram_id)} disabled={!form.telegram_id} className="btn-secondary text-sm" style={{opacity: verifyId === form.telegram_id ? 0.5 : 1}}>شناسه تأیید شده: {verifyId === form.telegram_id ? '✅' : '❌'}</button>
          </div>
          <label className="flex flex-col gap-1"><span className="text-sm text-dark-400">نقش</span><select value={form.role} onChange={e => setForm({...form, role: e.target.value})} className="input">{roles.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
          <div className="space-y-2">
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_bots} onChange={e => setForm({...form, can_manage_bots: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> مدیریت ربات‌ها</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_accounts} onChange={e => setForm({...form, can_manage_accounts: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> مدیریت حساب‌ها</label>
            <label className="flex items-center gap-2"><input type="checkbox" checked={form.can_manage_admins} onChange={e => setForm({...form, can_manage_admins: e.target.checked})} disabled={form.role === 'SUPER_ADMIN'} /> مدیریت مدیران (فقط سوپر)</label>
          </div>
          <label className="flex items-center gap-2"><input type="checkbox" checked={form.is_active} onChange={e => setForm({...form, is_active: e.target.checked})} /> فعال</label>
          <div className="flex gap-2">
            <button onClick={() => { if (verifyId !== form.telegram_id) return alert('لطفاً ابتدا شناسه تلگرام را تأیید کنید'); createMut.mutate({ ...form, telegram_id: parseInt(form.telegram_id) }) }} disabled={createMut.isPending || verifyId !== form.telegram_id} className="btn-primary text-sm">{createMut.isPending ? 'در حال افزودن...' : 'افزودن مدیر'}</button>
            <button onClick={() => { setShowAdd(false); setForm({ telegram_id: '', role: 'ADMIN', can_manage_bots: false, can_manage_accounts: false, can_manage_admins: false, is_active: true }); setVerifyId('') }} className="btn-secondary text-sm">انصراف</button>
          </div>
          {createMut.isError && <div className="text-red-400 text-sm">خطا: {createMut.error?.response?.data?.detail || createMut.error?.message}</div>}
        </div>
      )}

      <div className="space-y-3">
        {isLoading ? (
          <>
            <SkeletonRow />
            <SkeletonRow />
          </>
        ) : admins?.length ? (
          admins.map((admin: any) => (
            <div key={admin.id} className="glass-card p-4 space-y-3 transition-all hover:bg-dark-800/40">
              <div className="flex flex-wrap items-center gap-4">
                <div className="flex-1 min-w-[200px]">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-base text-white/90 font-medium">
                      {admin.first_name || ''} {admin.last_name || ''}
                      {admin.username && <span className="mr-2 text-primary-400">@{admin.username}</span>}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-bold ${
                      admin.role === 'SUPER_ADMIN' ? 'bg-purple-500/20 text-purple-300' :
                      admin.role === 'ADMIN' ? 'bg-blue-500/20 text-blue-300' :
                      'bg-gray-500/20 text-gray-400'
                    }`}>
                      {admin.role}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-xs ${admin.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-red-500/20 text-red-300'}`}>
                      {admin.is_active ? 'فعال' : 'غیرفعال'}
                    </span>
                    {admin.is_owner && (
                      <span className="px-2 py-0.5 rounded-full text-xs bg-yellow-500/20 text-yellow-300">👑 شما</span>
                    )}
                  </div>
                </div>
                {editingId === admin.id ? (
                  <div className="flex gap-2">
                    <button onClick={() => updateMut.mutate({ id: admin.id, data: editForm })} disabled={updateMut.isPending} className="btn-primary btn-sm">{updateMut.isPending ? 'ذخیره...' : 'ذخیره'}</button>
                    <button onClick={() => setEditingId(null)} className="btn-secondary btn-sm">انصراف</button>
                  </div>
                ) : (
                  <div className="flex gap-2">
                    <button onClick={() => { setEditForm({ role: admin.role, can_manage_bots: admin.can_manage_bots, can_manage_accounts: admin.can_manage_accounts, can_manage_admins: admin.can_manage_admins, is_active: admin.is_active }); setEditingId(admin.id) }} className="btn-secondary btn-sm" disabled={admin.is_owner}>ویرایش</button>
                    <button onClick={() => { if (admin.is_owner) return alert('نمی‌توانید خودتان را حذف کنید'); if (confirm(`حذف مدیر ${admin.telegram_id}?`)) deleteMut.mutate(admin.id) }} className="btn-secondary btn-sm text-red-400 hover:bg-red-500/10" disabled={admin.is_owner}>حذف</button>
                  </div>
                )}
              </div>

              {editingId === admin.id && (
                <div className="space-y-2 pt-2 border-t border-white/[0.06]">
                  <label className="flex flex-col gap-1"><span className="text-sm text-dark-400">نقش</span><select value={editForm.role} onChange={e => setEditForm({...editForm, role: e.target.value})} className="input" disabled={admin.is_owner}>{roles.map(r => <option key={r} value={r}>{r}</option>)}</select></label>
                  <div className="space-y-1">
                    <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_bots} onChange={e => setEditForm({...editForm, can_manage_bots: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> مدیریت ربات‌ها</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_accounts} onChange={e => setEditForm({...editForm, can_manage_accounts: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> مدیریت حساب‌ها</label>
                    <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.can_manage_admins} onChange={e => setEditForm({...editForm, can_manage_admins: e.target.checked})} disabled={editForm.role === 'SUPER_ADMIN'} /> مدیریت مدیران</label>
                  </div>
                  <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.is_active} onChange={e => setEditForm({...editForm, is_active: e.target.checked})} /> فعال</label>
                </div>
              )}

              {!editingId && (
                <div className="text-xs text-dark-400 space-y-0.5 pb-1">
                  <div>شناسه تلگرام: <span className="font-mono text-dark-300">{admin.telegram_id}</span></div>
                  <div>دسترسی‌ها: {((admin.can_manage_bots ? '🤖 ربات‌ها' : '') + (admin.can_manage_accounts ? ' 👤 حساب‌ها' : '') + (admin.can_manage_admins ? ' 👑 مدیران' : '') || 'هیچ')}</div>
                  <div>ساخته‌شده توسط: {admin.created_by || 'N/A'}</div>
                  <div>تاریخ ایجاد: {new Date(admin.created_at).toLocaleDateString('fa-IR')}</div>
                  {admin.last_login && <div>آخرین ورود: {new Date(admin.last_login).toLocaleString('fa-IR')}</div>}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="glass-card p-6 text-center text-dark-400">مدیری پیکربندی نشده است.</div>
        )}
      </div>
    </div>
  )
}
