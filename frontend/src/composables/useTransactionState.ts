import { ref, computed, watch, type Ref } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'
import type { RouteLocationNormalized } from 'vue-router'

/**
 * Transaction State Management Composable
 * Handles transaction list state, filters, pagination, sorting, and selection
 */
export function useTransactionState(
    route: RouteLocationNormalized,
    accounts: Ref<any[]>,
    categories: Ref<any[]>,
    budgets: Ref<any[]>,
    loans: Ref<any[]>,
    expenseGroups: Ref<any[]>
) {
    const notify = useNotificationStore()
    const auth = useAuthStore()

    // Core State
    const transactions = ref<any[]>([])
    const loading = ref(true)
    const total = ref(0)
    const metrics = ref({
        monthly_income: 0,
        monthly_spending: 0,
        breakdown: {
            net_worth: 0
        }
    })

    // Filter State
    const selectedAccount = ref<string>('')
    const searchQuery = ref('')
    const categoryFilter = ref('')
    const today = new Date()
    const startDate = ref<string>(new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0])
    const endDate = ref<string>(today.toISOString().split('T')[0])
    const selectedTimeRange = ref<string>('this-month')

    const timeRangeOptions = [
        { title: 'All Time', value: 'all' },
        { title: 'Today', value: 'today' },
        { title: 'This Week', value: 'this-week' },
        { title: 'This Month', value: 'this-month' },
        { title: 'Last Month', value: 'last-month' },
        { title: 'Custom Range', value: 'custom' }
    ]

    // Pagination State
    const page = ref(1)
    const pageSize = ref(50)
    const totalPages = computed(() => Math.ceil(total.value / pageSize.value))

    // Sorting State
    const txnSortKey = ref('date')
    const txnSortOrder = ref<'asc' | 'desc'>('desc')

    // Selection State
    const selectedIds = ref<Set<string>>(new Set())
    const allSelected = computed(() => {
        return transactions.value.length > 0 && transactions.value.every(t => selectedIds.value.has(t.id))
    })

    /**
     * Fetch transactions with current filters
     */
    async function refreshAccounts() {
        try {
            const res = await financeApi.getAccounts(auth.selectedMemberId || undefined)
            accounts.value = res.data
        } catch (e) {
            console.error('Failed to refresh accounts', e)
        }
    }

    /**
     * Fetch transactions with current filters
     */
    async function fetchData() {
        loading.value = true
        try {
            // Load master data if not already loaded OR if we need to refresh based on member
            if (accounts.value.length === 0) {
                const [accRes, catRes, budgetRes, loanRes, groupRes] = await Promise.all([
                    financeApi.getAccounts(auth.selectedMemberId || undefined),
                    financeApi.getCategories(true),
                    financeApi.getBudgets(undefined, undefined, auth.selectedMemberId || undefined),
                    financeApi.getLoans(auth.selectedMemberId || undefined),
                    financeApi.getExpenseGroups(auth.selectedMemberId || undefined)
                ])
                accounts.value = accRes.data
                categories.value = catRes.data
                budgets.value = budgetRes.data
                loans.value = loanRes.data
                expenseGroups.value = groupRes.data
            }

            // Set account from route query if available
            if (!selectedAccount.value && route.query.account_id) {
                selectedAccount.value = route.query.account_id as string
            }

            // If selectedAccount is NOT in the current accounts list (due to filter), reset it
            if (selectedAccount.value && accounts.value.length > 0) {
                const exists = accounts.value.some(a => a.id === selectedAccount.value)
                if (!exists) {
                    selectedAccount.value = ''
                }
            }

            const res = await financeApi.getTransactions(
                selectedAccount.value || undefined,
                page.value,
                pageSize.value,
                startDate.value || undefined,
                endDate.value || undefined,
                searchQuery.value || undefined,
                categoryFilter.value || undefined,
                txnSortKey.value,
                txnSortOrder.value,
                auth.selectedMemberId || undefined
            )

            transactions.value = res.data.items
            total.value = res.data.total

            // Fetch metrics for the same filters
            try {
                const metricsRes = await financeApi.getMetrics(
                    selectedAccount.value || undefined,
                    startDate.value || undefined,
                    endDate.value || undefined,
                    auth.selectedMemberId || undefined
                )
                metrics.value = metricsRes.data
            } catch (e) {
                console.error('[Transactions] Failed to fetch metrics', e)
            }

            // If current page exceeds total pages, reset to page 1
            if (page.value > Math.ceil(total.value / pageSize.value) && page.value > 1) {
                page.value = 1
                fetchData()
            }
        } catch (e) {
            console.error('[Transactions] Failed to fetch data', e)
            notify.error('Failed to load data')
        } finally {
            loading.value = false
            selectedIds.value.clear()
        }
    }

    /**
     * Handle time range selection
     */
    function handleTimeRangeChange(value: string) {
        selectedTimeRange.value = value
        const today = new Date()
        let start = ''
        let end = ''

        switch (value) {
            case 'today':
                start = today.toISOString().split('T')[0]
                end = start
                break
            case 'this-week': {
                const weekStart = new Date(today)
                weekStart.setDate(today.getDate() - today.getDay())
                start = weekStart.toISOString().split('T')[0]
                end = today.toISOString().split('T')[0]
                break
            }
            case 'this-month':
                start = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0]
                end = today.toISOString().split('T')[0]
                break
            case 'last-month': {
                const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
                const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
                start = lastMonthStart.toISOString().split('T')[0]
                end = lastMonthEnd.toISOString().split('T')[0]
                break
            }
            case 'all':
                start = ''
                end = ''
                break
            case 'custom':
                // Don't auto-set dates for custom
                return
        }

        startDate.value = start
        endDate.value = end
        page.value = 1
        fetchData()
    }

    /**
     * Toggle transaction sort
     */
    function toggleTxnSort(key: string) {
        if (txnSortKey.value === key) {
            txnSortOrder.value = txnSortOrder.value === 'asc' ? 'desc' : 'asc'
        } else {
            txnSortKey.value = key
            txnSortOrder.value = 'desc'
        }
        // Watcher will trigger fetchData
    }

    /**
     * Change page
     */
    function changePage(newPage: number) {
        if (newPage < 1 || newPage > totalPages.value) return
        page.value = newPage
        fetchData()
    }

    /**
     * Toggle select all
     */
    function toggleSelectAll() {
        if (allSelected.value) {
            selectedIds.value.clear()
        } else {
            transactions.value.forEach(t => selectedIds.value.add(t.id))
        }
    }

    /**
     * Toggle individual selection
     */
    function toggleSelection(id: string) {
        if (selectedIds.value.has(id)) {
            selectedIds.value.delete(id)
        } else {
            selectedIds.value.add(id)
        }
    }

    /**
     * Delete selected transactions
     */
    const showDeleteConfirm = ref(false)

    async function confirmDelete() {
        loading.value = true
        try {
            await financeApi.bulkDeleteTransactions(Array.from(selectedIds.value))
            notify.success(`Deleted ${selectedIds.value.size} transactions`)
            fetchData()
            showDeleteConfirm.value = false
            selectedIds.value.clear()
        } catch (e) {
            notify.error('Failed to delete transactions')
            loading.value = false
        }
    }

    // Watchers for automatic refresh on sort changes
    watch([txnSortKey, txnSortOrder], () => {
        page.value = 1
        fetchData()
    })

    return {
        // State
        transactions,
        loading,
        total,
        metrics,
        selectedAccount,
        searchQuery,
        categoryFilter,
        startDate,
        endDate,
        selectedTimeRange,
        timeRangeOptions,
        page,
        pageSize,
        totalPages,
        txnSortKey,
        txnSortOrder,
        selectedIds,
        allSelected,
        showDeleteConfirm,

        // Methods
        fetchData,
        handleTimeRangeChange,
        toggleTxnSort,
        changePage,
        toggleSelectAll,
        toggleSelection,
        confirmDelete,
        refreshAccounts
    }
}
