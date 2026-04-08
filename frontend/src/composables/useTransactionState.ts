import { ref, computed, watch, type Ref, type ComputedRef } from 'vue'
import { financeApi } from '@/api/client'
import { localDateString, todayLocalString } from '@/utils/time'
import { useNotificationStore } from '@/stores/notification'
import { useTransactionStore } from '@/stores/finance/transactions'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import { useExpenseGroupStore } from '@/stores/expenseGroups'
import type { RouteLocationNormalized } from 'vue-router'

/**
 * Transaction State Management Composable
 * Handles transaction list state, filters, pagination, sorting, and selection
 */
export function useTransactionState(
    route: RouteLocationNormalized,
    accounts: Ref<any[]> | ComputedRef<any[]>
) {
    const notify = useNotificationStore()
    const txnStore = useTransactionStore()
    const financeStore = useFinanceStore()
    const auth = useAuthStore()
    const groupStore = useExpenseGroupStore()

    // Core State (MAPPED TO STORE)
    const transactions = computed(() => txnStore.transactions)
    const loading = computed(() => txnStore.loading)
    const forecastData = ref<any>(null)
    const total = computed(() => txnStore.total)
    const metrics = computed(() => txnStore.metrics || {
        monthly_income: 0,
        monthly_spending: 0,
        breakdown: { net_worth: 0 }
    })

    // Filter State
    const selectedAccount = ref<string>('')
    const searchQuery = ref('')
    const categoryFilter = ref('')
    const today = new Date()
    const startDate = ref<string>(localDateString(today.getFullYear(), today.getMonth(), 1))
    const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0)
    const endDate = ref<string>(localDateString(lastDayOfMonth.getFullYear(), lastDayOfMonth.getMonth(), lastDayOfMonth.getDate()))
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
        await financeStore.fetchAccounts()
    }

    /**
     * Fetch transactions with current filters
     */
    /**
     * Fetch transactions with current filters
     */
    async function fetchData() {
        try {
            // Load master data via stores
            await Promise.all([
                financeStore.fetchAccounts(),
                financeStore.fetchCategories(),
                groupStore.fetchGroups(),
                financeApi.getSpendingForecast(startDate.value, endDate.value, auth.selectedMemberId || undefined).then(res => {
                    forecastData.value = res.data
                })
            ])

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

            // Delegated to Store
            await txnStore.fetchTransactions({
                accountId: selectedAccount.value || undefined,
                page: page.value,
                pageSize: pageSize.value,
                startDate: startDate.value || undefined,
                endDate: endDate.value || undefined,
                search: searchQuery.value || undefined,
                category: categoryFilter.value || undefined,
                sortKey: txnSortKey.value,
                sortOrder: txnSortOrder.value
            })

            // If current page exceeds total pages, reset to page 1
            if (page.value > Math.ceil(total.value / pageSize.value) && page.value > 1) {
                page.value = 1
                fetchData()
            }
        } catch (e) {
            console.error('[Transactions] Failed to fetch data', e)
            notify.error('Failed to load data')
        } finally {
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
                start = todayLocalString()
                end = localDateString(today.getFullYear(), today.getMonth(), today.getDate() + 1)
                break
            case 'this-week': {
                const weekStart = new Date(today)
                weekStart.setDate(today.getDate() - today.getDay())
                const weekEnd = new Date(weekStart)
                weekEnd.setDate(weekStart.getDate() + 6)
                start = localDateString(weekStart.getFullYear(), weekStart.getMonth(), weekStart.getDate())
                end = localDateString(weekEnd.getFullYear(), weekEnd.getMonth(), weekEnd.getDate())
                break
            }
            case 'this-month': {
                start = localDateString(today.getFullYear(), today.getMonth(), 1)
                const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0)
                end = localDateString(lastDay.getFullYear(), lastDay.getMonth(), lastDay.getDate())
                break
            }
            case 'last-month': {
                const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1)
                const lastMonthEnd = new Date(today.getFullYear(), today.getMonth(), 0)
                start = localDateString(lastMonthStart.getFullYear(), lastMonthStart.getMonth(), lastMonthStart.getDate())
                end = localDateString(lastMonthEnd.getFullYear(), lastMonthEnd.getMonth(), lastMonthEnd.getDate())
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
        txnStore.loading = true
        try {
            await financeApi.bulkDeleteTransactions(Array.from(selectedIds.value))
            notify.success(`Deleted ${selectedIds.value.size} transactions`)
            fetchData()
            showDeleteConfirm.value = false
            selectedIds.value.clear()
        } catch (e) {
            notify.error('Failed to delete transactions')
            txnStore.loading = false
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
        forecastData,
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
        fetchModalData: async () => {
            // Lazy load heavy data for modals via stores
            const budgetStore = (await import('@/stores/finance/budgets')).useBudgetStore()
            const loanStore = (await import('@/stores/finance/loans')).useLoanStore()

            if (budgetStore.budgets.length === 0 || loanStore.loans.length === 0) {
                try {
                    await Promise.all([
                        budgetStore.fetchBudgets(new Date().getFullYear(), new Date().getMonth() + 1),
                        loanStore.fetchLoans()
                    ])
                } catch (e) {
                    console.error('Failed to load modal data', e)
                }
            }
        },
        handleTimeRangeChange,
        toggleTxnSort,
        changePage,
        toggleSelectAll,
        toggleSelection,
        confirmDelete,
        refreshAccounts
    }
}
