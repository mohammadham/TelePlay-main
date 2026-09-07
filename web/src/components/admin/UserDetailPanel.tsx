import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import { useAdminUserDetail } from '../../lib/api'

function SkeletonRow() {
  return (
    <div className="glass-card p-4 animate-pulse space-y-3">
      <div className="flex items-center gap-4">
        <div className="flex-1 min-w-[200px] space-y-2">
          <div className="skeleton h-5 w-32" />
          <div className="skeleton h-4 w-48" />
          <div className="flex gap-2">
            {Array.from({ length: 4 }).map((_, i) => <div key={i} className="skeleton h-6 w-16 rounded-full" />)}
          </div>
        </div>
      </div>
      <div className="space-y-2 pt-2 border-t border-white/10">
        <div className="skeleton h-4 w-full" />
        <div className="skeleton h-4 w-3/4" />
        <div className="skeleton h-4 w-1/2" />
      </div>
    </div>
  )
}

export default function UserDetailPanel() {
  const [search, setSearch] = useState('')
  const [selectedTelegramId, setSelectedTelegramId] = useState<number | null>(null)

  const { data: users, isLoading: loadingUsers } = useQuery({
    queryKey: ['admin-users'],
    queryFn: async () => (await api.get('/admin/users')).data,
  })

  const { data: userDetail, isLoading: loadingDetail } = useAdminUserDetail(selectedTelegramId ?? 0)

  const filtered = search
    ? (users?.users || []).filter((u: any) =>
        String(u.telegram_id).includes(search) ||
        (u.first_name || '').toLowerCase().includes(search.toLowerCase()) ||
        (u.username || '').toLowerCase().includes(search.toLowerCase())
      )
    : users?.users || []

  return (
    <div className="space-y-4">
      {/* Search */}
      <div className="glass-card p-4">
        <h2 className="text-lg font-bold mb-3">👤 جستجوی کاربر</h2>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="جستجو بر اساس نام، یوزرنیم یا ID تلگرام..."
          className="input w-full"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_2fr] gap-4">
        {/* User List */}
        <div className="glass-card p-4">
          <h3 className="font-bold text-sm mb-3 text-dark-400">لیست کاربران ({filtered.length})</h3>
          {loadingUsers ? (
            Array.from({ length: 5 }).map((_, i) => <div key={i} className="skeleton h-10 rounded mb-2" />)
          ) : filtered.length === 0 ? (
            <div className="text-sm text-dark-400 text-center py-8">کاربری یافت نشد</div>
          ) : (
            <div className="space-y-1 max-h-[500px] overflow-y-auto">
              {filtered.map((u: any) => (
                <button
                  key={u.telegram_id}
                  onClick={() => setSelectedTelegramId(u.telegram_id)}
                  className={`w-full text-right p-2 rounded text-sm flex items-center justify-between transition-colors ${
                    selectedTelegramId === u.telegram_id
                      ? 'bg-primary-600/20 border border-primary-500/40'
                      : 'hover:bg-white/5 border border-transparent'
                  }`}
                >
                  <span className="truncate">
                    {u.first_name || 'بدون نام'}{' '}
                    <span className="text-dark-400">@{u.username || '—'}</span>
                  </span>
                  <span className="text-xs text-dark-500 ml-2 shrink-0">{u.telegram_id}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* User Detail */}
        <div>
          {loadingDetail ? (
            <SkeletonRow />
          ) : userDetail ? (
            <div className="space-y-4">
              {/* Header */}
              <div className="glass-card p-4">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-12 h-12 rounded-full bg-primary-600/30 flex items-center justify-center text-2xl">
                    👤
                  </div>
                  <div>
                    <div className="font-bold text-lg">
                      {userDetail.user.first_name || 'بدون نام'}
                      {userDetail.user.last_name && ` ${userDetail.user.last_name}`}
                    </div>
                    <div className="text-sm text-dark-400">
                      @{userDetail.user.username || '—'} · {userDetail.user.telegram_id}
                    </div>
                  </div>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { label: '📁 فایل‌ها', value: userDetail.stats.files_count },
                    { label: '📂 پوشه‌ها', value: userDetail.stats.folders_count },
                    { label: '❤️ لایک‌ها', value: userDetail.stats.liked_tracks },
                    { label: '🎵 تاریخچه', value: userDetail.stats.history_count },
                    { label: '⬇️ دانلودها', value: userDetail.stats.downloads_count },
                    { label: '📋 پلی‌لیست', value: userDetail.stats.playlists_count },
                    { label: '📺 تماشا', value: userDetail.stats.watch_progress_count },
                    { label: '💾 فضا', value: `${userDetail.stats.storage_mb} MB` },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-white/5 rounded p-2 text-center">
                      <div className="text-lg font-bold">{value}</div>
                      <div className="text-[10px] text-dark-400">{label}</div>
                    </div>
                  ))}
                </div>

                <div className="text-xs text-dark-500 mt-2">
                  عضویت: {new Date(userDetail.user.created_at).toLocaleDateString('fa-IR')} ·
                  آخرین فعالیت: {new Date(userDetail.user.last_active).toLocaleString('fa-IR')}
                </div>
              </div>

              {/* Recent Files */}
              {userDetail.recent_files.length > 0 && (
                <div className="glass-card p-4">
                  <h3 className="font-bold text-sm mb-2">📁 آخرین فایل‌ها</h3>
                  <div className="space-y-1">
                    {userDetail.recent_files.map((f) => (
                      <div key={f.id} className="text-xs flex justify-between py-1 border-b border-white/5">
                        <span className="truncate mr-2">{f.file_name}</span>
                        <span className="text-dark-400 shrink-0">
                          {(f.file_size / 1024 / 1024).toFixed(1)} MB
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Plays */}
              {userDetail.recent_plays.length > 0 && (
                <div className="glass-card p-4">
                  <h3 className="font-bold text-sm mb-2">🎵 آخرین پخش‌ها</h3>
                  <div className="space-y-1">
                    {userDetail.recent_plays.map((p, i) => (
                      <div key={i} className="text-xs flex justify-between py-1 border-b border-white/5">
                        <span className="truncate mr-2">{p.track_title}</span>
                        <span className="text-dark-400 shrink-0">
                          {new Date(p.played_at).toLocaleString('fa-IR')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recent Downloads */}
              {userDetail.recent_downloads.length > 0 && (
                <div className="glass-card p-4">
                  <h3 className="font-bold text-sm mb-2">⬇️ آخرین دانلودها</h3>
                  <div className="space-y-1">
                    {userDetail.recent_downloads.map((d, i) => (
                      <div key={i} className="text-xs flex justify-between py-1 border-b border-white/5">
                        <span className="truncate mr-2">{d.track_title}</span>
                        <span className="text-dark-400 shrink-0">
                          {d.status} · {d.progress}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {userDetail.recent_files.length === 0 &&
                userDetail.recent_plays.length === 0 &&
                userDetail.recent_downloads.length === 0 && (
                  <div className="glass-card p-6 text-center text-dark-400 text-sm">
                    این کاربر هنوز فعالیتی نداشته است
                  </div>
                )}
            </div>
          ) : (
            <div className="glass-card p-6 text-center text-dark-400">
              یک کاربر را از لیست انتخاب کنید
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
