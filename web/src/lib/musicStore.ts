import { create } from 'zustand'

interface MusicState {
  currentTrack: any | null
  queue: any[]
  queueIndex: number
  isPlaying: boolean
  shuffle: boolean
  repeat: 'off' | 'all' | 'one'
  setShuffle: (s: boolean) => void
  setRepeat: (r: 'off' | 'all' | 'one') => void
  setCurrent: (track: any) => void
  setQueue: (tracks: any[], index: number) => void
  setPlaying: (p: boolean) => void
  playNext: () => void
  playPrev: () => void
}

export const useMusicStore = create<MusicState>((set, get) => ({
  currentTrack: null,
  queue: [],
  queueIndex: -1,
  isPlaying: false,
  shuffle: false,
  repeat: 'off',
  setShuffle: (s) => set({ shuffle: s }),
  setRepeat: (r) => set({ repeat: r === 'off' ? 'all' : r === 'all' ? 'one' : 'off' }),
  setCurrent: (track) => set({ currentTrack: track, isPlaying: true }),
  setQueue: (tracks, index) => set({ queue: tracks, queueIndex: index, currentTrack: tracks[index], isPlaying: true }),
  setPlaying: (p) => set({ isPlaying: p }),
  playNext: () => {
    const { queue, queueIndex, shuffle } = get()
    let nextIndex: number
    if (shuffle) {
      nextIndex = Math.floor(Math.random() * queue.length)
    } else {
      nextIndex = queueIndex + 1
      if (nextIndex >= queue.length) nextIndex = 0 // loop
    }
    set({ queueIndex: nextIndex, currentTrack: queue[nextIndex], isPlaying: true })
  },
  playPrev: () => {
    const { queue, queueIndex } = get()
    if (queueIndex > 0) set({ queueIndex: queueIndex-1, currentTrack: queue[queueIndex-1], isPlaying: true })
  },
  removeTrack: (index: number) => {
    const { queue, queueIndex } = get()
    const newQueue = queue.filter((_: any, i: number) => i !== index)
    const newIndex = index >= newQueue.length ? newQueue.length - 1 : index
    set({
      queue: newQueue,
      queueIndex: newIndex >= 0 ? newIndex : 0,
      currentTrack: newQueue[newIndex >= 0 ? newIndex : 0] || null,
    })
  },
}))
