import { useState, useRef, useEffect } from 'react'
import { Play, Pause, SkipBack, SkipForward, Volume2, Shuffle, Repeat, Maximize2, Minimize2 } from 'lucide-react'
import { useMusicStore } from '../../lib/musicStore'
import { api } from '../../lib/api'

export default function NowPlayingBar() {
  const { currentTrack, isPlaying, queue, queueIndex, setPlaying, playNext, playPrev, setShuffle, shuffle } = useMusicStore()
  const mediaRef = useRef<HTMLAudioElement | HTMLVideoElement>(null)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.9)
  const [isMini, setIsMini] = useState(false)

  const isVideo = currentTrack?.media_type === 'music_video' || currentTrack?.media_type === 'reel'
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  const src = currentTrack ? `${currentTrack.stream_url}?token=${token}` : ''

  useEffect(() => {
    if (!mediaRef.current) return
    if (isPlaying) (mediaRef.current as any).play().catch(() => {})
    else (mediaRef.current as any).pause()
  }, [isPlaying, currentTrack])

  useEffect(() => {
    if (!currentTrack) return
    api.post('/v1/music/history', { track_id: currentTrack.id }).catch(() => {})
    api.get('/ads/next', { params: { play_count: queueIndex + 1 } }).then(r => {
      if (r.data?.ad) console.log('Ad due', r.data)
    }).catch(() => {})
  }, [currentTrack?.id])

  if (!currentTrack) return null

  const formatTime = (seconds: number) => {
    if (!seconds) return '0:00'
    return `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    setProgress(time)
    if (mediaRef.current) (mediaRef.current as any).currentTime = time
  }

  return (
    <div
      className={`fixed left-0 right-0 bg-[#181818] border-t border-white/10 z-40 transition-all duration-300 ${
        isVideo ? (isMini ? 'bottom-0 h-14' : 'bottom-0') : 'bottom-0 h-[90px]'
      }`}
    >
      {/* Video player */}
      {isVideo && !isMini && (
        <div className="relative w-full aspect-video bg-black">
          {isVideo ? (
            <video
              ref={mediaRef as any}
              src={src}
              className="w-full h-full object-contain"
              onTimeUpdate={(e) => setProgress((e.target as HTMLVideoElement).currentTime)}
              onLoadedMetadata={(e) => setDuration((e.target as HTMLVideoElement).duration)}
              onEnded={playNext}
            />
          ) : (
            <audio
              ref={mediaRef as any}
              src={src}
              onTimeUpdate={(e) => setProgress((e.target as HTMLAudioElement).currentTime)}
              onLoadedMetadata={(e) => setDuration((e.target as HTMLAudioElement).duration)}
              onEnded={playNext}
            />
          )}
          <button
            onClick={() => setIsMini(true)}
            className="absolute top-2 right-2 bg-black/50 hover:bg-black/70 text-white p-1.5 rounded-full transition"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Controls bar */}
      <div className={`flex items-center px-4 gap-4 h-[90px] ${isVideo && !isMini ? '-mt-[calc(100%-90px)]' : ''}`}>
        {/* Track info */}
        <div className="flex items-center gap-3 w-[30%] min-w-0">
          <div className="w-14 h-14 rounded bg-[#282828] flex items-center justify-center overflow-hidden shrink-0">
            {currentTrack.cover_url ? (
              <img src={currentTrack.cover_url} className="w-full h-full object-cover" />
            ) : (
              <span className="text-2xl">🎵</span>
            )}
          </div>
          <div className="min-w-0">
            <p className="text-sm text-white truncate">{currentTrack.title}</p>
            <p className="text-xs text-white/60 truncate">{currentTrack.artist?.name}</p>
          </div>
          {isVideo && (
            <button onClick={() => setIsMini(false)} className="text-white/60 hover:text-white ml-1">
              <Maximize2 className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Controls */}
        <div className="flex-1 flex flex-col items-center gap-2 max-w-[640px]">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setShuffle(!shuffle)}
              className={`${shuffle ? 'text-[#1DB954]' : 'text-white/60'} hover:text-white transition-colors`}
            >
              <Shuffle className="w-4 h-4" />
            </button>
            <button onClick={playPrev} className="text-white/80 hover:text-white transition-colors">
              <SkipBack className="w-5 h-5 fill-white/80" />
            </button>
            <button
              onClick={() => setPlaying(!isPlaying)}
              className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center hover:scale-105 transition-transform"
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 ml-0.5 fill-black" />}
            </button>
            <button onClick={playNext} className="text-white/80 hover:text-white transition-colors">
              <SkipForward className="w-5 h-5 fill-white/80" />
            </button>
            <button className="text-white/60 hover:text-white transition-colors">
              <Repeat className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center gap-2 w-full">
            <span className="text-xs text-white/60 w-10 text-right">{formatTime(progress)}</span>
            <input
              type="range"
              min={0}
              max={duration || 1}
              step={0.1}
              value={progress}
              onChange={handleSeek}
              className="flex-1 h-1 bg-white/20 rounded-full accent-[#1DB954] cursor-pointer"
            />
            <span className="text-xs text-white/60 w-10">{formatTime(duration)}</span>
          </div>
        </div>

        {/* Volume */}
        <div className="w-[30%] flex items-center justify-end gap-2">
          <Volume2 className="w-4 h-4 text-white/60" />
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={(e) => {
              const v = parseFloat(e.target.value)
              setVolume(v)
              if (mediaRef.current) (mediaRef.current as any).volume = v
            }}
            className="w-24 accent-[#1DB954] cursor-pointer"
          />
        </div>
      </div>

      {/* Mini video bar */}
      {isVideo && isMini && (
        <div className="h-14 flex items-center px-4 gap-4">
          <div className="w-10 h-10 rounded bg-[#282828] flex items-center justify-center">
            <span className="text-lg">🎬</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate">{currentTrack.title}</p>
            <p className="text-xs text-white/60 truncate">{currentTrack.artist?.name}</p>
          </div>
          <button onClick={() => setIsMini(false)} className="text-white/60 hover:text-white">
            <Maximize2 className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  )
}
