import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export const useLoanStore = defineStore('loans', () => {
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    const loans = ref<any[]>([])
    const loading = ref(false)

    useStorePersistence('loans_list', loans, memberId)

    async function fetchLoans() {
        loading.value = true
        try {
            const response = await financeApi.getLoans(auth.selectedMemberId || undefined)
            loans.value = response.data
        } catch (error) {
            console.error('[LoanStore] Failed to fetch loans', error)
        } finally {
            loading.value = false
        }
    }

    return {
        loans,
        loading,
        fetchLoans
    }
})
