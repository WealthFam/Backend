import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export const useGoalStore = defineStore('goals', () => {
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    const goals = ref<any[]>([])
    const accounts = ref<any[]>([])
    const portfolio = ref<any[]>([])
    const loading = ref(false)

    useStorePersistence('goals_list', goals, memberId)
    useStorePersistence('goals_accounts', accounts, memberId)
    useStorePersistence('goals_portfolio', portfolio, memberId)

    async function fetchGoals(mId?: string) {
        loading.value = true
        try {
            const res = await financeApi.getInvestmentGoals(mId || auth.selectedMemberId || undefined)
            goals.value = res.data
        } catch (error) {
            console.error('[GoalStore] Failed to fetch goals', error)
        } finally {
            loading.value = false
        }
    }

    async function fetchAccounts(mId?: string) {
        try {
            const res = await financeApi.getAccounts(mId || auth.selectedMemberId || undefined)
            accounts.value = res.data.filter((a: any) => a.type === 'BANK' || a.type === 'INVESTMENT')
        } catch (error) {
            console.error('[GoalStore] Failed to fetch accounts', error)
        }
    }

    async function fetchPortfolio(mId?: string) {
        try {
            const res = await financeApi.getPortfolio(mId || auth.selectedMemberId || undefined)
            portfolio.value = res.data
        } catch (error) {
            console.error('[GoalStore] Failed to fetch portfolio', error)
        }
    }

    return {
        goals,
        accounts,
        portfolio,
        loading,
        fetchGoals,
        fetchAccounts,
        fetchPortfolio
    }
})
