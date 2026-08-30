export default function VideoCard({ movie, onPlay }: { movie: any; onPlay: () => void }) {
  return (
    <div onClick={onPlay} className="min-w-[180px] w-[180px] cursor-pointer group">
      <div className="aspect-[2/3] rounded-md overflow-hidden bg-dark-800 relative">
        {movie.thumbnail_url ? <img src={movie.thumbnail_url} className="w-full h-full object-cover group-hover:scale-110 transition duration-300" /> : <div className="w-full h-full flex items-center justify-center text-3xl">🎬</div>}
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition" />
        <button className="absolute bottom-2 left-2 right-2 bg-white text-black text-xs font-bold py-1 rounded opacity-0 group-hover:opacity-100 transition">Play</button>
      </div>
      <p className="text-sm mt-1 truncate">{movie.title}</p>
      <p className="text-xs text-dark-400">{movie.year || ''} {movie.genre ? `• ${movie.genre}` : ''}</p>
    </div>
  )
}
