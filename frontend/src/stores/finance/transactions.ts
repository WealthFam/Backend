import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export const useTransactionStore = defineStore('transactions', () => {
    const auth = useAuthStore()

    // State
    const transactions = ref<any[]>([])
    const total = ref(0)
    const metrics = ref<any>(null)
    const loading = ref(false)

    // Member-specific persistence
    const memberId = computed(() => auth.selectedMemberId)
    useStorePersistence('txns_list', transactions, memberId)
    useStorePersistence('txns_total', total, memberId)
    useStorePersistence('txns_metrics', metrics, memberId)

    async function fetchTransactions(params: any) {
        loading.value = true
        try {
            const res = await financeApi.getTransactions(
                params.accountId,
                params.page,
                params.pageSize,
                params.startDate,
                params.endDate,
                params.search,
                params.category,
                params.sortKey,
                params.sortOrder,
                auth.selectedMemberId || undefined
            )
            transactions.value = res.data.data
            total.value = res.data.total

            // Fetch metrics if on main list with no search
            if (!params.search && !params.category) {
                const mRes = await financeApi.getMetrics(
                    params.accountId,
                    params.startDate,
                    params.endDate,
                    auth.selectedMemberId || undefined
                )
                metrics.value = mRes.data
            }
        } catch (error) {
            console.error('[TransactionStore] Failed to fetch', error)
        } finally {
            loading.value = false
        }
    }

    return {
        transactions,
        total,
        metrics,
        loading,
        fetchTransactions
    }
})
