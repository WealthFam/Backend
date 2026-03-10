import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'

const notifications = ref<any[]>([])
const isConnected = ref(false)
const socket = ref<WebSocket | null>(null)

export function useWebSockets() {
    const auth = useAuthStore()

    const connect = () => {
        if (!auth.user || !auth.user.tenant_id) return

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
        let host = window.location.host
        
        // If we're hitting the frontend (usually port 5173 or 80), 
        // and we're on localhost or an IP, we might need to point to the backend (8000)
        if (host.includes('localhost') || host.includes('127.0.0.1')) {
            host = 'localhost:8000'
        } else if (window.location.port === '5173' || window.location.port === '3000') {
            // Development mode usually runs on 5173, backend on 8000
            host = `${window.location.hostname}:8000`
        }

        const tenantId = auth.user.tenant_id
        const token = auth.token

        const wsUrl = `${protocol}//${host}/ws/${tenantId}?token=${token}`

        // console.log('Connecting to WebSocket:', wsUrl)
        socket.value = new WebSocket(wsUrl)

        socket.value.onopen = () => {
            // console.log('WebSocket Connected')
            isConnected.value = true
        }

        socket.value.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (data.type === 'NOTIFICATION') {
                    // Prepend new notification
                    notifications.value = [data.payload, ...notifications.value].slice(0, 50)
                }
            } catch (e) {
                console.error('Error parsing WebSocket message:', e)
            }
        }

        socket.value.onclose = () => {
            // console.log('WebSocket Disconnected. Retrying in 5s...')
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
            const response = await fetch(`${window.location.protocol}//${window.location.host.includes('localhost') ? 'localhost:8000' : window.location.host}/api/v1/mobile/alerts`, {
                headers: {
                    'Authorization': `Bearer ${auth.token}`
                }
            })
            if (response.ok) {
                const data = await response.json()
                notifications.value = data
            }
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
