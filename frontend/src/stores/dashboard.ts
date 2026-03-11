import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export const useDashboardStore = defineStore('dashboard', () => {
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    const metrics = ref<any>(null)
    const mfPortfolio = ref<any>(null)
    const netWorthTrend = ref<number[]>([])
    const spendingTrend = ref<number[]>([])
    const aiInsights = ref<any>(null)
    const loading = ref(false)

    // Apply Persistence
    useStorePersistence('dashboard_metrics', metrics, memberId)
    useStorePersistence('dashboard_portfolio', mfPortfolio, memberId)
    useStorePersistence('dashboard_net_worth_trend', netWorthTrend, memberId)
    useStorePersistence('dashboard_spending_trend', spendingTrend, memberId)
    useStorePersistence('dashboard_ai_insights', aiInsights, memberId)

    async function fetchDashboardData(userId?: string) {
        loading.value = true
        const uId = userId || auth.selectedMemberId || undefined
        try {
            const [m, p, nwt, st] = await Promise.all([
                financeApi.getMetrics(undefined, undefined, undefined, uId),
                financeApi.getPortfolio(uId),
                financeApi.getNetWorthTimeline(30, uId),
                financeApi.getSpendingTrend(uId)
            ])
            metrics.value = m.data

            // Basic portfolio aggregation for summary
            if (p.data && Array.isArray(p.data)) {
                let invested = 0, current = 0
                p.data.forEach((h: any) => {
                    invested += Number(h.invested_value || 0)
                    current += Number(h.current_value || 0)
                })
                mfPortfolio.value = {
                    ...(mfPortfolio.value || {}),
                    invested,
                    current
                }
            }

            netWorthTrend.value = nwt.data.map((p: any) => Number(p.total || 0))
            spendingTrend.value = st.data.map((p: any) => Number(p.amount || 0))

            // Fetch AI Insights if metrics are available
            if (metrics.value) {
                // Background fetch for AI (no force refresh by default)
                fetchAiInsights(false)
            }
        } catch (error) {
            console.error('[DashboardStore] Failed to fetch data', error)
        } finally {
            loading.value = false
        }
    }

    async function fetchAiInsights(forceRefresh: boolean = false) {
        const uId = memberId.value || undefined
        const now = new Date()
        try {
            const res = await financeApi.getBudgetsInsights(now.getFullYear(), now.getMonth() + 1, uId, forceRefresh)
            aiInsights.value = res.data
        } catch (error) {
            console.error('[DashboardStore] Failed to fetch AI Insights', error)
        }
    }

    return {
        metrics,
        mfPortfolio,
        netWorthTrend,
        spendingTrend,
        aiInsights,
        loading,
        fetchDashboardData,
        fetchAiInsights
    }
})
