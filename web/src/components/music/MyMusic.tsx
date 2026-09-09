/**
 * My Music — users create tracks from their existing Telegram file library.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query'
import { api, useMyMusicTracks, TelegramFile } from '../../lib/api'
import TrackCard from './TrackCard'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'
import { Plus, Headphones, X, Upload, Search } from 'lucide-react'
import { useSEO } from '../../hooks/useSEO'

type MediaType = 'all' | 'audio' | 'music_video' | 'reel'

export default function MyMusic() {
  useSEO({ title: 'My Music', description: 'Create and manage your music tracks', type: 'website' })
  const navigate = useNavigate()
  const { setQueue } = useMusicStore()
  const { setPreviewFile } = useAppStore()
  const qc = useQueryClient()
  const { data: tracks, isLoading: tracksLoading } = useMyMusicTracks()
  const [showUpload, setShowUpload] = useState(false)
  const [mediaType, setMediaType] = useState<MediaType>('all')
  const [searchQ, setSearchQ] = useState('')
  const [isSearchingFiles, setIsSearchingFiles] = useState(false)
  const [fileSearchResults, setFileSearchResults] = useState<TelegramFile[]>([])

  // Upload form state
  const [formTitle, setFormTitle] = useState('')
  const [formArtist, setFormArtist] = useState('')
  const [formAlbum, setFormAlbum] = useState('')
  const [formDuration, setFormDuration] = useState('')
  const [formGenre, setFormGenre] = useState('')
  const [formMediaType, setFormMediaType] = useState<'audio' | 'music_video' | 'reel'>('audio')
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null)
  const [selectedFile, setSelectedFile] = useState<TelegramFile | null>(null)
  const [uploading, setUploading] = useState(false)

  const list = (Array.isArray(tracks) ? tracks : [])
    .filter(t => mediaType === 'all' || t.media_type === mediaType)
    .filter(t => !searchQ || t.title.toLowerCase().includes(searchQ.toLowerCase()))

  const playTrack = (track: any) => {
    if (track.media_type === 'music_video' || track.media_type === 'reel') {
      api.get(`/files/${track.file_id}`).then(r => {
        setPreviewFile(r.data as TelegramFile)
      }).catch(console.error)
    } else {
      setQueue(list, list.findIndex((t: any) => t.id === track.id))
    }
  }

  const searchFiles = async (q: string) => {
    if (!q.trim()) {
      setFileSearchResults([])
      return
    }
    setIsSearchingFiles(true)
    try {
      const { data } = await api.get<{ files: TelegramFile[] }>('/files', { params: { search: q, per_page: 20 } })
      setFileSearchResults(data?.files || [])
    } catch (e) {
      console.error('File search failed:', e)
    }
    setIsSearchingFiles(false)
  }

  const uploadTrack = useMutation({
    mutationFn: async () => {
      return api.post('/v1/music/my/upload', {
        title: formTitle.trim(),
        artist_name: formArtist.trim(),
        file_id: selectedFileId,
        album_title: formAlbum.trim() || undefined,
        duration: formDuration ? parseInt(formDuration) : undefined,
        genre: formGenre.trim() || undefined,
        media_type: formMediaType,
      })
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-music-tracks'] })
      qc.invalidateQueries({ queryKey: ['music-tracks'] })
      setShowUpload(false)
      resetForm()
    },
    onError: (e: any) => {
      console.error('Upload failed:', e)
      alert(e.response?.data?.detail || 'Upload failed')
    },
  })

  function resetForm() {
    setFormTitle('')
    setFormArtist('')
    setFormAlbum('')
    setFormDuration('')
    setFormGenre('')
    setFormMediaType('audio')
    setSelectedFileId(null)
    setSelectedFile(null)
    setFileSearchResults([])
  }

  const handleUpload = async () => {
    if (!formTitle.trim() || !formArtist.trim() || !selectedFileId) return
    setUploading(true)
    try {
      await uploadTrack.mutateAsync()
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#121212] text-white pb-28">
      {/* Header */}
      <div className="px-6 py-6 bg-gradient-to-b from-[#1DB954]/20 to-[#121212]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs font-medium text-white/60 uppercase tracking-wider mb-1">My Library</p>
            <h1 className="text-4xl font-bold">My Music</h1>
            <p className="text-white/50 text-sm mt-1">Create tracks from your uploaded files</p>
          </div>
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#1DB954] text-black font-semibold rounded-full hover:bg-[#1ed760] transition-all"
          >
            <Plus className="w-5 h-5" />
            Add Track
          </button>
        </div>

        {/* Filters */}
        <div className="flex gap-3 flex-wrap items-center">
          {(['all', 'audio', 'music_video', 'reel'] as MediaType[]).map(key => (
            <button
              key={key}
              onClick={() => setMediaType(key)}
              className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                mediaType === key
                  ? 'bg-[#1DB954] text-black'
                  : 'bg-white/10 text-white/70 hover:bg-white/15'
              }`}
            >
              {key === 'all' ? 'All' : key === 'audio' ? 'Audio' : key === 'music_video' ? 'Music Videos' : 'Reels'}
            </button>
          ))}
          <div className="ml-auto relative">
            <Search className="w-4 h-4 text-white/40 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              placeholder="Search tracks..."
              className="bg-white/10 text-white pl-9 pr-4 py-1.5 rounded-full text-sm placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50 w-40"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="px-6 py-6">
        {tracksLoading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="space-y-2.5">
                <div className="skeleton-spotify aspect-square rounded-md" />
                <div className="skeleton-spotify h-3.5 w-3/4 rounded" />
                <div className="skeleton-spotify h-3 w-1/2 rounded" />
              </div>
            ))}
          </div>
        ) : list.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-white/30">
            <Music className="w-16 h-16 mb-4 opacity-30" />
            <p className="text-lg font-medium text-white/50">
              {searchQ ? 'No tracks match your search' : 'No tracks yet'}
            </p>
            <p className="text-sm mt-2">
              {searchQ ? 'Try a different search term' : 'Upload files via Telegram bot, then add them here'}
            </p>
            {!searchQ && (
              <button
                onClick={() => setShowUpload(true)}
                className="mt-6 flex items-center gap-2 px-5 py-2.5 bg-[#1DB954] text-black font-semibold rounded-full hover:bg-[#1ed760] transition-all"
              >
                <Plus className="w-5 h-5" />
                Add First Track
              </button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {list.map((t: any) => (
              <TrackCard
                key={t.id}
                track={t}
                isVideo={t.media_type === 'music_video' || t.media_type === 'reel'}
                onPlay={() => playTrack(t)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUpload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-[#1a1a1a] border border-white/10 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="p-6 border-b border-white/10 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold">Add New Track</h2>
                <p className="text-white/50 text-sm mt-1">Select a file from your library</p>
              </div>
              <button onClick={() => { setShowUpload(false); resetForm() }} className="text-white/50 hover:text-white">
                <X className="w-6 h-6" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* File selector */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">Select File *</label>
                {selectedFile ? (
                  <div className="flex items-center gap-3 p-3 bg-[#282828] rounded-lg">
                    <Headphones className="w-8 h-8 text-[#1DB954]" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{selectedFile.file_name}</p>
                      <p className="text-xs text-white/50">
                        {(selectedFile.file_size / 1024 / 1024).toFixed(1)} MB
                      </p>
                    </div>
                    <button onClick={() => { setSelectedFile(null); setSelectedFileId(null) }} className="text-white/40 hover:text-white">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <div className="flex gap-2">
                      <input
                        value={searchQ}
                        onChange={e => { setSearchQ(e.target.value); searchFiles(e.target.value) }}
                        onKeyDown={e => { if (e.key === 'Enter') searchFiles(searchQ) }}
                        placeholder="Search your files..."
                        className="flex-1 bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
                      />
                      {isSearchingFiles && (
                        <div className="w-8 h-8 border-2 border-[#1DB954]/30 border-t-[#1DB954] rounded-full animate-spin" />
                      )}
                    </div>
                    {fileSearchResults.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-[#1a1a1a] border border-white/10 rounded-lg max-h-48 overflow-y-auto">
                        {fileSearchResults.map((f: TelegramFile) => (
                          <button
                            key={f.id}
                            onClick={() => { setSelectedFileId(f.id); setSelectedFile(f); setSearchQ(''); setFileSearchResults([]); }}
                            className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-white/5 text-left transition-colors"
                          >
                            <Music className="w-5 h-5 text-[#1DB954] shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">{f.file_name}</p>
                              <p className="text-xs text-white/40">{(f.file_size / 1024 / 1024).toFixed(1)} MB</p>
                            </div>
                          </button>
                        ))}
                      </div>
                    )}
                    {!isSearchingFiles && fileSearchResults.length === 0 && searchQ.length >= 2 && (
                      <p className="text-sm text-white/40 mt-2 text-center">No files found</p>
                    )}
                    {!searchQ && (
                      <p className="text-xs text-white/30 mt-2 text-center">Send files to the bot to add them to your library</p>
                    )}
                  </div>
                )}
              </div>

              {/* Title */}
              <input
                value={formTitle}
                onChange={e => setFormTitle(e.target.value)}
                placeholder="Track Title *"
                className="w-full bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
              />

              {/* Artist */}
              <input
                value={formArtist}
                onChange={e => setFormArtist(e.target.value)}
                placeholder="Artist Name *"
                className="w-full bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
              />

              {/* Album (optional) */}
              <input
                value={formAlbum}
                onChange={e => setFormAlbum(e.target.value)}
                placeholder="Album (optional)"
                className="w-full bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
              />

              {/* Duration + Genre row */}
              <div className="grid grid-cols-2 gap-3">
                <input
                  value={formDuration}
                  onChange={e => setFormDuration(e.target.value)}
                  placeholder="Duration (sec)"
                  className="bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
                />
                <input
                  value={formGenre}
                  onChange={e => setFormGenre(e.target.value)}
                  placeholder="Genre"
                  className="bg-[#282828] border border-white/10 rounded-lg px-4 py-2.5 text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-[#1DB954]/50"
                />
              </div>

              {/* Media type */}
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">Media Type</label>
                <div className="flex gap-2">
                  {(['audio', 'music_video', 'reel'] as const).map(type => (
                    <button
                      key={type}
                      onClick={() => setFormMediaType(type)}
                      className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all ${
                        formMediaType === type
                          ? 'bg-[#1DB954] text-black'
                          : 'bg-[#282828] text-white/60 hover:bg-white/10'
                      }`}
                    >
                      {type === 'audio' ? 'Audio' : type === 'music_video' ? 'Music Video' : 'Reel'}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="p-6 border-t border-white/10 flex gap-3">
              <button
                onClick={() => { setShowUpload(false); resetForm() }}
                className="flex-1 px-4 py-2.5 rounded-lg text-white/60 hover:bg-white/5 transition-colors font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!formTitle.trim() || !formArtist.trim() || !selectedFileId || uploading}
                className="flex-1 px-4 py-2.5 rounded-lg bg-[#1DB954] text-black font-semibold hover:bg-[#1ed760] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                ) : (
                  <><Upload className="w-4 h-4" /> Add Track</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
