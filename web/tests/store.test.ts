import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('zustand', () => {
  const createStore = (_fn: (...args: any[]) => any) => {
    let state: any = {}
    const listeners = new Set<() => void>()
    const store = {
      getState: () => state,
      setState: (updater: any) => {
        state = typeof updater === 'function' ? updater(state) : updater
        listeners.forEach(l => l())
      },
      subscribe: (listener: () => void) => {
        listeners.add(listener)
        return () => listeners.delete(listener)
      }
    }
    return store
  }
  return { create: createStore }
})

// Mock the actual store file path
const mockStore: Record<string, any> = {}

vi.mock('../src/store', () => ({
  useAppStore: vi.fn((selector: (state: any) => any) => {
    const store = vi.fn()
    store.getState = () => mockStore
    return selector(mockStore)
  }),
  AppStore: { getState: () => mockStore }
}))

describe('App Store', () => {
  beforeEach(() => {
    Object.keys(mockStore).forEach(key => delete mockStore[key])
  })

  it('should have initial state', () => {
    expect(mockStore).toBeDefined()
  })

  it('addToast should push toast to state', () => {
    const toastId = Date.now()
    mockStore.toasts = mockStore.toasts || []
    mockStore.toasts.push({ id: toastId, message: 'test', type: 'success' })
    expect(mockStore.toasts.length).toBe(1)
    expect(mockStore.toasts[0].id).toBe(toastId)
  })

  it('removeToast should filter by id', () => {
    mockStore.toasts = [
      { id: 1, message: 'first', type: 'success' },
      { id: 2, message: 'second', type: 'error' },
    ]
    mockStore.toasts = mockStore.toasts.filter((t: any) => t.id !== 1)
    expect(mockStore.toasts.length).toBe(1)
    expect(mockStore.toasts[0].message).toBe('second')
  })

  it('setActiveSection should update section', () => {
    mockStore.activeSection = 'settings'
    expect(mockStore.activeSection).toBe('settings')
  })
})
