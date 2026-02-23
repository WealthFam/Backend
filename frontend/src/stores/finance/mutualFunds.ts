import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'

export const useMutualFundStore = defineStore('mutualFunds', () => {
    const notification = useNotificationStore()
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    // State
    const isSyncing = ref(false)
    const syncStatus = ref<any>(null)
    const portfolio = ref<any[]>([])
    const analytics = ref<any>(null)
    const aiAnalysis = ref<string>('')

    useStorePersistence('mf_sync_status', syncStatus, memberId)
    useStorePersistence('mf_portfolio', portfolio, memberId)
    useStorePersistence('mf_analytics', analytics, memberId)
    useStorePersistence('mf_ai_analysis', aiAnalysis, memberId)

    const lastFetch = ref<number>(0)

    // Actions
    async function fetchSyncStatus() {
        try {
            const { data } = await financeApi.getMutualFundSyncStatus()
            syncStatus.value = data
            lastFetch.value = Date.now()

            // Handle transition from running to completed/error
            if (isSyncing.value && data.status !== 'running') {
                isSyncing.value = false
                if (data.status === 'completed') {
                    notification.success(`Mutual Fund sync completed: ${data.updated_count} funds updated.`)
                } else if (data.status === 'error') {
                    notification.error(`Mutual Fund sync failed: ${data.error}`)
                }
            } else if (data.status === 'running') {
                isSyncing.value = true
            }
        } catch (error) {
            console.error('[MutualFundStore] Failed to fetch sync status:', error)
        }
    }

    async function triggerSync() {
        if (isSyncing.value) return

        isSyncing.value = true
        try {
            await financeApi.triggerMutualFundSync()
            notification.info('Mutual Fund background sync started...')

            // Poll sooner to catch the "running" state
            setTimeout(fetchSyncStatus, 1000)
        } catch (error) {
            isSyncing.value = false
            console.error('[MutualFundStore] Sync trigger failed:', error)
            // Error notification is handled by axios interceptor but we can add more context if needed
        }
    }

    return {
        isSyncing,
        syncStatus,
        portfolio,
        analytics,
        aiAnalysis,
        lastFetch,
        fetchSyncStatus,
        triggerSync
    }
})
