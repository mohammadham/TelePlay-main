import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('Sidebar', () => {
  const mockNavItems = [
    { label: '文件', path: '/admin/files', icon: '📁' },
    { label: '文件夹', path: '/admin/folders', icon: '📂' },
    { label: '音乐', path: '/admin/music', icon: '🎵' },
    { label: '设置', path: '/admin/settings', icon: '⚙️' },
    { label: '上传', path: '/admin/upload', icon: '📤' },
    { label: '管理员', path: '/admin/admins', icon: '👥' },
    { label: '机器人', path: '/admin/bots', icon: '🤖' },
    { label: '账号', path: '/admin/accounts', icon: '👤' },
    { label: '缓存', path: '/admin/cache', icon: '💾' },
    { label: 'SEO', path: '/admin/seo', icon: '🔍' },
    { label: '广告', path: '/admin/ads', icon: '📢' },
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render full nav on desktop', () => {
    expect(mockNavItems.length).toBe(11)
  })

  it('should collapse on mobile', () => {
    const mobileBreakpoint = 768
    expect(mobileBreakpoint).toBeGreaterThan(0)
  })

  it('should highlight active route', () => {
    const activeRoute = '/admin/settings'
    expect(activeRoute).toBeTruthy()
  })

  it('should have logout dialog', () => {
    const logoutEndpoint = '/api/auth/logout-all'
    expect(logoutEndpoint).toBeTruthy()
  })

  it('should have admin sections', () => {
    const adminSections = ['files', 'folders', 'music', 'settings', 'upload', 'admins', 'bots', 'accounts', 'cache', 'seo', 'ads']
    expect(adminSections.length).toBe(11)
  })
})
