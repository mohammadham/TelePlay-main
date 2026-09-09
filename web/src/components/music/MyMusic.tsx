/**
 * My Music — users create tracks from their existing Telegram file library.
 */
import { useEffect, useState, useRef, ChangeEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient, useMutation } from '@tanstack/react-query'
import { api, useMyMusicTracks, TelegramFile } from '../../lib/api'
import TrackCard from './TrackCard'
import Progress from '../Progress'
import { useMusicStore } from '../../lib/musicStore'
import { useAppStore } from '../../lib/store'
import { Plus, Headphones, X, Upload, Search, Bot } from 'lucide-react'
import { useSEO } from '../../hooks/useSEO'

type MediaType = 'all' | 'audio' | 'music_video' | 'reel'

export default function MyMusic() {
  const navigate = useNavigate()
  useSEO({ title: 'My Music', description: 'Create and manage your music tracks', type: 'website' })
  const { setQueue } = useMusicStore()
  const { setPreviewFile } = useAppStore()
  const qc = useQueryClient()
  const { data: tracks, isLoading: tracksLoading } = useMyMusicTracks()
  const [showUpload, setShowUpload] = useState(false)
  const [mediaType, setMediaType] = useState<MediaType>('all')
  const [searchQ, setSearchQ] = useState('')
  const [isSearchingFiles, setIsSearchingFiles] = useState(false)
  const [fileSearchResults, setFileSearchResults] = useState<TelegramFile[]>([])
  const [myMusicDisabled, setMyMusicDisabled] = useState(false)

  useEffect(() => {
    async function checkMyMusicStatus() {
      try {
        const { data } = await api.get('/admin/settings')
        const myMusicSetting = data.find((s: any) => s.key === 'MY_MUSIC_ENABLED')
        setMyMusicDisabled(!(myMusicSetting && myMusicSetting.value === 'true'))
      } catch (error) {
        console.error('Failed to check My Music status:', error)
        // Default to enabled if we can't check
        setMyMusicDisabled(false)
      }
    }
    checkMyMusicStatus()
  }, [])

  // Upload form state
  const [formTitle, setFormTitle] = useState('')
  const [formArtist, setFormArtist] = useState('')
  const [formAlbum, setFormAlbum] = useState('')
  const [formDuration, setFormDuration] = useState('')
  const [formGenre, setFormGenre] = useState('')
  const [formMediaType, setFormMediaType] = useState<'audio' | 'music_video' | 'reel'>('audio')
  const [selectedFileId, setSelectedFileId] = useState<number | null>(null)
  const [selectedFile, setSelectedFile] = useState<TelegramFile | null>(null)
  const [webFile, setWebFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [uploadStatus, setUploadStatus] = useState<string>('')
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [isFormLocked, setIsFormLocked] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
    mutationFn: async (payload: { title: string; artist_name: string; file_id: number; album_title?: string; duration?: number; genre?: string; media_type: 'audio' | 'music_video' | 'reel' }) => {
      return api.post('/v1/music/my/upload', payload)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['my-music-tracks'] })
      qc.invalidateQueries({ queryKey: ['music-tracks'] })
      setShowUpload(false)
      resetForm()
    },
    onError: (e: any) => {
      console.error('Upload failed:', e)
      let errorMessage = 'Upload failed'
      if (e.response && e.response.data) {
        errorMessage = e.response.data.detail || 'Upload failed'
      } else if (e.message) {
        errorMessage = e.message
      }
      setUploadError(errorMessage)
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
    setWebFile(null)
    setFileSearchResults([])
  }

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0]
      // Store the raw browser File for upload
      setWebFile(file)
      // Create a display object - file_id here will be DB row ID after upload
      setSelectedFile({
        id: Date.now(),
        user_id: 0,
        folder_id: null,
        file_id: Date.now().toString(),
        file_unique_id: `web_${Date.now()}`,
        file_name: file.name,
        file_size: file.size,
        mime_type: file.type || null,
        file_type: 'audio',
        duration: null,
        width: null,
        height: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        stream_url: '',
        thumbnail_url: null,
      } as TelegramFile)
      setUploadError(null)
      setUploadStatus('')
    }
  }

  const handleUpload = async () => {
    if (!formTitle.trim() || !formArtist.trim() || (!selectedFileId && !webFile)) return

    // Lock form and show upload progress
    setUploading(true)
    setIsFormLocked(true)
    setUploadProgress(0)
    setUploadStatus('Uploading file...')
    setUploadError(null)

    try {
      let fileId: number | null = selectedFileId ?? null
      let isWebUpload = false

      // If we have a web file (not from Telegram search), upload it first
      if (webFile && !fileId) {
        const formData = new FormData()
        formData.append('file', webFile)

        // Upload file to get DB file_id
        const uploadResponse = await api.post('/upload', formData, {
          headers: {
            'Content-Type': 'multipart/form-data'
          },
          onUploadProgress: (progressEvent) => {
            const total = progressEvent.total || webFile.size
            const percentCompleted = Math.round((progressEvent.loaded * 100) / total)
            setUploadProgress(percentCompleted)
          }
        })

        // uploadResponse returns { file_id: str(db_file.id), ... }
        // Convert to integer since Track.file_id is ForeignKey to files.id (int)
        fileId = parseInt(uploadResponse.data.file_id, 10)
        isWebUpload = true
      }

      if (!fileId) {
        throw new Error('No file selected')
      }

      // If this was a web upload, we need to store the file_id in selectedFile
      // for the uploadTrack mutation which expects it as the file_id parameter
      if (isWebUpload && webFile) {
        // After upload, the file_id is set correctly by the upload step
        // but we need to make sure selectedFileId is updated
        setSelectedFileId(fileId)
      }

      // Now use the file_id to create the track
      // For web uploads: file_id is File.id (FK to files.id)
      // For Telegram uploads: file_id is File.id (FK to files.id)
      await uploadTrack.mutateAsync({
        title: formTitle.trim(),
        artist_name: formArtist.trim(),
        file_id: fileId,
        album_title: formAlbum.trim() || undefined,
        duration: formDuration ? parseInt(formDuration) : undefined,
        genre: formGenre.trim() || undefined,
        media_type: formMediaType
      })

      // After successful upload
      setUploadProgress(100)
      setUploadStatus(isWebUpload ? 'File uploaded and track created!' : 'Track created successfully!')

      // Close modal after delay
      setTimeout(() => {
        setUploadStatus('')
        setShowUpload(false)
        resetForm()
      }, 2000)
    } catch (error) {
      setUploadProgress(0)
      setUploadStatus('')
      setUploadError(error instanceof Error ? error.message : 'Upload failed')
      setUploading(false)
      setIsFormLocked(false)
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
            <Headphones className="w-16 h-16 mb-4 opacity-30" />
            <p className="text-lg font-medium text-white/50">
              {searchQ ? 'No tracks match your search' : 'No tracks yet'}
            </p>
            <p className="text-sm mt-2">
              {searchQ ? 'Try a different search term' : 'Upload files via Telegram bot, then add them here'}
            </p>
            {!searchQ && !myMusicDisabled && (
              <button
                onClick={() => setShowUpload(true)}
                className="mt-6 flex items-center gap-2 px-5 py-2.5 bg-[#1DB954] text-black font-semibold rounded-full hover:bg-[#1ed760] transition-all"
              >
                <Plus className="w-5 h-5" />
                Add First Track
              </button>
            )}
            {myMusicDisabled && (
              <div className="mt-6 text-center">
                <p className="text-sm text-yellow-400">This feature is disabled by admin</p>
              </div>
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
      {showUpload && !myMusicDisabled && (
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
                    <button onClick={() => { setSelectedFile(null); setSelectedFileId(null); setWebFile(null) }} className="text-white/40 hover:text-white">
                      <X className="w-5 h-5" />
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    {/* Web upload button */}
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      disabled={isFormLocked}
                      className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-[#282828] border border-dashed border-white/20 rounded-lg text-white/60 hover:bg-[#282828]/80 hover:border-[#1DB954]/50 hover:text-[#1DB954] transition-all disabled:opacity-40 disabled:cursor-not-allowed mb-3"
                    >
                      <Upload className="w-5 h-5" />
                      <span className="text-sm font-medium">Upload from computer (Web)</span>
                    </button>
                    <input
                      ref={fileInputRef}
                      type="file"
                      accept="audio/*,video/*"
                      className="hidden"
                      onChange={handleFileSelect}
                      disabled={isFormLocked}
                    />
                    <div className="flex items-center gap-2 mt-2">
                      <span className="text-white/20 text-xs">or</span>
                      <span className="text-white/20 text-xs">Choose from your Telegram file library</span>
                    </div>
                    <button
                      onClick={() => navigate('/files')}
                      className="flex items-center gap-2 px-3 py-1.5 mt-2 text-sm text-white/60 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    >
                      <Bot className="w-4 h-4" />
                      <span>Browse files via Telegram bot</span>
                    </button>
                    <div className="flex gap-2 mt-2">
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
                            <Headphones className="w-5 h-5 text-[#1DB954] shrink-0" />
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
                      <p className="text-xs text-white/30 mt-2 text-center">Send files to Telegram bot first, then choose here</p>
                    )}
                  </div>
                )}
                {/* Upload progress */}
                {uploading && (
                  <div className="mt-3 space-y-2">
                    <div className="flex items-center justify-between text-xs text-white/50">
                      <span>{uploadStatus}</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <Progress value={uploadProgress} className="w-full" />
                    <button
                      onClick={() => { setUploading(false); setIsFormLocked(false); setUploadStatus(''); setUploadProgress(0); }}
                      className="text-xs text-red-400 hover:text-red-300 underline"
                    >
                      Cancel upload
                    </button>
                  </div>
                )}
                {uploadError && (
                  <p className="mt-2 text-sm text-red-400">{uploadError}</p>
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
                disabled={uploading}
                className="flex-1 px-4 py-2.5 rounded-lg text-white/60 hover:bg-white/5 transition-colors font-medium disabled:opacity-40"
              >
                Cancel
              </button>
              <button
                onClick={handleUpload}
                disabled={!formTitle.trim() || !formArtist.trim() || (!selectedFileId && !webFile) || uploading}
                className="flex-1 px-4 py-2.5 rounded-lg bg-[#1DB954] text-black font-semibold hover:bg-[#1ed760] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {uploading ? (
                  <><div className="w-4 h-4 border-2 border-black/30 border-t-black rounded-full animate-spin" /> Uploading...</>
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
