import apiClient from './client'

export interface AlertSchema {
  id: string
  title: string
  body: string
  category: string
  icon?: string
  created_at: string
  is_read: boolean
}

export interface AlertList {
  data: AlertSchema[]
  total: number
}

export const notificationsApi = {
  getAlerts: (limit: number = 20, skip: number = 0) =>
    apiClient.get<AlertList>('/notifications/', { params: { limit, skip } }),
  markAsRead: (id: string) =>
    apiClient.post(`/notifications/${id}/read`)
}
