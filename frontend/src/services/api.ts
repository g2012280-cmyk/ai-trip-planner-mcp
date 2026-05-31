import axios from 'axios'
import type { TripPlan, TripPlanRequest } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000, // 3 分钟，LLM 生成可能较慢
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(
  config => config,
  error => Promise.reject(error)
)

api.interceptors.response.use(
  response => response,
  error => {
    console.error('请求失败:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export const generateTripPlan = async (request: TripPlanRequest): Promise<TripPlan> => {
  const response = await api.post<TripPlan>('/trip/plan', request)
  return response.data
}

export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get('/trip/health')
  return response.data
}
