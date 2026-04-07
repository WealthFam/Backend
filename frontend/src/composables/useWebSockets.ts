import { onMounted, watch, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useActivityStore } from '@/stores/activity'

let socket: WebSocket | null = null
let reconnectTimer: any = null

export function useWebSockets() {
    const auth = useAuthStore()
    const activityStore = useActivityStore()

    const connect = () => {
        if (!auth.token || !auth.user?.tenant_id) return
        if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        let host = window.location.host
        
        if (host.includes('localhost') || host.includes('127.0.0.1')) {
            host = 'localhost:8000'
        } else if (window.location.port === '5173' || window.location.port === '3000') {
            host = `${window.location.hostname}:8000`
        }

        const tenantId = auth.user.tenant_id
        const token = auth.token

        const wsUrl = `${protocol}//${host}/ws/${tenantId}?token=${token}`
        socket = new WebSocket(wsUrl)

        socket.onopen = () => {
            activityStore.setConnected(true)
            if (reconnectTimer) {
                clearTimeout(reconnectTimer)
                reconnectTimer = null
            }
        }

        socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                // Always update lastEvent for reactivity across components
                activityStore.setLastEvent(data)

                if (data.type === 'NOTIFICATION') {
                    activityStore.addActivity(data.payload)
                }
            } catch (e) {
                console.error('[WebSockets] Error parsing message:', e)
            }
        }

        socket.onclose = () => {
            activityStore.setConnected(false)
            // Exponential backoff or simple retry
            if (!reconnectTimer) {
                reconnectTimer = setTimeout(() => {
                    reconnectTimer = null
                    connect()
                }, 5000)
            }
        }

        socket.onerror = (error) => {
            console.error('[WebSockets] Error:', error)
            socket?.close()
        }
    }

    const disconnect = () => {
        if (socket) {
            socket.close()
            socket = null
        }
        if (reconnectTimer) {
            clearTimeout(reconnectTimer)
            reconnectTimer = null
        }
    }

    onMounted(() => {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            connect()
            activityStore.fetchActivities()
        }
    })

    // Reconnect on auth change
    watch(() => auth.token, (newToken) => {
        if (newToken) {
            connect()
        } else {
            disconnect()
            activityStore.clearActivities()
        }
    })

    return {
        notifications: computed(() => activityStore.activities),
        isConnected: computed(() => activityStore.isConnected),
        clearNotifications: () => activityStore.clearActivities(),
        fetchNotifications: (limit?: number) => activityStore.fetchActivities(limit)
    }
}
