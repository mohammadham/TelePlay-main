import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

afterEach(() => {
  cleanup()
})

// Mock tanstack query
vi.mock('@tanstack/react-query', () => ({
  useQuery: vi.fn(),
  useMutation: vi.fn(),
  useQueryClient: vi.fn(),
  QueryClientProvider: ({ children }: { children: React.ReactNode }) => children,
}))

// Mock router
vi.mock('react-router-dom', () => ({
  BrowserRouter: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Routes: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  Route: ({ element }: { element: React.ReactNode }) => element,
  Link: ({ to, children }: { to: string; children: React.ReactNode }) => <a href={to}>{children}</a>,
  useParams: () => ({}),
  useSearchParams: () => [{}, vi.fn()],
  useNavigate: () => vi.fn(),
  Outlet: () => null,
}))

// Mock zustand
vi.mock('zustand', () => ({
  create: (_fn: (...args: any[]) => any) => (_set: any, _get: any) => ({}),
}))

// Mock CSS modules
vi.mock('*.css', () => ({}))
vi.mock('*.module.css', () => ({}))
vi.mock('*.module.scss', () => ({}))

// Mock images
vi.mock('*', () => ({
  default: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PHJlY3Qgd2lkdGg9IjEwIiBoZWlnaHQ9IjEwIiBmaWxsPSIjZmZmIi8+PC9zdmc+',
}))

// Mock video.js
vi.mock('video.js', () => ({
  __esModule: true,
  default: vi.fn(),
}))
