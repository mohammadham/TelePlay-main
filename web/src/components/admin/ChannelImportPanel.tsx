import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useAppStore } from '../../lib/store'
import { Loader2, Play, Pause, RefreshCw, Eye, CheckCircle, XCircle, AlertCircle, Clock, Download, Upload, Info, AlertTriangle, Search, ChevronDown, ChevronUp, FileText, SlidersHorizontal } from 'lucide-react'

interface ImportJob {
  id: number
  admin_id: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  file_types: string[]
  date_from: string | null
  date_to: string | null
  target_folder_id: number | null
  user_account_id: number | null
  total_scanned: number
  total_imported: number
  total_skipped: number
  total_errors: number
  last_message_id: number | null
  error_message: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
  admin_username?: string
  admin_first_name?: string
}

interface UserAccount {
  id: number
  name: string
  username: string | null
  phone: string
  user_id: number | null
  purpose: string
  is_active?: boolean
  flood_wait_until: string | null
  last_used: string | null
}

interface Folder {
  id: number
  name: string
  parent_id: number | null
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-500/20 text-yellow-400',
  running: 'bg-blue-500/20 text-blue-400',
  completed: 'bg-green-500/20 text-green-400',
  failed: 'bg-red-500/20 text-red-400',
  cancelled: 'bg-gray-500/20 text-gray-400',
}

const STATUS_ICONS: Record<string, any> = {
  pending: Clock,
  running: Loader2,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: AlertCircle,
}

function StatusBadge({ status }: { status: string }) {
  const Icon = status && STATUS_ICONS[status]
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_COLORS[status]}`}>
      {Icon ? <Icon className={`w-3 h-3 inline mr-1 ${status === 'running' ? 'animate-spin' : ''}`} /> : null}
      {status.toUpperCase()}
    </span>
  )
}

function getAdminDisplayName(job: ImportJob): string {
  if (job.admin_username) return `@${job.admin_username}`
  if (job.admin_first_name) return job.admin_first_name
  return `Admin #${job.admin_id}`
}

