import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

export default function AccountManager() {
  const qc = useQueryClient()
  const { data: accounts, isLoading } = useQuery({
    queryKey: ['admin-accounts'],
    queryFn: async () => (await api.get('/admin/accounts')).data,
  })
  const [showAdd, setShowAdd] = useState(false)
  const [loginStep, setLoginStep] = useState<'idle' | 'code' | 'verify'>('idle')
  const [loginData, setLoginData] = useState({ name: '', phone: '', api_id: '', api_hash: '' })
  const [codeData, setCodeData] = useState({ phone_code_hash: '', code: '', password: '' })

  const purposes = ['STORAGE', 'STREAMING', 'DOWNLOAD']

  const startLoginMut = useMutation({
    mutationFn: async (d: any) => (await api.post('/admin/accounts/login/start', d)).data,
    onSuccess: (res) => {
      setCodeData(prev => ({ ...prev, phone_code_hash: res.phone_code_hash }))
      setLoginStep('verify')
    }
  })

  const verifyLoginMut = useMutation({
    mutationFn: async (d: any) => (await api.post('/admin/accounts/login/verify', d)).data,
    onSuccess: (res) => {
      // Auto-fill the create form with verified session
      setLoginData(prev => ({
        ...prev,
        // session will be passed to create
      }))
      // Store session in a ref or state for create
      window.__TEMP_SESSION__ = {
        session_string: res.session_string,
        user_id: res.user_id,
        username: res.username,
        has_2fa: res.has_2fa,
      }
      setLoginStep('idle')
      setShowAdd(true)
    }
  })

  const createMut = useMutation({
    mutationFn: async (d: any) => (await api.post('/admin/accounts/with-session', d)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-accounts'] })
      setShowAdd(false)
      setLoginData({ name: '', phone: '', api_id: '', api_hash: '' })
      delete window.__TEMP_SESSION__
    }
  })

  const updateMut = useMutation({
    mutationFn: async ({ id, data }: { id: number; data: any }) => (await api.put(`/admin/accounts/${id}`, data)).data,
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-accounts'] }); setEditingId(null) }
  })

  const deleteMut = useMutation({
    mutationFn: async ({ id, revoke }: { id: number; revoke: boolean }) => (await api.delete(`/admin/accounts/${id}?revoke_session=${revoke}`)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-accounts'] })
  })

  const healthMut = useMutation({
    mutationFn: async (id: number) => (await api.post(`/admin/accounts/${id}/health`)).data,
    onSuccess: (res) => alert(res.ok ? `✅ Healthy\nUser: @${res.username}\nFlood wait: ${res.flood_wait_seconds ?? 0}s` : `❌ ${res.error}`)
  })

  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ name: '', phone: '', api_id: '', api_hash: '', purpose: 'STORAGE', is_active: true, two_fa_password: '' })

  if (isLoading) return <div className="p-6">Loading accounts...</div>

  return (
    <div className="p-6 space-y-6 max-w-4xl">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">Account Manager (MTProto)</h2>
        <button onClick={() => { setLoginStep('code'); setShowAdd(false) }} className="btn-primary">+ Add Account</button>
      </div>

      {/* Login Flow - Step 1: Send Code */}
      {loginStep === 'code' && (
        <div className="glass-card p-4 space-y-3 border-primary-500/30">
          <h3 className="font-bold">Step 1: Send Login Code</h3>
          <label className="flex flex-col gap-1"><span className="text-sm">Account Name *</span><input value={loginData.name} onChange={e => setLoginData({...loginData, name: e.target.value})} placeholder="storage_1, stream_2" className="input" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">Phone Number *</span><input value={loginData.phone} onChange={e => setLoginData({...loginData, phone: e.target.value})} placeholder="+989xxxxxxxxx" className="input" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">API ID *</span><input type="number" value={loginData.api_id} onChange={e => setLoginData({...loginData, api_id: e.target.value})} placeholder="2345678" className="input" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">API Hash *</span><input type="password" value={loginData.api_hash} onChange={e => setLoginData({...loginData, api_hash: e.target.value})} placeholder="a1b2c3..." className="input" /></label>
          <div className="flex gap-2">
            <button onClick={() => startLoginMut.mutate({ name: loginData.name, phone: loginData.phone.startsWith('+') ? loginData.phone : '+' + loginData.phone, api_id: parseInt(loginData.api_id), api_hash: loginData.api_hash })} disabled={startLoginMut.isPending || !loginData.name || !loginData.phone || !loginData.api_id || !loginData.api_hash} className="btn-primary">{startLoginMut.isPending ? 'Sending...' : 'Send Code'}</button>
            <button onClick={() => setLoginStep('idle')} className="btn-secondary">Cancel</button>
          </div>
          {startLoginMut.isError && <div className="text-red-400 text-sm">Error: {startLoginMut.error?.response?.data?.detail || startLoginMut.error?.message}</div>}
        </div>
      )}

      {/* Login Flow - Step 2: Verify Code */}
      {loginStep === 'verify' && (
        <div className="glass-card p-4 space-y-3 border-primary-500/30">
          <h3 className="font-bold">Step 2: Verify Code</h3>
          <p className="text-sm text-dark-400">Enter the code sent to {loginData.phone}</p>
          <label className="flex flex-col gap-1"><span className="text-sm">Login Code *</span><input value={codeData.code} onChange={e => setCodeData({...codeData, code: e.target.value})} placeholder="12345" maxLength={6} className="input text-center tracking-widest" /></label>
          <label className="flex flex-col gap-1"><span className="text-sm">2FA Password (if enabled)</span><input type="password" value={codeData.password} onChange={e => setCodeData({...codeData, password: e.target.value})} placeholder="Optional 2FA password" className="input" /></label>
          <div className="flex gap-2">
            <button onClick={() => verifyLoginMut.mutate({ name: loginData.name, phone: loginData.phone, api_id: parseInt(loginData.api_id), api_hash: loginData.api_hash, phone_code_hash: codeData.phone_code_hash, code: codeData.code, password: codeData.password || undefined })} disabled={verifyLoginMut.isPending || !codeData.code} className="btn-primary">{verifyLoginMut.isPending ? 'Verifying...' : 'Verify & Continue'}</button>
            <button onClick={() => setLoginStep('code')} className="btn-secondary">Back</button>
          </div>
          {verifyLoginMut.isError && <div className="text-red-400 text-sm">Error: {verifyLoginMut.error?.response?.data?.detail || verifyLoginMut.error?.message}</div>}
        </div>
      )}

      {/* Create Account Form (after successful login) */}
      {showAdd && !loginStep && (
        <div className="glass-card p-4 space-y-3 border-green-500/30">
          <h3 className="font-bold">Step 3: Save Account</h3>
          <p className="text-sm text-green-400">✅ Login verified! Session ready.</p>
          <label className="flex flex-col gap-1"><span className="text-sm">Purpose</span><select value={loginData.purpose || 'STORAGE'} onChange={e => setLoginData({...loginData, purpose: e.target.value})} className="input">{purposes.map(p => <option key={p} value={p}>{p}</option>)}</select></label>
          <label className="flex flex-col gap-1"><span className="text-sm">2FA Password (for future logins)</span><input type="password" value={loginData.two_fa_password || ''} onChange={e => setLoginData({...loginData, two_fa_password: e.target.value})} placeholder="Optional: save 2FA password encrypted" className="input" /></label>
          <label className="flex items-center gap-2"><input type="checkbox" checked={loginData.is_active !== false} onChange={e => setLoginData({...loginData, is_active: e.target.checked})} /> Active</label>
          <div className="flex gap-2">
            <button onClick={() => {
              const session = window.__TEMP_SESSION__
              if (!session?.session_string) return alert('Session missing, please re-login')
              createMut.mutate({
                name: loginData.name,
                phone: loginData.phone,
                api_id: parseInt(loginData.api_id),
                api_hash: loginData.api_hash,
                session_string: session.session_string,
                two_fa_password: loginData.two_fa_password || null,
                purpose: loginData.purpose || 'STORAGE',
                is_active: loginData.is_active !== false,
              })
            }} disabled={createMut.isPending} className="btn-primary">{createMut.isPending ? 'Saving...' : 'Save Account'}</button>
            <button onClick={() => { setShowAdd(false); setLoginStep('idle'); delete window.__TEMP_SESSION__ }} className="btn-secondary">Cancel</button>
          </div>
          {createMut.isError && <div className="text-red-400 text-sm">Error: {createMut.error?.response?.data?.detail || createMut.error?.message}</div>}
        </div>
      )}

      <div className="space-y-3">
        {accounts?.map((acc: any) => (
          <div key={acc.id} className="glass-card p-4 space-y-3">
            <div className="flex flex-wrap items-center gap-4">
              <div className="flex-1 min-w-[200px]">
                <span className="font-mono text-lg">{acc.name}</span>
                <span className={`ml-2 px-2 py-0.5 rounded text-xs ${acc.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                  {acc.is_active ? 'Active' : 'Inactive'}
                </span>
                <span className="ml-2 px-2 py-0.5 rounded text-xs bg-primary-500/20 text-primary-400">{acc.purpose}</span>
                {acc.username && <span className="ml-2 text-dark-400">@{acc.username}</span>}
                {acc.flood_wait_until && new Date(acc.flood_wait_until) > new Date() && (
                  <span className="ml-2 px-2 py-0.5 rounded text-xs bg-yellow-500/20 text-yellow-400">⏳ Flood Wait</span>
                )}
              </div>
              {editingId === acc.id ? (
                <div className="flex gap-2">
                  <button onClick={() => updateMut.mutate({ id: acc.id, data: editForm })} disabled={updateMut.isPending} className="btn-primary btn-sm">{updateMut.isPending ? 'Saving...' : 'Save'}</button>
                  <button onClick={() => setEditingId(null)} className="btn-secondary btn-sm">Cancel</button>
                </div>
              ) : (
                <div className="flex gap-2">
                  <button onClick={() => { setEditForm({ name: acc.name, phone: acc.phone, api_id: '', api_hash: '', purpose: acc.purpose, is_active: acc.is_active, two_fa_password: '' }); setEditingId(acc.id) }} className="btn-secondary btn-sm">Edit</button>
                  <button onClick={() => healthMut.mutate(acc.id)} disabled={healthMut.isPending} className="btn-primary btn-sm">{healthMut.isPending ? 'Checking...' : 'Health'}</button>
                  <button onClick={() => { const revoke = confirm('Revoke Telegram session? (Logs out everywhere)'); if (confirm(`Delete account "${acc.name}"?${revoke ? ' Session will be revoked.' : ''}`)) deleteMut.mutate({ id: acc.id, revoke }) }} className="btn-secondary btn-sm text-red-400 hover:bg-red-500/10">Delete</button>
                </div>
              )}
            </div>

            {editingId === acc.id && (
              <div className="space-y-2 pt-2 border-t border-white/10">
                <label className="flex flex-col gap-1"><span className="text-sm">Name</span><input value={editForm.name} onChange={e => setEditForm({...editForm, name: e.target.value})} className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">Phone</span><input value={editForm.phone} onChange={e => setEditForm({...editForm, phone: e.target.value})} className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">New API Hash (leave empty to keep)</span><input type="password" value={editForm.api_hash} onChange={e => setEditForm({...editForm, api_hash: e.target.value})} placeholder="Optional" className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">2FA Password (leave empty to keep)</span><input type="password" value={editForm.two_fa_password} onChange={e => setEditForm({...editForm, two_fa_password: e.target.value})} placeholder="Optional" className="input" /></label>
                <label className="flex flex-col gap-1"><span className="text-sm">Purpose</span><select value={editForm.purpose} onChange={e => setEditForm({...editForm, purpose: e.target.value})} className="input">{purposes.map(p => <option key={p} value={p}>{p}</option>)}</select></label>
                <label className="flex items-center gap-2"><input type="checkbox" checked={editForm.is_active} onChange={e => setEditForm({...editForm, is_active: e.target.checked})} /> Active</label>
              </div>
            )}

            {!editingId && (
              <div className="text-xs text-dark-400 space-y-1">
                <div>User ID: {acc.user_id}</div>
                <div>Phone: {acc.phone}</div>
                <div>Last used: {acc.last_used ? new Date(acc.last_used).toLocaleString() : 'Never'}</div>
                <div>Created: {new Date(acc.created_at).toLocaleString()}</div>
              </div>
            )}
          </div>
        ))}
        {!accounts?.length && <div className="glass-card p-6 text-center text-dark-400">No MTProto accounts configured. Click "Add Account" to start.</div>}
      </div>
    </div>
  )
}