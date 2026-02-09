import { defineStore } from 'pinia'
import { ref } from 'vue'
import { financeApi } from '@/api/client'

export const useFinanceStore = defineStore('finance', () => {
    // State
    const categories = ref<any[]>([])
    const accounts = ref<any[]>([])


    const recurringTransactions = ref<any[]>([])
    // const metrics = ref<any>(null)

    const loading = ref(false)
    const error = ref<string | null>(null)

    // Actions
    async function fetchAll(userId?: string) {
        loading.value = true
        error.value = null
        try {
            const [cats, accs, recs] = await Promise.all([
                financeApi.getCategories(),
                financeApi.getAccounts(),
                financeApi.getRecurringTransactions(userId)
            ])
            categories.value = cats.data
            accounts.value = accs.data
            recurringTransactions.value = recs.data

            // Should we fetch metrics here too?
            // metrics is dashboard specific usually.
        } catch (e: any) {
            console.error("Failed to fetch finance data", e)
            error.value = e.message || "Failed to load data"
        } finally {
            loading.value = false
        }
    }

    async function fetchCategories() {
        if (categories.value.length > 0) return // Cache hit?
        try {
            const res = await financeApi.getCategories()
            categories.value = res.data
        } catch (e) {
            console.error("Failed to fetch categories", e)
        }
    }

    async function fetchAccounts() {
        try {
            const res = await financeApi.getAccounts()
            accounts.value = res.data
        } catch (e) {
            console.error("Failed to fetch accounts", e)
        }
    }

    async function fetchRecurring(userId?: string) {
        try {
            const res = await financeApi.getRecurringTransactions(userId)
            recurringTransactions.value = res.data
        } catch (e) {
            console.error("Failed to fetch recurring", e)
        }
    }

    // Getters / Helpers
    function getCategoryColor(name: string): string {
        const cat = categories.value.find(c => c.name === name)
        return cat?.color || '#3B82F6' // Default Blue
    }

    function getCategoryIcon(name: string): string {
        const cat = categories.value.find(c => c.name === name)
        return cat?.icon || '🏷️'
    }

    function getAccountName(id: string): string {
        const acc = accounts.value.find(a => a.id === id)
        return acc ? acc.name : 'Unknown Account'
    }

    return {
        categories,
        accounts,
        recurringTransactions,
        loading,
        error,
        fetchAll,
        fetchCategories,
        fetchAccounts,
        fetchRecurring,
        getCategoryColor,
        getCategoryIcon,
        getAccountName
    }
})
