import { useEffect, useRef, useState } from 'react'
import { Play, Pause, SkipBack, SkipForward, Volume2, Repeat, Shuffle, Heart, Maximize2 } from 'lucide-react'
import { useMusicStore } from '../../lib/musicStore'
import { api } from '../../lib/api'

export default function NowPlayingBar() {
  const { currentTrack, isPlaying, queue, queueIndex, setPlaying, setCurrent, playNext, playPrev } = useMusicStore()
  const audioRef = useRef<HTMLAudioElement>(null)
  const [progress, setProgress] = useState(0)
  const [duration, setDuration] = useState(0)
  const [volume, setVolume] = useState(0.9)
  const [shuffle, setShuffle] = useState(false)

  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  const src = currentTrack ? `${currentTrack.stream_url}?token=${token}` : ''

  useEffect(() => {
    if (!audioRef.current) return
    if (isPlaying) audioRef.current.play().catch(()=>{})
    else audioRef.current.pause()
  }, [isPlaying, currentTrack])

  useEffect(() => {
    if (!currentTrack) return
    // play count + ad check
    api.post('/v1/music/history', { track_id: currentTrack.id }).catch(()=>{})
    // ad injection check
    api.get('/ads/next', { params: { play_count: queueIndex+1 } }).then(r=>{
      if (r.data?.ad) console.log('Ad due', r.data)
    }).catch(()=>{})
  }, [currentTrack?.id])

  if (!currentTrack) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 h-[84px] bg-[#181818] border-t border-white/10 flex items-center px-4 gap-4 z-40">
      <audio ref={audioRef} src={src} onTimeUpdate={e=>setProgress((e.target as HTMLAudioElement).currentTime)} onLoadedMetadata={e=>setDuration((e.target as HTMLAudioElement).duration)} onEnded={playNext} />
      <div className="flex items-center gap-3 w-[30%] min-w-0">
        <div className="w-14 h-14 rounded bg-dark-800 flex items-center justify-center overflow-hidden shrink-0">
          {currentTrack.cover_url ? <img src={currentTrack.cover_url} className="w-full h-full object-cover" /> : <span>🎵</span>}
        </div>
        <div className="min-w-0">
          <p className="text-sm text-white truncate">{currentTrack.title}</p>
          <p className="text-xs text-white/60 truncate">{currentTrack.artist?.name}</p>
        </div>
        <button className="ml-2 text-white/60 hover:text-white"><Heart className="w-4 h-4" /></button>
      </div>

      <div className="flex-1 flex flex-col items-center gap-2 max-w-[640px]">
        <div className="flex items-center gap-4">
          <button onClick={()=>setShuffle(!shuffle)} className={shuffle?'text-[#1DB954]':'text-white/60 hover:text-white'}><Shuffle className="w-4 h-4" /></button>
          <button onClick={playPrev} className="text-white/80 hover:text-white"><SkipBack className="w-5 h-5 fill-white/80" /></button>
          <button onClick={()=>setPlaying(!isPlaying)} className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center hover:scale-105 transition">
            {isPlaying ? <Pause className="w-4 h-4 fill-black" /> : <Play className="w-4 h-4 ml-0.5 fill-black" />}
          </button>
          <button onClick={playNext} className="text-white/80 hover:text-white"><SkipForward className="w-5 h-5 fill-white/80" /></button>
          <button className="text-white/60 hover:text-white"><Repeat className="w-4 h-4" /></button>
        </div>
        <div className="flex items-center gap-2 w-full">
          <span className="text-xs text-white/60 w-10 text-right">{Math.floor(progress/60)}:{String(Math.floor(progress%60)).padStart(2,'0')}</span>
          <div className="flex-1 h-1 bg-white/20 rounded group">
            <div className="h-full bg-white group-hover:bg-[#1DB954] rounded" style={{ width: duration? `${(progress/duration)*100}%` : '0%' }} />
          </div>
          <span className="text-xs text-white/60 w-10">{duration? Math.floor(duration/60)+':'+String(Math.floor(duration%60)).padStart(2,'0') : '0:00'}</span>
        </div>
      </div>

      <div className="w-[30%] flex items-center justify-end gap-2">
        <Volume2 className="w-4 h-4 text-white/60" />
        <input type="range" min={0} max={1} step={0.05} value={volume} onChange={e=>{ setVolume(parseFloat(e.target.value)); if(audioRef.current) audioRef.current.volume = parseFloat(e.target.value)}} className="w-24 accent-white" />
        <button className="text-white/60 hover:text-white"><Maximize2 className="w-4 h-4" /></button>
      </div>
    </div>
  )
}
