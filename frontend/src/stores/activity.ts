import { defineStore } from 'pinia'
import { ref } from 'vue'
import { notificationsApi, type AlertSchema } from '@/api/notifications'
import { useAuthStore } from '@/stores/auth'

export interface ActivityItem extends AlertSchema {
    payload?: any
}

export const useActivityStore = defineStore('activity', () => {
    const auth = useAuthStore()
    const activities = ref<ActivityItem[]>([])
    const isConnected = ref(false)
    const loading = ref(false)
    const lastEvent = ref<{ type: string, payload: any } | null>(null)

    async function fetchActivities(limit: number = 20) {
        if (!auth.token) return
        loading.value = true
        try {
            const res = await notificationsApi.getAlerts(limit)
            // Ensure we don't have duplicates even from the fetch
            const newActivities = res.data.data
            const uniqueActivities = [...newActivities].filter((v, i, a) => a.findIndex(t => t.id === v.id) === i)
            activities.value = uniqueActivities
        } catch (e) {
            console.error('[ActivityStore] Failed to fetch activities', e)
        } finally {
            loading.value = false
        }
    }

    function addActivity(item: ActivityItem) {
        if (!item || !item.id) return
        // Prevent duplicates and keep limit to 50
        const exists = activities.value.some(a => a.id === item.id)
        if (!exists) {
            activities.value = [item, ...activities.value].slice(0, 50)
        }
    }

    function setConnected(status: boolean) {
        isConnected.value = status
    }

    function setLastEvent(event: { type: string; payload: any }) {
        lastEvent.value = event
    }

    function clearActivities() {
        activities.value = []
    }

    return {
        activities,
        isConnected,
        loading,
        lastEvent,
        fetchActivities,
        addActivity,
        setConnected,
        setLastEvent,
        clearActivities
    }
})
