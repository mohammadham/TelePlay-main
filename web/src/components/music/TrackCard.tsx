import { Play, Heart, Download } from 'lucide-react'
import { MusicTrack } from '../../lib/api'

export interface TrackCardProps {
  track: MusicTrack
  onPlay: () => void
  onLike?: () => void
  isLiked?: boolean
  onDownload?: () => void
  downloading?: boolean
  isVideo?: boolean
}

export default function TrackCard({
  track,
  onPlay,
  onLike,
  isLiked = false,
  onDownload,
  downloading = false,
  isVideo = false,
}: TrackCardProps) {
  const cover = track.cover_url || track.thumbnail_url

  return (
    <div className="card-spotify group p-3 flex flex-col gap-3">
      <div className="relative aspect-square rounded-md overflow-hidden bg-[#282828]">
        {cover ? (
          <img
            src={cover}
            alt={track.title}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">
            {isVideo ? '🎬' : '🎵'}
          </div>
        )}

        {/* Play button */}
        <button
          onClick={onPlay}
          className="absolute bottom-2 right-2 w-10 h-10 rounded-full bg-[#1DB954] text-black flex items-center justify-center shadow-lg opacity-0 translate-y-2 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-200 hover:scale-105 hover:bg-[#1ed760]"
        >
          <Play className="w-5 h-5 ml-0.5 fill-black" />
        </button>

        {/* Explicit badge */}
        {track.explicit && (
          <span className="absolute top-2 left-2 text-[10px] bg-white/90 text-black px-1 rounded font-bold">
            E
          </span>
        )}

        {/* Media type badge */}
        {isVideo && (
          <span
            className={`absolute top-2 right-2 text-[10px] px-1.5 py-0.5 rounded font-bold ${
              track.media_type === 'reel'
                ? 'bg-purple-600 text-white'
                : 'bg-red-600 text-white'
            }`}
          >
            {track.media_type === 'reel' ? 'Reel' : 'MV'}
          </span>
        )}
      </div>

      <div className="min-w-0">
        <p className="text-sm font-semibold text-white truncate">{track.title}</p>
        <p className="text-xs text-white/60 truncate">{track.artist?.name || 'Unknown Artist'}</p>
      </div>

      <div className="flex items-center justify-between text-xs text-white/40">
        <span>
          {track.duration
            ? `${Math.floor(track.duration / 60)}:${String(track.duration % 60).padStart(2, '0')}`
            : ''}
        </span>
        <div className="flex gap-1">
          {onDownload && (
            <button
              onClick={onDownload}
              className={`p-1 rounded ${downloading ? 'text-[#1DB954]' : 'hover:text-white'}`}
              title="Download"
            >
              <Download className="w-4 h-4" />
            </button>
          )}
          {onLike && (
            <button
              onClick={onLike}
              className={`p-1 rounded ${isLiked ? 'text-[#1DB954]' : 'hover:text-white'}`}
              title={isLiked ? 'Unlike' : 'Like'}
            >
              <Heart className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function TrackCardSkeleton() {
  return (
    <div className="p-3 flex flex-col gap-3">
      <div className="relative aspect-square rounded-md overflow-hidden bg-[#282828] animate-pulse" />
      <div className="min-w-0 space-y-2">
        <div className="h-4 bg-[#282828] rounded animate-pulse w-3/4" />
        <div className="h-3 bg-[#282828] rounded animate-pulse w-1/2" />
      </div>
      <div className="flex items-center justify-between">
        <div className="h-3 bg-[#282828] rounded animate-pulse w-12" />
        <div className="flex gap-1">
          <div className="w-6 h-6 bg-[#282828] rounded animate-pulse" />
          <div className="w-6 h-6 bg-[#282828] rounded animate-pulse" />
        </div>
      </div>
    </div>
  )
}
