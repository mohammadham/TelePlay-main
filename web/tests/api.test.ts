import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

describe('API Client', () => {
  const mockAxios = {
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() }
    },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should have request interceptor', () => {
    const axiosInstance = axios.create()
    axiosInstance.interceptors.request.use(vi.fn())
    expect(axiosInstance.interceptors.request.use).toHaveBeenCalled()
  })

  it('should have response interceptor', () => {
    const axiosInstance = axios.create()
    axiosInstance.interceptors.response.use(vi.fn(), vi.fn())
    expect(axiosInstance.interceptors.response.use).toHaveBeenCalled()
  })

  it('GET should return data property', async () => {
    mockAxios.get.mockResolvedValue({ data: { result: 'ok' } })
    const response = await axios.get('/test')
    expect(response.data).toEqual({ result: 'ok' })
  })

  it('POST should send body', async () => {
    mockAxios.post.mockResolvedValue({ data: { created: true } })
    const response = await axios.post('/test', { key: 'value' })
    expect(mockAxios.post).toHaveBeenCalledWith('/test', { key: 'value' }, expect.any(Object))
    expect(response.data.created).toBe(true)
  })

  it('should handle 401 unauthorized', async () => {
    const axiosInstance = axios.create()
    let refreshPromise: Promise<any> | null = null

    axiosInstance.interceptors.response.use(
      response => response,
      async error => {
        const originalRequest = error.config
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true
          if (!refreshPromise) {
            refreshPromise = Promise.resolve({ data: { access_token: 'new-token' } })
          }
          const { data } = await refreshPromise
          originalRequest.headers['Authorization'] = `Bearer ${data.access_token}`
          return axiosInstance(originalRequest)
        }
        return Promise.reject(error)
      }
    )

    const error = { response: { status: 401 }, config: {} }
    await expect(axiosInstance.interceptors.response.handlers[1].rejected(error)).resolves.toBeDefined()
  })
})
