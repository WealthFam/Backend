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
    const netWorthLabels = ref<string[]>([])
    const spendingTrend = ref<number[]>([])
    const spendingLabels = ref<string[]>([])
    const sixMonthSpendingTrend = ref<number[]>([])
    const sixMonthLabels = ref<string[]>([])
    const aiInsights = ref<any>(null)
    const loading = ref(false)

    const projectedBudgetTrend = computed(() => {
        if (!spendingTrend.value || spendingTrend.value.length === 0) return []
        const trend: number[] = []
        let cumulative = 0
        spendingTrend.value.forEach(val => {
            cumulative += val
            trend.push(cumulative)
        })

        // Project/predict the remaining days of the month
        const now = new Date()
        const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
        const currentDay = trend.length // since spendingTrend is exactly MTD

        if (currentDay > 0 && currentDay < daysInMonth) {
            const burnRate = cumulative / currentDay
            for (let i = currentDay + 1; i <= daysInMonth; i++) {
                cumulative += burnRate
                trend.push(cumulative)
            }
        }
        return trend
    })

    const projectedBudgetLabels = computed(() => {
        if (!spendingTrend.value || spendingTrend.value.length === 0) return []
        const labels: string[] = []
        const now = new Date()
        const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate()
        for (let i = 1; i <= daysInMonth; i++) {
            labels.push(new Date(now.getFullYear(), now.getMonth(), i).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }))
        }
        return labels
    })

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
            const [m, pAnalytics, nwt, st, bh] = await Promise.all([
                financeApi.getMetrics(undefined, undefined, undefined, uId),
                financeApi.getAnalytics(uId),
                financeApi.getNetWorthTimeline(30, uId),
                financeApi.getSpendingTrend(uId),
                financeApi.getBudgetHistory(6, uId)
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
            netWorthLabels.value = nwt.data.map((p: any) => p.date ? new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '')

            spendingTrend.value = st.data.map((p: any) => Number(p.amount || 0))
            spendingLabels.value = st.data.map((p: any) => p.date ? new Date(p.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '')

            if (bh.data && Array.isArray(bh.data)) {
                sixMonthSpendingTrend.value = bh.data.map((month: any) => {
                    const overall = month.data?.find((c: any) => c.category === 'OVERALL')
                    if (overall) return Number(overall.spent || 0)
                    return month.data?.reduce((sum: number, c: any) => sum + Number(c.spent || 0), 0) || 0
                })
                sixMonthLabels.value = bh.data.map((month: any) => month.month || '')
            }

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
        netWorthLabels,
        spendingTrend,
        spendingLabels,
        sixMonthSpendingTrend,
        sixMonthLabels,
        projectedBudgetTrend,
        projectedBudgetLabels,
        aiInsights,
        loading,
        fetchDashboardData,
        fetchAiInsights
    }
})
