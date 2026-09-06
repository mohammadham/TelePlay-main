import { Play, Heart, MoreVertical, Download, ListPlus, Share2 } from 'lucide-react'

export interface TrackCardProps {
  track: any
  onPlay: () => void
  onLike?: () => void
  isLiked?: boolean
  onAddQueue?: () => void
  isVideo?: boolean
  downloading?: boolean
  onDownload?: () => void
}

export default function TrackCard({
  track,
  onPlay,
  onLike,
  isLiked,
  isVideo = false,
  downloading = false,
  onDownload,
}: TrackCardProps) {
  const cover = track.cover_url || track.thumbnail_url
  return (
    <div className="group glass-card p-3 card-hover flex flex-col gap-3 relative">
      <div className="relative aspect-square rounded-lg overflow-hidden bg-dark-800 flex items-center justify-center">
        {cover ? (
          <img src={cover} alt={track.title} className="w-full h-full object-cover" loading="lazy" />
        ) : (
          <span className="text-4xl">{isVideo ? '🎬' : '🎵'}</span>
        )}
        {/* Play overlay for video tracks */}
        {isVideo && (
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
            <Play className="w-8 h-8 text-white fill-white" />
          </div>
        )}
        <button
          onClick={onPlay}
          className="absolute bottom-2 right-2 w-10 h-10 rounded-full bg-[#1DB954] text-black flex items-center justify-center shadow-lg opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-200 hover:scale-105 hover:bg-[#1ed760]"
        >
          {isVideo ? <Play className="w-5 h-5 ml-0.5 fill-black" /> : <Play className="w-5 h-5 ml-0.5 fill-black" />}
        </button>
        {track.explicit && <span className="absolute top-2 left-2 text-[10px] bg-white/90 text-black px-1 rounded font-bold">E</span>}
        {/* Media type badge */}
        {isVideo && (
          <span className={`absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded font-bold ${
            track.media_type === 'reel'
              ? 'bg-purple-600 text-white'
              : 'bg-red-600 text-white'
          }`}>
            {track.media_type === 'reel' ? 'Reel' : 'MV'}
          </span>
        )}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-semibold truncate text-white">{track.title}</p>
        <p className="text-xs truncate text-dark-400">{track.artist?.name || 'Unknown Artist'}</p>
      </div>
      <div className="flex items-center justify-between">
        <span className="text-xs text-dark-500">
          {track.duration ? Math.floor(track.duration / 60) + ':' + String(track.duration % 60).padStart(2, '0') : ''}
        </span>
        <div className="flex gap-1">
          {onDownload && (
            <button
              onClick={onDownload}
              className={`p-1 rounded ${downloading ? 'text-[#1DB954]' : 'text-dark-400 hover:text-white'}`}
              title="Download"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onLike}
            className={`p-1 rounded ${isLiked ? 'text-[#1DB954]' : 'text-dark-400 hover:text-white'}`}
          >
            <Heart className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
          </button>
          <button className="p-1 text-dark-400 hover:text-white">
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  )
}
