import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export const useBudgetStore = defineStore('budgets', () => {
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    const budgets = ref<any[]>([])
    const overallBudget = ref<any>(null)
    const insights = ref<any[]>([])
    const loading = ref(false)

    // Persist last viewed month's data for instant load
    useStorePersistence('last_budgets', budgets, memberId)
    useStorePersistence('last_overall_budget', overallBudget, memberId)
    useStorePersistence('last_budget_insights', insights, memberId)

    async function fetchBudgets(year: number, month: number, userId?: string) {
        loading.value = true
        const uId = userId || auth.selectedMemberId || undefined
        try {
            const [budgetRes, overviewRes] = await Promise.all([
                financeApi.getBudgets(year, month, uId),
                financeApi.getBudgetOverview(year, month, uId)
            ])
            budgets.value = budgetRes.data
            overallBudget.value = overviewRes.data
        } catch (error) {
            console.error('[BudgetStore] Failed to fetch budgets', error)
        } finally {
            loading.value = false
        }
    }

    async function fetchInsights(year: number, month: number, userId?: string) {
        const uId = userId || auth.selectedMemberId || undefined
        try {
            const res = await financeApi.getBudgetsInsights(year, month, uId)
            insights.value = res.data
        } catch (error) {
            console.error('[BudgetStore] Failed to fetch insights', error)
        }
    }

    return {
        budgets,
        overallBudget,
        insights,
        loading,
        fetchBudgets,
        fetchInsights
    }
})
