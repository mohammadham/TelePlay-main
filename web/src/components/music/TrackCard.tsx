import { Play, Heart, MoreVertical, Download, ListPlus, Share2 } from 'lucide-react'

export interface TrackCardProps {
  track: any
  onPlay: () => void
  onLike?: () => void
  isLiked?: boolean
  onAddQueue?: () => void
}

export default function TrackCard({ track, onPlay, onLike, isLiked }: TrackCardProps) {
  const cover = track.cover_url || track.thumbnail_url
  return (
    <div className="group glass-card p-3 card-hover flex flex-col gap-3 relative">
      <div className="relative aspect-square rounded-lg overflow-hidden bg-dark-800 flex items-center justify-center">
        {cover ? (
          <img src={cover} alt={track.title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <span className="text-4xl">🎵</span>
        )}
        <button
          onClick={onPlay}
          className="absolute bottom-2 right-2 w-10 h-10 rounded-full bg-[#1DB954] text-black flex items-center justify-center shadow-lg opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-200 hover:scale-105 hover:bg-[#1ed760]"
        >
          <Play className="w-5 h-5 ml-0.5 fill-black" />
        </button>
        {track.explicit && <span className="absolute top-2 left-2 text-[10px] bg-white/90 text-black px-1 rounded font-bold">E</span>}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold truncate text-white">{track.title}</p>
        <p className="text-xs truncate text-dark-400">{track.artist?.name || 'Unknown Artist'}</p>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-dark-500">{track.duration ? Math.floor(track.duration/60)+':'+String(track.duration%60).padStart(2,'0') : ''}</span>
        <div className="flex gap-1">
          <button onClick={onLike} className={`p-1 rounded ${isLiked?'text-[#1DB954]':'text-dark-400 hover:text-white'}`}><Heart className={`w-4 h-4 ${isLiked?'fill-current':''}`} /></button>
          <button className="p-1 text-dark-400 hover:text-white"><MoreVertical className="w-4 h-4" /></button>
        </div>
      </div>
    </div>
  )
}
