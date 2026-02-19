import { ref, watch, computed, type Ref } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

/**
 * Transaction Modals Composable
 * Handle all modal-related state and logic (Edit, Smart Categorization, Bulk Rename)
 */
export function useTransactionModals(
    selectedAccount: Ref<string>,
    accounts: Ref<any[]>,
    budgets: Ref<any[]>,
    transactions: Ref<any[]>,
    fetchData: Function,
    showSmartPrompt: Ref<boolean>,
    smartPromptData: Ref<any>,
    refreshAccounts: Function
) {
    const notify = useNotificationStore()

    // Modal State
    const showModal = ref(false)
    const isEditing = ref(false)
    const editingTxnId = ref<string | null>(null)
    const originalCategory = ref<string | null>(null)
    const originalExclude = ref(false)
    const originalDescription = ref('')

    // Match Finding
    const potentialMatches = ref<any[]>([])
    const isSearchingMatches = ref(false)
    const matchesSearched = ref(false)

    // Rename Modal
    const showRenamePrompt = ref(false)
    const renamePromptData = ref({
        oldName: '',
        newName: '',
        count: 0,
        syncToParser: true
    })

    // Form State
    const defaultForm = {
        description: '',
        category: '',
        amount: null,
        date: new Date().toISOString().slice(0, 16),
        account_id: '',
        is_transfer: false,
        to_account_id: '',
        linked_transaction_id: '',
        exclude_from_reports: false,
        is_emi: false,
        loan_id: '',
        expense_group_id: ''
    }
    const form = ref({ ...defaultForm })

    // Budget display
    const currentCategoryBudget = computed(() => {
        if (!form.value.category || form.value.is_transfer) return null
        return budgets.value.find(b => b.category === form.value.category) || null
    })

    // Watch for transfer toggle to auto-set category
    watch(() => form.value.is_transfer, (isTransfer) => {
        if (isTransfer) {
            form.value.category = 'Transfer'
            form.value.exclude_from_reports = true
        } else if (form.value.category === 'Transfer') {
            form.value.category = ''
            form.value.exclude_from_reports = false
        }
    })

    /**
     * Open add transaction modal
     */
    function openAddModal() {
        isEditing.value = false
        editingTxnId.value = null
        form.value = {
            ...defaultForm,
            account_id: selectedAccount.value || (accounts.value[0]?.id || ''),
            date: new Date().toISOString().slice(0, 16),
            is_transfer: false,
            to_account_id: '',
            linked_transaction_id: '',
            is_emi: false,
            loan_id: '',
            expense_group_id: ''
        }
        potentialMatches.value = []
        matchesSearched.value = false
        showModal.value = true
    }

    /**
     * Open edit transaction modal
     */
    function openEditModal(txn: any) {
        if (!txn) {
            openAddModal()
            return
        }
        isEditing.value = true
        editingTxnId.value = txn.id
        originalCategory.value = txn.category
        originalDescription.value = txn.description || ''
        originalExclude.value = txn.exclude_from_reports || false
        form.value = {
            description: txn.description,
            category: txn.category,
            amount: txn.amount,
            date: txn.date ? txn.date.slice(0, 16) : new Date().toISOString().slice(0, 16),
            account_id: txn.account_id,
            is_transfer: txn.is_transfer || false,
            to_account_id: txn.transfer_account_id || '',
            linked_transaction_id: txn.linked_transaction_id || '',
            exclude_from_reports: txn.exclude_from_reports || false,
            is_emi: txn.is_emi || false,
            loan_id: txn.loan_id || '',
            expense_group_id: txn.expense_group_id || ''
        }
        potentialMatches.value = []
        matchesSearched.value = false
        showModal.value = true
    }

    /**
     * Handle form submission (create or update)
     */
    async function handleSubmit() {
        try {
            // Validation
            if (!form.value.account_id) {
                notify.error('Please select an account')
                return
            }
            if (!form.value.amount || Number(form.value.amount) === 0) {
                notify.error('Please enter a valid amount')
                return
            }
            if (!form.value.date) {
                notify.error('Please select a date')
                return
            }

            const payload = {
                description: form.value.description,
                category: form.value.category,
                amount: Number(form.value.amount),
                date: new Date(form.value.date).toISOString(),
                account_id: form.value.account_id,
                is_transfer: form.value.is_transfer,
                to_account_id: form.value.to_account_id,
                linked_transaction_id: form.value.linked_transaction_id,
                exclude_from_reports: form.value.exclude_from_reports,
                is_emi: form.value.is_emi,
                loan_id: form.value.loan_id,
                expense_group_id: form.value.expense_group_id
            }

            if (isEditing.value && editingTxnId.value) {
                await financeApi.updateTransaction(editingTxnId.value, payload)
                notify.success('Transaction updated')

                // Smart Categorization Detection
                if (form.value.category !== originalCategory.value && form.value.category) {
                    const txn = transactions.value.find(t => t.id === editingTxnId.value)
                    if (txn) {
                        const pattern = txn.recipient || txn.description
                        try {
                            const res = await financeApi.getMatchCount([pattern])
                            const totalSimilar = res.data.count

                            if (totalSimilar > 0 || txn.recipient) {
                                smartPromptData.value = {
                                    txnId: editingTxnId.value,
                                    category: form.value.category,
                                    pattern: pattern,
                                    count: totalSimilar,
                                    createRule: true,
                                    applyToSimilar: totalSimilar > 0,
                                    excludeFromReports: false
                                }
                                showSmartPrompt.value = true
                            }
                        } catch (e) {
                            console.error('Match count failed', e)
                        }
                    }
                }

                // Exclude from reports detection
                if (form.value.exclude_from_reports && !originalExclude.value) {
                    const txn = transactions.value.find(t => t.id === editingTxnId.value)
                    if (txn) {
                        const pattern = txn.recipient || txn.description
                        try {
                            const res = await financeApi.getMatchCount([pattern])
                            smartPromptData.value = {
                                txnId: editingTxnId.value,
                                category: form.value.category || 'Uncategorized',
                                pattern: pattern,
                                count: res.data.count,
                                createRule: true,
                                applyToSimilar: res.data.count > 0,
                                excludeFromReports: true
                            }
                            showSmartPrompt.value = true
                        } catch (e) {
                            console.error('Match count failed', e)
                        }
                    }
                }

                // Rename Detection
                if (form.value.description !== originalDescription.value) {
                    try {
                        const res = await financeApi.getMatchCount([originalDescription.value], false)
                        if (res.data.count > 0) {
                            renamePromptData.value = {
                                oldName: originalDescription.value,
                                newName: form.value.description,
                                count: res.data.count,
                                syncToParser: true
                            }
                            showRenamePrompt.value = true
                        }
                    } catch (e) {
                        console.error('Rename check failed', e)
                    }
                }
            } else {
                await financeApi.createTransaction(payload)
                notify.success('Transaction added')
            }
            showModal.value = false
            fetchData()
            refreshAccounts()
        } catch (e: any) {
            console.error(e)
            const msg = e.response?.data?.detail || 'Failed to save transaction'
            notify.error(msg)
        }
    }

    /**
     * Handle bulk rename
     */
    async function handleBulkRename() {
        try {
            await financeApi.bulkRename(
                renamePromptData.value.oldName,
                renamePromptData.value.newName,
                renamePromptData.value.syncToParser
            )
            notify.success(`Renamed ${renamePromptData.value.count} transactions`)
            showRenamePrompt.value = false
            fetchData()
        } catch (e) {
            console.error(e)
            notify.error('Bulk rename failed')
        }
    }

    /**
     * Handle smart categorization
     */
    async function handleSmartCategorize() {
        try {
            const res = await financeApi.smartCategorize({
                transaction_id: smartPromptData.value.txnId,
                category: smartPromptData.value.category,
                create_rule: smartPromptData.value.createRule,
                apply_to_similar: smartPromptData.value.applyToSimilar,
                exclude_from_reports: smartPromptData.value.excludeFromReports
            })

            if (res.data.success) {
                notify.success(`Success! Updated ${res.data.affected} transactions.`)
                if (res.data.rule_created) {
                    notify.success(`Rule saved for "${res.data.pattern}"`)
                }
            }
            showSmartPrompt.value = false
            fetchData()
        } catch (e) {
            notify.error('Smart categorization failed')
        }
    }

    /**
     * Find potential matches for transfer linking
     */
    async function findMatches() {
        if (!form.value.to_account_id || !form.value.amount || !form.value.date) return

        isSearchingMatches.value = true
        matchesSearched.value = false
        try {
            const txnDate = new Date(form.value.date)
            const startDate = new Date(txnDate)
            startDate.setDate(startDate.getDate() - 3)
            const endDate = new Date(txnDate)
            endDate.setDate(endDate.getDate() + 3)

            const res = await financeApi.getTransactions(
                form.value.to_account_id,
                1,
                50,
                startDate.toISOString().slice(0, 10),
                endDate.toISOString().slice(0, 10)
            )

            const targetAmount = -Number(form.value.amount)

            potentialMatches.value = res.data.items.filter((t: any) => {
                return Math.abs(t.amount - targetAmount) < 1.0 &&
                    t.id !== editingTxnId.value &&
                    (!t.linked_transaction_id || t.linked_transaction_id === editingTxnId.value)
            })

            matchesSearched.value = true
        } catch (e) {
            console.error('Match search failed', e)
        } finally {
            isSearchingMatches.value = false
        }
    }

    /**
     * Select/deselect a match
     */
    function selectMatch(match: any) {
        if (form.value.linked_transaction_id === match.id) {
            form.value.linked_transaction_id = ''
        } else {
            form.value.linked_transaction_id = match.id
        }
    }

    return {
        // State
        showModal,
        isEditing,
        editingTxnId,
        originalCategory,
        originalExclude,
        originalDescription,
        potentialMatches,
        isSearchingMatches,
        matchesSearched,
        showRenamePrompt,
        renamePromptData,
        form,
        defaultForm,
        currentCategoryBudget,

        // Methods
        openAddModal,
        openEditModal,
        handleSubmit,
        handleBulkRename,
        handleSmartCategorize,
        findMatches,
        selectMatch
    }
}
