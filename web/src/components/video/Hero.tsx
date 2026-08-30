export default function Hero({ movie, onPlay }: { movie: any; onPlay: () => void }) {
  if (!movie) return <div className="h-[400px] bg-dark-900 animate-pulse" />
  return (
    <div className="relative h-[480px] w-full overflow-hidden">
      <img src={movie.thumbnail_url} className="absolute inset-0 w-full h-full object-cover" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#121212] via-[#121212]/60 to-transparent" />
      <div className="absolute bottom-0 left-0 p-8 max-w-2xl space-y-3">
        <h1 className="text-4xl font-black drop-shadow-lg">{movie.title}</h1>
        <p className="text-sm text-white/80 line-clamp-2">{movie.description || `${movie.genre || ''} • ${movie.year || ''}`}</p>
        <div className="flex gap-3">
          <button onClick={onPlay} className="bg-white text-black px-6 py-2 rounded font-bold hover:bg-white/90">▶ Play</button>
          <button className="bg-white/20 backdrop-blur px-6 py-2 rounded font-bold hover:bg-white/30">＋ My List</button>
        </div>
      </div>
    </div>
  )
}
