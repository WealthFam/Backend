import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { mobileApi } from '@/api/client'

export interface Notification {
    id: string
    title: string
    body: string
    category: 'EXPENSE' | 'MILESTONE' | 'BUDGET_ALERT' | 'ACCOUNT' | 'INFO'
    created_at: string
    payload?: any
}

const notifications = ref<Notification[]>([])
const isConnected = ref(false)
const socket = ref<WebSocket | null>(null)

export function useWebSockets() {
    const auth = useAuthStore()

    const connect = () => {
        if (!auth.user || !auth.user.tenant_id) return

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
        socket.value = new WebSocket(wsUrl)

        socket.value.onopen = () => {
            isConnected.value = true
        }

        socket.value.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'NOTIFICATION') {
                    notifications.value = [data.payload, ...notifications.value].slice(0, 50)
                }
            } catch (e) {
                console.error('Error parsing WebSocket message:', e)
            }
        }

        socket.value.onclose = () => {
            isConnected.value = false
            setTimeout(connect, 5000)
        }

        socket.value.onerror = (error) => {
            console.error('WebSocket Error:', error)
            socket.value?.close()
        }
    }

    const fetchNotifications = async () => {
        if (!auth.token) return
        try {
            const res = await mobileApi.getAlerts()
            notifications.value = res.data
        } catch (e) {
            console.error('Error fetching initial notifications:', e)
        }
    }

    onMounted(() => {
        if (!socket.value || socket.value.readyState !== WebSocket.OPEN) {
            connect()
            fetchNotifications()
        }
    })

    const clearNotifications = () => {
        notifications.value = []
    }

    return {
        notifications,
        isConnected,
        clearNotifications,
        fetchNotifications
    }
}
