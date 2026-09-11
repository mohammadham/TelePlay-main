import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useState, useEffect, useRef } from 'react'
import { useAppStore } from '../../lib/store'

const SECTIONS = [
  {
    id: 'telegram',
    label: '📡 Telegram Settings',
    keys: ['TELEGRAM_API_ID', 'TELEGRAM_API_HASH', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_STORAGE_CHANNEL_ID'],
  },
  {
    id: 'auth',
    label: '🔐 Auth & Access',
    keys: ['JWT_SECRET', 'WEB_BASE_URL'],
  },
  {
    id: 'features',
    label: '🎛️ Feature Flags',
    keys: ['CACHE_ENABLED', 'VIDEO_CACHE_ENABLED', 'ADS_ENABLED'],
  },
  {
    id: 'channel_import',
    label: '📥 Channel Import',
    keys: ['CHANNEL_IMPORT_AUTO_RESUME'],
  },
]

export default function SettingsPanel() {
  const qc = useQueryClient()
  const addToast = useAppStore(s => s.addToast)
  const { data } = useQuery({ queryKey: ['admin-settings'], queryFn: async () => (await api.get('/admin/settings')).data })
  const [values, setValues] = useState<Record<string, string>>({})
  const [initialValues, setInitialValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const mountedRef = useRef(false)

  useEffect(() => {
    if (!data) return
    const m: Record<string, string> = {}
    data.forEach((r: any) => { m[r.key] = r.value })
    setValues(m)
    if (!mountedRef.current) {
      setInitialValues({ ...m })
      mountedRef.current = true
    }
  }, [data])

  const updateField = (key: string, value: string) => {
    setValues(prev => ({ ...prev, [key]: value }))
  }

  const changedKeys = Object.keys(values).filter(k => values[k] !== initialValues[k])
  const hasChanges = changedKeys.length > 0

  const saveMutation = useMutation({
    mutationFn: async () => (await api.put('/admin/settings', values)).data,
    onMutate: () => setSaving(true),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['admin-settings'] })
      setInitialValues(values)
      addToast(`تنظیمات ذخیره شد${res.changed?.length ? ` (${res.changed.length} تغییر)` : ''}`, 'success')
    },
    onError: (err: any) => {
      addToast('خطا در ذخیره تنظیمات: ' + (err?.response?.data?.detail || err?.message || 'Unknown error'), 'error')
    },
    onSettled: () => setSaving(false),
  })

  const handleSave = () => {
    if (!hasChanges) return
    saveMutation.mutate()
  }

  if (!data) return <div className="p-6">Loading settings...</div>

  return (
    <div className="p-6 space-y-6 max-w-3xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">تنظیمات سامانه</h2>
        {hasChanges && (
          <span className="text-xs text-amber-400 bg-amber-500/10 px-2 py-1 rounded">
            {changedKeys.length} تغییر نجات‌نشده
          </span>
        )}
      </div>

      {SECTIONS.map(section => {
        const sectionKeys = section.keys.filter(k => data.some((r: any) => r.key === k))
        if (sectionKeys.length === 0) return null
        return (
          <div key={section.id} className="glass-card p-4 space-y-4">
            <h3 className="font-semibold text-sm text-white/70 border-b border-white/5 pb-2">{section.label}</h3>
            {sectionKeys.map(key => {
              const row = data.find((r: any) => r.key === key)
              if (!row) return null
              const changed = values[key] !== initialValues[key]
              return (
                <label key={key} className={`flex flex-col gap-1 transition-colors ${changed ? 'text-amber-300' : ''}`}>
                  <span className="text-sm font-medium flex items-center gap-2">
                    {key}
                    <span className="text-xs text-dark-400 font-normal">— {row.description}</span>
                    {changed && (
                      <span className="ml-auto text-[10px] bg-amber-500/20 text-amber-300 px-1.5 py-0.5 rounded">تغییر یافته</span>
                    )}
                  </span>
                  <input
                    value={values[key] || ''}
                    onChange={e => updateField(key, e.target.value)}
                    className={`input transition-all ${changed ? 'border-amber-500/50' : ''}`}
                    placeholder={key}
                  />
                </label>
              )
            })}
          </div>
        )
      })}

      <button
        onClick={handleSave}
        disabled={saving || !hasChanges}
        className={`btn-primary ${!hasChanges ? 'opacity-40 cursor-not-allowed' : ''}`}
      >
        {saving ? 'در حال ذخیره...' : `ذخیره تغییرات${hasChanges ? ` (${changedKeys.length})` : ''}`}
      </button>
    </div>
  )
}