export default function ChannelImportPanel() {
  const qc = useQueryClient()
  const addToast = useAppStore((s) => s.addToast)
  const [activeJobId, setActiveJobId] = useState<number | null>(null)
  const [previewResult, setPreviewResult] = useState<{scanned: number, estimated_matches: number} | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [jobStartTime, setJobStartTime] = useState<Date | null>(null) // For ETA calculation
  
  // Form state
  const [fileTypes, setFileTypes] = useState({ video: true, audio: true, document: true, image: true })
  // Default: date_from = yesterday, date_to = today (YYYY-MM-DD, local)
  const _toYmd = (d: Date) => {
    const yr = d.getFullYear()
    const mo = String(d.getMonth() + 1).padStart(2, '0')
    const dy = String(d.getDate()).padStart(2, '0')
    return `${yr}-${mo}-${dy}`
  }
  const _today = new Date()
  const _yesterday = new Date(_today.getTime() - 24 * 60 * 60 * 1000)
  const [dateFrom, setDateFrom] = useState(_toYmd(_yesterday))
  const [dateTo, setDateTo] = useState(_toYmd(_today))
  const [userAccountId, setUserAccountId] = useState<number | null>(null)
  const [targetFolderId, setTargetFolderId] = useState<number | null>(null)
  const [storageChannelId, setStorageChannelId] = useState<number | null>(null)
  // Advanced filters
  const [minFileSize, setMinFileSize] = useState('')
  const [maxFileSize, setMaxFileSize] = useState('')
  const [filenameRegex, setFilenameRegex] = useState('')
  const [captionRegex, setCaptionRegex] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  // Fetch data
  const { data: jobsData, refetch: _refetchJobs } = useQuery({
    queryKey: ['admin-channel-import-jobs'],
    queryFn: async () => (await api.get('/admin/channel-import/jobs')).data,
    refetchInterval: 2000,
  })

  const { data: accounts } = useQuery({
    queryKey: ['admin-channel-import-accounts'],
    queryFn: async () => (await api.get('/admin/channel-import/accounts')).data,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    refetchInterval: 15000,
    staleTime: 0,
  })

  const { data: folders, error: foldersError } = useQuery({
    queryKey: ['admin-channel-import-folders'],
    queryFn: async () => (await api.get('/admin/channel-import/folders')).data,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    refetchInterval: 10000, // Refresh folders every 10s to catch new folders
    staleTime: 0,
    retry: false,
  })

  const { data: storageChannels } = useQuery({
    queryKey: ['admin-channel-import-storage-channels'],
    queryFn: async () => (await api.get('/admin/channel-import/storage-channels')).data,
    refetchOnMount: 'always',
    refetchOnWindowFocus: true,
    refetchInterval: 15000,
    staleTime: 0,
  })

  // Active job polling
  const { data: activeJob, refetch: refetchActiveJob } = useQuery({
    queryKey: ['admin-channel-import-job', activeJobId],
    queryFn: async () => (await api.get(`/admin/channel-import/jobs/${activeJobId}`)).data,
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const data = query.state.data as ImportJob | undefined
      return data?.status === 'running' ? 2000 : false
    },
  })

  // Mutations
  const startMut = useMutation({
    mutationFn: async (payload: any) => (await api.post('/admin/channel-import/start', payload)).data,
    onSuccess: (job) => {
      setActiveJobId(job.id)
      qc.invalidateQueries({ queryKey: ['admin-channel-import-jobs'] })
    },
    onError: (err: any) => {
      addToast(err.response?.data?.detail || err.message || 'Failed to start import', 'error')
    },
  })

  const previewMut = useMutation({
    mutationFn: async (payload: any) => (await api.post('/admin/channel-import/preview', payload)).data,
    onSuccess: (res) => setPreviewResult(res),
    onError: (err: any) => {
      addToast(`Preview failed: ${err.response?.data?.detail || err.message}`, 'error')
    },
  })

  const cancelMut = useMutation({
    mutationFn: async (id: number) => (await api.post(`/admin/channel-import/jobs/${id}/cancel`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-channel-import-jobs'] })
      if (activeJobId) refetchActiveJob()
      addToast('Job cancelled successfully', 'success')
    },
    onError: (err: any) => {
      addToast(`Failed to cancel: ${err.response?.data?.detail || err.message}`, 'error')
    },
  })

  // Auto-set active job if there's a running one
  useEffect(() => {
    const runningJob = jobsData?.jobs?.find((j: ImportJob) => j.status === 'running')
    if (runningJob && !activeJobId) {
      setActiveJobId(runningJob.id)
    }
  }, [jobsData, activeJobId])
  // Auto-select storage channel if only one exists
  useEffect(() => {
    if (!storageChannelId && storageChannels && storageChannels.length === 1) {
      setStorageChannelId(storageChannels[0].id)
    }
  }, [storageChannels, storageChannelId])

  // Auto-select MTProto account if only one active/eligible exists
  useEffect(() => {
    if (userAccountId || !accounts?.length) return
    const eligible = accounts.filter((a: UserAccount) => {
      const isActive = (a as any).is_active !== false
      const inFlood = a.flood_wait_until && new Date(a.flood_wait_until) > new Date()
      return isActive && !inFlood
    })
    if (eligible.length === 1) {
      setUserAccountId(eligible[0].id)
    }
  }, [accounts, userAccountId])
  const getPayload = () => ({
    file_types: Object.entries(fileTypes).filter(([, v]) => v).map(([k]) => k),
    date_from: dateFrom || null,
    date_to: dateTo || null,
    user_account_id: userAccountId,
    target_folder_id: targetFolderId,
    storage_channel_id: storageChannelId,
    min_file_size: minFileSize ? parseInt(minFileSize) : null,
    max_file_size: maxFileSize ? parseInt(maxFileSize) : null,
    filename_regex: filenameRegex && filenameRegex.trim() ? filenameRegex.trim() : null,
    caption_regex: captionRegex && captionRegex.trim() ? captionRegex.trim() : null,
  })

  const handlePreview = () => {
    if (!Object.values(fileTypes).some(v => v)) {
      addToast('Select at least one file type', 'error')
      return
    }
    if (!storageChannelId) {
      addToast('Please select a storage channel', 'error')
      return
    }
    if (!userAccountId) {
      addToast('Please select an MTProto account', 'error')
      return
    }
    setPreviewLoading(true)
    previewMut.mutate(getPayload(), {
      onSettled: () => setPreviewLoading(false),
    })
  }

  const handleStart = () => {
    if (!Object.values(fileTypes).some(v => v)) {
      addToast('Select at least one file type', 'error')
      return
    }
    if (!storageChannelId) {
      addToast('Please select a storage channel', 'error')
      return
    }
    if (!accounts?.length) {
      addToast('No MTProto accounts available. Add one in Accounts panel first.', 'error')
      return
    }
    if (!userAccountId) {
      addToast('Please select an MTProto account', 'error')
      return
    }
    startMut.mutate(getPayload())
  }

  const formatDate = (iso: string | null) => iso ? new Date(iso).toLocaleString() : '—'
  const formatNumber = (n: number) => n.toLocaleString()

  // Check if selected account is in flood wait
  const selectedAccount = accounts?.find((a: UserAccount) => a.id === userAccountId)
  const isAccountInFloodWait = !!(
    selectedAccount?.flood_wait_until && 
    new Date(selectedAccount.flood_wait_until) > new Date()
  )

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold">📥 Channel Import</h2>
        <div className="flex gap-2">
          <button onClick={() => qc.invalidateQueries({ queryKey: ['admin-channel-import-jobs'] })} className="btn-secondary btn-sm">
            <RefreshCw className="w-4 h-4 mr-1" /> Refresh
          </button>
        </div>
      </div>

      {/* Configuration Card */}
      <div className="glass-card p-4 space-y-4 border-primary-500/20">
        <h3 className="font-bold text-lg">Import Configuration</h3>
        
        {/* File Types */}
        <div>
          <label className="text-sm text-dark-400 block mb-2">File Types</label>
          <div className="flex flex-wrap gap-3">
            {[
              { key: 'video' as const, label: '🎬 Video', color: 'bg-red-500/20 text-red-400' },
              { key: 'audio' as const, label: '🎵 Audio', color: 'bg-green-500/20 text-green-400' },
              { key: 'document' as const, label: '📄 Document', color: 'bg-blue-500/20 text-blue-400' },
              { key: 'image' as const, label: '🖼 Image', color: 'bg-purple-500/20 text-purple-400' },
            ].map(({ key, label, color }) => (
              <label key={key} className={`flex items-center gap-2 px-3 py-1.5 rounded-lg cursor-pointer transition-colors ${fileTypes[key] ? color : 'bg-white/5 hover:bg-white/10'}`}>
                <input
                  type="checkbox"
                  checked={fileTypes[key]}
                  onChange={(e) => setFileTypes(prev => ({ ...prev, [key]: e.target.checked }))}
                  className="w-4 h-4 accent-primary-500"
                />
                <span className="text-sm">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Date Range */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-sm text-dark-400">Date From</span>
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-dark-400">Date To</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input"
            />
          </label>
        </div>

        {/* User Account, Storage Channel & Folder */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <label className="flex flex-col gap-1">
            <span className="text-sm text-dark-400">MTProto Account <span className="text-red-400">*</span></span>
            <select
              value={userAccountId || ''}
              onChange={(e) => setUserAccountId(e.target.value ? parseInt(e.target.value) : null)}
              className="input"
              disabled={isAccountInFloodWait}
            >
              <option value="">Select account (required)</option>
              {accounts?.map((acc: UserAccount) => {
                const inFlood = !!(acc.flood_wait_until && new Date(acc.flood_wait_until) > new Date())
                const inactive = acc.is_active === false
                const maskedPhone = acc.phone ? acc.phone.slice(0, 3) + '****' + acc.phone.slice(-4) : ''
                return (
                  <option key={acc.id} value={acc.id} disabled={inFlood || inactive}>
                    {acc.name} {acc.username && `(@${acc.username})`} {maskedPhone && `· ${maskedPhone}`} [${acc.purpose}]
                    {inactive && ' ⏸ Inactive'}
                    {inFlood && ' ⏳ Flood Wait'}
                  </option>
                )
              })}
            </select>
            {isAccountInFloodWait && (
              <p className="text-xs text-yellow-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" /> Selected account is in Flood Wait
              </p>
            )}
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-dark-400">Storage Channel <span className="text-red-400">*</span></span>
            <select
              value={storageChannelId || ''}
              onChange={(e) => setStorageChannelId(e.target.value ? parseInt(e.target.value) : null)}
              className="input"
            >
              <option value="">Select channel (required)</option>
              {storageChannels?.map((ch: any) => (
                <option key={ch.id} value={ch.id}>
                  {ch.title} ({ch.channel_id})
                </option>
              ))}
            </select>
            {storageChannels?.length === 0 && (
              <p className="text-xs text-red-400">No storage channels configured in settings</p>
            )}
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-sm text-dark-400">Target Folder (optional)</span>
            <select
              value={targetFolderId || ''}
              onChange={(e) => setTargetFolderId(e.target.value ? parseInt(e.target.value) : null)}
              className="input"
              disabled={!!foldersError}
            >
              <option value="">Root (no folder)</option>
              {folders?.map((f: Folder) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            {foldersError && (
              <p className="text-xs text-yellow-400 flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {(foldersError as any)?.response?.data?.detail || 'Unable to load folders'}
              </p>
            )}
            {!foldersError && folders && folders.length === 0 && (
              <p className="text-xs text-dark-400">No folders yet — create one in Files panel</p>
            )}
          </label>
        </div>

        {/* Advanced Filters (collapsible) */}
        <div className="border-t border-white/10 pt-4">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm text-dark-400 hover:text-white transition-colors"
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span>Advanced Filters</span>
            {showAdvanced ? <ChevronUp className="w-4 h-4 ml-auto" /> : <ChevronDown className="w-4 h-4 ml-auto" />}
          </button>
          {showAdvanced && (
            <div className="mt-4 space-y-4 pt-4 border-t border-white/5">
              {/* File Size Range */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="flex flex-col gap-1">
                  <span className="text-sm text-dark-400 flex items-center gap-1">
                    <FileText className="w-3 h-3" /> Min File Size (bytes)
                  </span>
                  <input
                    type="number"
                    value={minFileSize}
                    onChange={(e) => setMinFileSize(e.target.value)}
                    placeholder="e.g. 1048576 (1MB)"
                    className="input"
                    min="0"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="text-sm text-dark-400 flex items-center gap-1">
                    <FileText className="w-3 h-3" /> Max File Size (bytes)
                  </span>
                  <input
                    type="number"
                    value={maxFileSize}
                    onChange={(e) => setMaxFileSize(e.target.value)}
                    placeholder="e.g. 104857600 (100MB)"
                    className="input"
                    min="0"
                  />
                </label>
              </div>

              {/* Filename Regex */}
              <label className="flex flex-col gap-1">
                <span className="text-sm text-dark-400 flex items-center gap-1">
                  <Search className="w-3 h-3" /> Filename Regex
                </span>
                <input
                  type="text"
                  value={filenameRegex}
                  onChange={(e) => setFilenameRegex(e.target.value)}
                  placeholder="e.g. .*\\.(mp4|mkv)$"
                  className="input font-mono text-sm"
                />
                <p className="text-xs text-dark-400">JavaScript regex pattern to match filename</p>
              </label>

              {/* Caption Regex */}
              <label className="flex flex-col gap-1">
                <span className="text-sm text-dark-400 flex items-center gap-1">
                  <Search className="w-3 h-3" /> Caption Regex
                </span>
                <input
                  type="text"
                  value={captionRegex}
                  onChange={(e) => setCaptionRegex(e.target.value)}
                  placeholder="e.g. .*teleplay.*"
                  className="input font-mono text-sm"
                />
                <p className="text-xs text-dark-400">JavaScript regex pattern to match message caption</p>
              </label>
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex flex-wrap gap-2 pt-2 border-t border-white/10">
          <button
            onClick={handlePreview}
            disabled={previewLoading || startMut.isPending}
            className="btn-secondary"
          >
            <Eye className="w-4 h-4 mr-1" />
            {previewLoading ? 'Previewing...' : 'Preview'}
          </button>
          <button
            onClick={handleStart}
            disabled={startMut.isPending || !accounts?.length || isAccountInFloodWait}
            className="btn-primary"
          >
            <Play className="w-4 h-4 mr-1" />
            {startMut.isPending ? 'Starting...' : 'Start Import'}
          </button>
        </div>

        {/* Preview Result */}
        {previewResult && (
          <div className="glass-card p-3 bg-green-500/10 border-green-500/20">
            <div className="flex items-center gap-4 text-sm flex-wrap">
              <span><Download className="w-4 h-4 inline mr-1" /> Scanned: <strong>{formatNumber(previewResult.scanned)}</strong></span>
              <span><Upload className="w-4 h-4 inline mr-1" /> Estimated matches: <strong className="text-green-400">{formatNumber(previewResult.estimated_matches)}</strong></span>
              <span className="text-yellow-400 flex items-center gap-1">
                <Info className="w-3 h-3" /> Limited to 5000 most recent messages
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Active Job Panel - show selected job from polling (running) or jobsData (completed/failed) */}
      {(() => {
        // For running jobs, use polling data; for others, use jobsData as fallback
        const displayJob = activeJob || (activeJobId ? jobsData?.jobs?.find((j: ImportJob) => j.id === activeJobId) : null);
        
        if (!displayJob) return null;
        
        // Track start time for ETA calculation (only for running jobs)
        useEffect(() => {
          if (displayJob.status === 'running' && !jobStartTime) {
            setJobStartTime(new Date());
          } else if (displayJob.status !== 'running') {
            setJobStartTime(null);
          }
        }, [displayJob.status, displayJob.id]);

        // Calculate ETA for running jobs
        const getETA = () => {
          if (displayJob.status !== 'running' || !jobStartTime || displayJob.total_scanned === 0) return null;
          const elapsedSeconds = (Date.now() - jobStartTime.getTime()) / 1000;
          const rate = displayJob.total_scanned / elapsedSeconds; // messages per second
          if (rate === 0) return null;
          // Estimate total messages (we don't know exact total, so use scanned as baseline)
          // For simplicity, estimate based on current rate and remaining in current batch
          const estimatedTotal = displayJob.total_scanned + (displayJob.total_scanned * 0.5); // rough estimate
          const remaining = estimatedTotal - displayJob.total_scanned;
          const etaSeconds = remaining / rate;
          return etaSeconds;
        };

        const eta = getETA();
        const formatETA = (seconds: number) => {
          if (seconds < 60) return `${Math.round(seconds)}s`;
          if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
          return `${Math.round(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`;
        };
        
        return (
          <div className="glass-card p-4 space-y-4 border-primary-500/30">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-lg">Import Job #{displayJob.id}</h3>
              <StatusBadge status={displayJob.status} />
            </div>

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Scanned</span>
                <span className="font-mono">{formatNumber(displayJob.total_scanned)}</span>
              </div>
              <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary-500 transition-all duration-300"
                  style={{ width: displayJob.total_scanned > 0 ? Math.min(100, (displayJob.total_imported / displayJob.total_scanned) * 100) + '%' : '0%' }}
                />
              </div>
              {/* ETA Display */}
              {eta && jobStartTime && (
                <div className="text-xs text-yellow-400 flex items-center gap-1">
                  <span>⏱ ~{formatETA(eta)} remaining</span>
                  <span className="text-gray-500">|</span>
                  <span>{(displayJob.total_scanned / ((Date.now() - jobStartTime.getTime()) / 1000)).toFixed(1)} msg/s</span>
                </div>
              )}
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="glass-card p-3 text-center">
                <div className="text-2xl font-bold text-green-400">{formatNumber(displayJob.total_imported)}</div>
                <div className="text-xs text-dark-400">Imported</div>
              </div>
              <div className="glass-card p-3 text-center">
                <div className="text-2xl font-bold text-yellow-400">{formatNumber(displayJob.total_skipped)}</div>
                <div className="text-xs text-dark-400">Skipped (dup)</div>
              </div>
              <div className="glass-card p-3 text-center">
                <div className="text-2xl font-bold text-red-400">{formatNumber(displayJob.total_errors)}</div>
                <div className="text-xs text-dark-400">Errors</div>
              </div>
              <div className="glass-card p-3 text-center">
                <div className="text-2xl font-bold text-blue-400">{formatNumber(displayJob.total_scanned)}</div>
                <div className="text-xs text-dark-400">Total Scanned</div>
              </div>
            </div>

            {/* Job Details */}
            <div className="text-sm text-dark-400 space-y-1 font-mono">
              <div>Started: {formatDate(displayJob.started_at)}</div>
              {displayJob.finished_at && <div>Finished: {formatDate(displayJob.finished_at)}</div>}
              {displayJob.last_message_id && <div>Last Message ID: {displayJob.last_message_id}</div>}
              {displayJob.error_message && (
                <div className="text-red-400">Error: {displayJob.error_message}</div>
              )}
            </div>

            {/* Cancel Button - for pending or running jobs */}
            {(displayJob.status === 'running' || displayJob.status === 'pending') && (
              <button
                onClick={() => cancelMut.mutate(displayJob.id)}
                disabled={cancelMut.isPending}
                className="btn-secondary w-full"
              >
                <Pause className="w-4 h-4 mr-1" />
                {cancelMut.isPending ? 'Cancelling...' : 'Cancel Job'}
              </button>
            )}
          </div>
        )
      })()}

      {/* Jobs History */}
      <div className="glass-card p-4">
        <h3 className="font-bold text-lg mb-4">Import History</h3>
        
        {!jobsData?.jobs?.length ? (
          <div className="text-center text-dark-400 py-8">No import jobs yet</div>
        ) : (
          <div className="space-y-2">
            {jobsData.jobs.map((job: ImportJob) => (
              <div
                key={job.id}
                className={`p-3 rounded-lg flex items-center justify-between gap-4 ${activeJobId === job.id ? 'ring-2 ring-primary-500/50' : ''}`}
                onClick={() => setActiveJobId(job.id)}
              >
                <div className="flex items-center gap-3 min-w-0 flex-1">
                  <StatusBadge status={job.status} />
                  <div className="text-sm min-w-0">
                    <div className="font-medium truncate">
                      Types: {job.file_types.map(t => t.charAt(0).toUpperCase() + t.slice(1)).join(', ')}
                    </div>
                    <div className="text-dark-400 text-xs flex items-center gap-2">
                      {job.date_from && `From: ${new Date(job.date_from).toLocaleDateString()}`}
                      {job.date_to && `To: ${new Date(job.date_to).toLocaleDateString()}`}
                      <span className="text-gray-500">|</span>
                      <span>by {getAdminDisplayName(job)}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4 text-sm text-dark-400 font-mono shrink-0">
                  <span>✓ {formatNumber(job.total_imported)}</span>
                  <span>⊘ {formatNumber(job.total_skipped)}</span>
                  <span>✗ {formatNumber(job.total_errors)}</span>
                  <span>🔍 {formatNumber(job.total_scanned)}</span>
                  <span className="text-xs">{formatDate(job.created_at)}</span>
                  {job.status === 'running' && (
                    <Loader2 className="w-4 h-4 animate-spin text-primary-400" />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}