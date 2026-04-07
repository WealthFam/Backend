import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useActivityStore } from '@/stores/activity'
import { useStorePersistence } from '@/utils/persistence'

export const useDashboardStore = defineStore('dashboard', () => {
    const auth = useAuthStore()
    const activityStore = useActivityStore()
    const memberId = computed(() => auth.selectedMemberId)

    const metrics = ref<any>(null)
    const mfPortfolio = ref<{
        invested: number
        current: number
        pl: number
        plPercent: number
        xirr: number
        loading: boolean
    }>({
        invested: 0,
        current: 0,
        pl: 0,
        plPercent: 0,
        xirr: 0,
        loading: true
    })
    const netWorthTrend = ref<number[]>([])
    const spendingTrend = ref<number[]>([])
    const aiInsights = ref<any>(null)
    const loading = ref(false)

    const recentNotifications = computed(() => activityStore.activities)

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
            const [m, pAnalytics, nwt, st] = await Promise.all([
                financeApi.getMetrics(undefined, undefined, undefined, uId),
                financeApi.getAnalytics(uId),
                financeApi.getNetWorthTimeline(30, uId),
                financeApi.getSpendingTrend(uId)
            ])
            
            // Activity fetch is now managed by activityStore or handled elsewhere
            // but we can trigger it here if needed for initial load consistency
            activityStore.fetchActivities(10)

            metrics.value = m.data

            // Portfolio Analytics from dedicated endpoint
            if (pAnalytics.data) {
                const p = pAnalytics.data
                mfPortfolio.value = {
                    invested: Number(p.total_invested || 0),
                    current: Number(p.current_value || 0),
                    pl: Number(p.profit_loss || 0),
                    plPercent: Number(p.profit_loss_percent || 0),
                    xirr: Number(p.xirr || 0),
                    loading: false
                }
            }

            netWorthTrend.value = nwt.data.map((p: any) => Number(p.total || 0))
            spendingTrend.value = st.data.map((p: any) => Number(p.amount || 0))

            // Fetch AI Insights if metrics are available
            if (metrics.value) {
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
        recentNotifications,
        netWorthTrend,
        spendingTrend,
        aiInsights,
        loading,
        fetchDashboardData,
        fetchAiInsights
    }
})
