import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'

const STRATEGIES = [
  { value: 'round_robin', label: 'Round Robin' },
  { value: 'pressure', label: 'Pressure-based' },
  { value: 'random', label: 'Random' },
  { value: 'error_based', label: 'Error-based' },
]

export default function UploadManagerPanel() {
  const qc = useQueryClient()
  const { data: config } = useQuery({
    queryKey: ['upload-config'],
    queryFn: async () => (await api.get('/admin/upload/config')).data,
  })
  const { data: health } = useQuery({
    queryKey: ['upload-health'],
    queryFn: async () => (await api.get('/admin/upload/health')).data,
  })

  const [values, setValues] = useState({
    upload_strategy: 'round_robin',
    web_upload_enabled: true,
    bot_fallback_enabled: true,
    max_concurrent_uploads: 5,
    my_music_enabled: true,
  })

  useEffect(() => {
    if (config) {
      setValues({
        upload_strategy: config.upload_strategy || 'round_robin',
        web_upload_enabled: config.web_upload_enabled,
        bot_fallback_enabled: config.bot_fallback_enabled,
        max_concurrent_uploads: config.max_concurrent_uploads || 5,
        my_music_enabled: config.my_music_enabled,
      })
    }
  }, [config])

  const save = useMutation({
    mutationFn: async () =>
      await api.put('/admin/upload/config', {
        upload_strategy: values.upload_strategy,
        web_upload_enabled: values.web_upload_enabled,
        bot_fallback_enabled: values.bot_fallback_enabled,
        max_concurrent_uploads: values.max_concurrent_uploads,
        my_music_enabled: values.my_music_enabled,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['upload-config'] })
      qc.invalidateQueries({ queryKey: ['upload-health'] })
    },
  })

  const refresh = useMutation({
    mutationFn: async () => (await api.post('/admin/upload/health/refresh')).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['upload-health'] }),
  })

  const updateField = (field: string, value: any) =>
    setValues({ ...values, [field]: value })

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-bold">Upload Configuration</h2>
        <button onClick={() => refresh.mutate()} className="btn-secondary text-sm">
          Refresh Pool Health
        </button>
      </div>

      {/* Strategy Selection */}
      <div className="glass-card p-4 space-y-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Upload Strategy</span>
          <select
            value={values.upload_strategy}
            onChange={(e) => updateField('upload_strategy', e.target.value)}
            className="input"
          >
            {STRATEGIES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Feature Toggles */}
      <div className="glass-card p-4 space-y-3">
        <h3 className="font-medium">Feature Toggles</h3>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.web_upload_enabled}
            onChange={(e) => updateField('web_upload_enabled', e.target.checked)}
          />
          <span className="text-sm">Web Upload Enabled</span>
        </label>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.bot_fallback_enabled}
            onChange={(e) => updateField('bot_fallback_enabled', e.target.checked)}
          />
          <span className="text-sm">Bot Fallback Enabled</span>
        </label>

        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={values.my_music_enabled}
            onChange={(e) => updateField('my_music_enabled', e.target.checked)}
          />
          <span className="text-sm">My Music Enabled</span>
        </label>
      </div>

      {/* Concurrent Uploads */}
      <div className="glass-card p-4 space-y-3">
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Max Concurrent Uploads</span>
          <input
            type="number"
            min={1}
            max={20}
            value={values.max_concurrent_uploads}
            onChange={(e) => updateField('max_concurrent_uploads', parseInt(e.target.value) || 1)}
            className="input w-32"
          />
        </label>
      </div>

      {/* Pool Health */}
      {health && (
        <div className="glass-card p-4 space-y-2">
          <h3 className="font-medium">Pool Health</h3>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>Total Bots: <b>{health.total_bots}</b></div>
            <div>Total Users: <b>{health.total_users}</b></div>
            <div>Active Users: <b className="text-emerald-400">{health.active_users}</b></div>
            <div>Total Active: <b>{health.total_active_clients}</b></div>
          </div>
        </div>
      )}

      {/* Save */}
      <button
        onClick={() => save.mutate()}
        disabled={save.isPending}
        className="btn-primary"
      >
        {save.isPending ? 'Saving...' : 'Save Configuration'}
      </button>
    </div>
  )
}
