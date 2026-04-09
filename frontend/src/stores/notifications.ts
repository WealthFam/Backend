import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi, type AlertSchema } from '@/api/notifications'
import { useAuthStore } from '@/stores/auth'

export interface Notification extends AlertSchema {
    payload?: any
}

export const useNotificationStore = defineStore('notifications', () => {
    const auth = useAuthStore()
    const notifications = ref<Notification[]>([])
    const isConnected = ref(false)
    const loading = ref(false)
    const lastEvent = ref<{ type: string, payload: any } | null>(null)

    async function fetchNotifications(limit: number = 20) {
        if (!auth.token) return
        loading.value = true
        try {
            const res = await notificationsApi.getAlerts(limit)
            notifications.value = res.data.data
        } catch (e) {
            console.error('[NotificationStore] Failed to fetch notifications', e)
        } finally {
            loading.value = false
        }
    }

    function addNotification(notification: Notification) {
        // Prevent duplicates and keep limit to 50
        const exists = notifications.value.some(n => n.id === notification.id)
        if (!exists) {
            notifications.value = [notification, ...notifications.value].slice(0, 50)
        }
    }

    function setConnected(status: boolean) {
        isConnected.value = status
    }

    function clearNotifications() {
        notifications.value = []
    }

    function setLastEvent(event: { type: string; payload: any }) {
        lastEvent.value = event
    }

    return {
        notifications,
        isConnected,
        loading,
        lastEvent,
        fetchNotifications,
        addNotification,
        setConnected,
        setLastEvent,
        clearNotifications
    }
})
