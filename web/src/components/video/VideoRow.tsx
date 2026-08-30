import VideoCard from './VideoCard'

export default function VideoRow({ title, movies, onPlay }: { title: string; movies: any[]; onPlay: (m:any)=>void }) {
  if (!movies?.length) return null
  return (
    <div className="space-y-2">
      <h3 className="text-lg font-bold px-6">{title}</h3>
      <div className="flex gap-3 overflow-x-auto no-scrollbar px-6 pb-2">
        {movies.map((m) => <VideoCard key={m.id} movie={m} onPlay={()=>onPlay(m)} />)}
      </div>
    </div>
  )
}
