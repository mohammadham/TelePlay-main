import { useState, useRef, useEffect } from 'react'
import { Play, Pause, SkipBack, SkipForward, Volume2, VolumeX, Shuffle, Repeat, Maximize2, Minimize2, Mic2, Disc, List } from 'lucide-react'
import { useMusicStore } from '../../lib/musicStore'
import { api } from '../../lib/api'
import QueuePanel from './QueuePanel'

export default function NowPlayingBar() {
  const { currentTrack, isPlaying, queueIndex, shuffle, repeat, setShuffle, setRepeat, setPlaying, playNext, playPrev } = useMusicStore()
  const mediaRef = useRef<HTMLAudioElement | HTMLVideoElement>(null)
  const progressRef = useRef<HTMLInputElement>(null)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(() => {
    const saved = localStorage.getItem('volume')
    return saved ? parseFloat(saved) : 0.9
  })
  const [isMuted, setIsMuted] = useState(false)
  const [isMini, setIsMini] = useState(false)
  const [showQueue, setShowQueue] = useState(false)

  // Persist volume
  useEffect(() => {
    localStorage.setItem('volume', String(volume))
    if (mediaRef.current) (mediaRef.current as any).volume = volume
  }, [volume])

  const isVideo = currentTrack?.media_type === 'music_video' || currentTrack?.media_type === 'reel'
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  const src = currentTrack ? `${currentTrack.stream_url}?token=${token}` : ''

  // Play/pause sync with store
  useEffect(() => {
    if (!mediaRef.current) return
    if (isPlaying) (mediaRef.current as any).play().catch(() => setPlaying(false))
    else (mediaRef.current as any).pause()
  }, [isPlaying, currentTrack, setPlaying])

  // Track history + ad check (fire-and-forget, non-critical)
  useEffect(() => {
    if (!currentTrack) return
    api.post('/v1/music/history', { track_id: currentTrack.id }).catch(console.error)
    api.get('/ads/next', { params: { play_count: queueIndex + 1 } }).catch(() => {})
  }, [currentTrack?.id, queueIndex])

  // Auto-advance on end
  const handleEnded = () => {
    if (repeat === 'one') {
      const el = mediaRef.current
      if (el) {
        ;(el as any).currentTime = 0
        ;(el as any).play().catch(() => {})
      }
    } else {
      playNext()
    }
  }

  if (!currentTrack) return null

  const formatTime = (seconds: number) => {
    if (!seconds || !isFinite(seconds)) return '0:00'
    const m = Math.floor(seconds / 60)
    const s = Math.floor(seconds % 60)
    return `${m}:${s.toString().padStart(2, '0')}`
  }

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value)
    setProgress(time)
    if (mediaRef.current) (mediaRef.current as any).currentTime = time
  }

  const togglePlay = () => setPlaying(!isPlaying)
  const prevTrack = () => {
    if (progress > 3) {
      if (mediaRef.current) (mediaRef.current as any).currentTime = 0
      setProgress(0)
    } else {
      playPrev()
    }
  }
  const nextTrack = () => playNext()

  const setShuffleToggle = () => setShuffle(!shuffle)
  const toggleRepeat = () => setRepeat(repeat === 'off' ? 'all' : repeat === 'all' ? 'one' : 'off')

  const volumeDisplay = isMuted ? 0 : volume
  const toggleMute = () => {
    setIsMuted(!isMuted)
    setVolume(isMuted ? 0.9 : 0)
  }

  // ---- LEFT: track info ----
  const LeftSection = () => (
    <div className="flex items-center gap-3 w-[30%] min-w-0">
      <div className="w-12 h-12 rounded overflow-hidden bg-[#282828] shrink-0 group cursor-pointer hover:opacity-80 transition-opacity">
        {currentTrack.cover_url ? (
          <img src={currentTrack.cover_url} alt="" className="w-full h-full object-cover" />
        ) : (
          <Disc className="w-6 h-6 text-white/40 mx-auto mt-3" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm text-white truncate font-medium leading-tight">{currentTrack.title}</p>
        <p className="text-xs text-white/60 truncate leading-tight">{currentTrack.artist?.name || 'Unknown Artist'}</p>
      </div>
    </div>
  )

  // ---- CENTER: controls ----
  const CenterSection = ({ compact }: { compact?: boolean }) => (
    <div className={`flex flex-col items-center gap-1 ${compact ? 'gap-0' : ''}`}>
      <div className="flex items-center gap-3">
        <button
          onClick={setShuffleToggle}
          className={`transition-colors ${shuffle ? 'text-[#1DB954]' : 'text-white/50 hover:text-white'}`}
          title="Shuffle"
        >
          <Shuffle className="w-4 h-4" />
        </button>
        <button onClick={prevTrack} className="text-white/70 hover:text-white transition-colors" title="Previous">
          <SkipBack className="w-5 h-5 fill-current" />
        </button>
        <button
          onClick={togglePlay}
          className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center hover:scale-105 active:scale-95 transition-transform"
          title={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 ml-0.5 fill-black" />}
        </button>
        <button onClick={nextTrack} className="text-white/70 hover:text-white transition-colors" title="Next">
          <SkipForward className="w-5 h-5 fill-current" />
        </button>
        <button
          onClick={toggleRepeat}
          className={`relative transition-colors ${repeat !== 'off' ? 'text-[#1DB954]' : 'text-white/50 hover:text-white'}`}
          title="Repeat"
        >
          <Repeat className="w-4 h-4" />
          {repeat === 'one' && (
            <span className="absolute -top-1 -right-1 text-[8px] font-bold text-[#1DB954] leading-none">1</span>
          )}
        </button>
      </div>
      {!compact && (
        <div
          className="flex items-center gap-2 w-full"
          onMouseEnter={() => {}}
          onMouseLeave={() => {}}
        >
          <span className="text-xs text-white/60 w-10 text-right tabular-nums">{formatTime(progress)}</span>
          <div className="relative flex-1 group">
            <input
              ref={progressRef}
              type="range"
              min={0}
              max={duration || 1}
              step={0.1}
              value={progress}
              onChange={handleSeek}
              className="w-full h-1 appearance-none bg-white/20 rounded-full cursor-pointer accent-[#1DB954] hover:h-1.5 transition-all [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:opacity-0 [&::-webkit-slider-thumb]:transition-opacity hover:[&::-webkit-slider-thumb]:opacity-100 [&::-moz-range-thumb]:w-3 [&::-moz-range-thumb]:h-3 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-white [&::-moz-range-thumb]:border-0 [&::-moz-range-thumb]:opacity-0 hover:[&::-moz-range-thumb]:opacity-100"
            />
            {/* visible thumb on hover */}
            <div
              className="pointer-events-none absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white opacity-0 hover:opacity-100 transition-opacity shadow"
              style={{ left: duration ? `${(progress / duration) * 100}%` : '0%' }}
            />
          </div>
          <span className="text-xs text-white/60 w-10 tabular-nums">{formatTime(duration)}</span>
        </div>
      )}
    </div>
  )

  // ---- RIGHT: volume ----
  const RightSection = () => (
    <div className="flex items-center justify-end gap-2 w-[30%]">
      <button onClick={toggleMute} className="text-white/60 hover:text-white transition-colors">
        {volumeDisplay === 0 ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
      </button>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={volumeDisplay}
        onChange={(e) => { setVolume(parseFloat(e.target.value)); setIsMuted(false) }}
        className="w-24 h-1 accent-[#1DB954] cursor-pointer"
      />
    </div>
  )

  return (
    <>
      {/* Full-height mode: 90px for audio, auto for video (player above bar) */}
      <div
        className={`fixed left-0 right-0 bg-[#181818] border-t border-white/10 z-40 transition-all duration-300 ${
          isVideo && !isMini ? 'bottom-0 h-auto pb-[90px]' : 'bottom-0 h-[90px]'
        }`}
      >
        {/* Video player */}
        {isVideo && !isMini && (
          <div className="relative w-full bg-black">
            {isVideo ? (
              <video
                ref={mediaRef as any}
                src={src}
                className="w-full max-h-[220px] object-contain"
                onTimeUpdate={(e) => setProgress((e.target as HTMLVideoElement).currentTime)}
                onLoadedMetadata={(e) => setDuration((e.target as HTMLVideoElement).duration)}
                onEnded={handleEnded}
              />
            ) : (
              <audio ref={mediaRef as any} src={src} onEnded={handleEnded} />
            )}
            <button
              onClick={() => setIsMini(true)}
              className="absolute top-2 right-2 bg-black/60 hover:bg-black/80 text-white p-1.5 rounded-full transition"
              title="Minimize"
            >
              <Minimize2 className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Controls bar */}
        <div className="flex items-center px-4 gap-4 h-[90px]">
          <LeftSection />
          <CenterSection />
          <button
            onClick={() => setShowQueue(true)}
            className="text-white/50 hover:text-white transition-colors hidden md:block"
            title="Queue"
          >
            <List className="w-5 h-5" />
          </button>
          <RightSection />
        </div>
      </div>

      {/* Mini mode (video minimized to bar) */}
      {isVideo && isMini && (
        <div className="fixed left-0 right-0 bg-[#181818] border-t border-white/10 z-40 h-14 flex items-center px-4 gap-4">
          <div className="w-10 h-10 rounded overflow-hidden bg-[#282828] shrink-0">
            {currentTrack.cover_url ? (
              <img src={currentTrack.cover_url} alt="" className="w-full h-full object-cover" />
            ) : (
              <Mic2 className="w-5 h-5 text-white/40 mx-auto mt-2.5" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-white truncate font-medium">{currentTrack.title}</p>
            <p className="text-xs text-white/60 truncate">{currentTrack.artist?.name || 'Unknown Artist'}</p>
          </div>
          <CenterSection compact />
          <button
            onClick={() => setIsMini(false)}
            className="text-white/60 hover:text-white transition-colors ml-2"
            title="Expand"
          >
            <Maximize2 className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Queue Panel */}
      {showQueue && (
        <QueuePanel onClose={() => setShowQueue(false)} />
      )}
    </>
  )
}
