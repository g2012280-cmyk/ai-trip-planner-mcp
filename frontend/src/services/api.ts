import axios from 'axios'
import type { TripPlan, TripPlanRequest } from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 180000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    console.error('Request failed:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)

export const generateTripPlan = async (request: TripPlanRequest): Promise<TripPlan> => {
  const { data } = await api.post<TripPlan>('/trip/plan', request)
  return data
}

export const healthCheck = async (): Promise<{ status: string }> => {
  const { data } = await api.get('/trip/health')
  return data
}
