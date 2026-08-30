import { useQuery } from '@tanstack/react-query'
import { api } from '../../lib/api'
import Hero from './Hero'
import VideoRow from './VideoRow'
import { useAppStore } from '../../lib/store'

export default function VideoHome() {
  const { data } = useQuery({ queryKey: ['video-browse'], queryFn: async () => (await api.get('/v1/video/browse')).data })
  const { setPreviewFile } = useAppStore()

  const play = (m:any) => {
    // reuse existing File preview: create pseudo TelegramFile
    setPreviewFile({ id: m.file_id, file_name: m.title, file_type: 'video', stream_url: m.stream_url, file_size: 0, mime_type: 'video/mp4' } as any)
  }

  return (
    <div className="bg-[#121212] min-h-screen text-white pb-10">
      <Hero movie={data?.hero} onPlay={()=> data?.hero && play(data.hero)} />
      <div className="space-y-6 mt-6">
        {data?.continue_watching?.length > 0 && <VideoRow title="Continue Watching" movies={data.continue_watching} onPlay={play} />}
        {Object.entries(data?.by_genre || {}).map(([genre, movies]: any) => <VideoRow key={genre} title={genre} movies={movies} onPlay={play} />)}
        {!data && <p className="px-6 text-dark-400">No movies yet — admin upload via bot + create movie.</p>}
      </div>
      <div className="px-6 mt-8 glass-card p-3 text-xs text-dark-400">Ad • pre-roll 15s skippable after 5s (future IMA)</div>
    </div>
  )
}
