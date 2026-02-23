import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useAuthStore } from '@/stores/auth'

export interface ExpenseGroup {
    id: string
    name: string
    description: string
    is_active: boolean
    created_at: string
}

export const useExpenseGroupStore = defineStore('expenseGroups', () => {
    const auth = useAuthStore()
    const memberId = computed(() => auth.selectedMemberId)

    const groups = ref<ExpenseGroup[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)

    useStorePersistence('expense_groups_list', groups, memberId)

    async function fetchGroups() {
        loading.value = true
        try {
            const response = await financeApi.getExpenseGroups(auth.selectedMemberId || undefined)
            groups.value = response.data
            error.value = null
        } catch (err: any) {
            error.value = 'Failed to fetch expense groups'
            console.error(err)
        } finally {
            loading.value = false
        }
    }

    async function createGroup(name: string, description: string) {
        try {
            const response = await financeApi.createExpenseGroup({ name, description })
            groups.value.push(response.data)
        } catch (err: any) {
            throw new Error('Failed to create expense group')
        }
    }

    async function updateGroup(id: string, name: string, description: string, is_active: boolean) {
        try {
            const response = await financeApi.updateExpenseGroup(id, { name, description, is_active })
            const index = groups.value.findIndex(g => g.id === id)
            if (index !== -1) {
                groups.value[index] = response.data
            }
        } catch (err: any) {
            throw new Error('Failed to update expense group')
        }
    }

    async function deleteGroup(id: string) {
        try {
            await financeApi.deleteExpenseGroup(id)
            groups.value = groups.value.filter(g => g.id !== id)
        } catch (err: any) {
            throw new Error('Failed to delete expense group')
        }
    }

    return {
        groups,
        loading,
        error,
        fetchGroups,
        createGroup,
        updateGroup,
        deleteGroup
    }
})
