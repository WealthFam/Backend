import { ref, watch, type Ref } from 'vue'
import { localISOString } from '@/utils/time'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'

/**
 * Triage and Training State Management Composable
 * Handles pending triage transactions and unparsed messages (training area)
 */
export function useTriageState(
    accounts: Ref<any[]>,
    categories: Ref<any[]>,
    showSmartPrompt: Ref<boolean>,
    smartPromptData: Ref<any>,
    fetchData: Function
) {
    const notify = useNotificationStore()
    const auth = useAuthStore()

    // Triage State
    const triageTransactions = ref<any[]>([])
    const triagePagination = ref({ total: 0, limit: 12, skip: 0 })
    const triageSearchQuery = ref('')
    const triageSourceFilter = ref<'ALL' | 'SMS' | 'EMAIL'>('ALL')
    const triageSortKey = ref('date')
    const triageSortOrder = ref<'asc' | 'desc'>('desc')
    const selectedTriageIds = ref<string[]>([])

    // Training State
    const unparsedMessages = ref<any[]>([])
    const trainingPagination = ref({ total: 0, limit: 12, skip: 0 })
    const trainingSearchQuery = ref('')
    const trainingSortKey = ref('created_at')
    const trainingSortOrder = ref<'asc' | 'desc'>('desc')
    const trainingSenderFilter = ref<string | null>(null)
    const trainingSubjectFilter = ref<string | null>(null)
    const selectedTrainingIds = ref<string[]>([])
    const expandedTrainingIds = ref<Set<string>>(new Set())

    // Spam Filter State
    const spamFilters = ref<any[]>([])
    const showSpamManager = ref(false)

    // Modal States
    const showDiscardConfirm = ref(false)
    const showTrainingDiscardConfirm = ref(false)
    const createIgnoreRule = ref(false)
    const triageIdToDiscard = ref<string | null>(null)
    const trainingIdToDiscard = ref<string | null>(null)

    // Training Label Form
    const selectedMessage = ref<any | null>(null)
    const showLabelForm = ref(false)
    const labelForm = ref({
        amount: 0,
        balance: null as number | null,
        credit_limit: null as number | null,
        date: localISOString(),
        account_mask: '',
        recipient: '',
        ref_id: '',
        category: 'Uncategorized',
        type: 'DEBIT',
        exclude_from_reports: false,
        generate_pattern: true
    })

    const loading = ref(false)
    const isProcessingBulk = ref(false)

    /**
     * Fetch triage and training data
     */
    async function fetchTriage(resetSkip = false) {
        loading.value = true
        try {
            if (resetSkip) {
                triagePagination.value.skip = 0
                trainingPagination.value.skip = 0
            }

            // Ensure we have accounts and categories for rendering
            if (accounts.value.length === 0 || categories.value.length === 0) {
                const [accRes, catRes] = await Promise.all([
                    financeApi.getAccounts(auth.selectedMemberId || undefined),
                    financeApi.getCategories(true)
                ])
                accounts.value = accRes.data
                categories.value = catRes.data
            }


            const [res, trainingRes] = await Promise.all([
                financeApi.getTriage({
                    limit: triagePagination.value.limit,
                    skip: triagePagination.value.skip,
                    sort_by: triageSortKey.value,
                    sort_order: triageSortOrder.value,
                    search: triageSearchQuery.value || undefined,
                    source: triageSourceFilter.value !== 'ALL' ? triageSourceFilter.value : undefined,
                    user_id: auth.selectedMemberId || undefined
                } as any),
                financeApi.getTraining({
                    limit: trainingPagination.value.limit,
                    skip: trainingPagination.value.skip,
                    sender_filter: trainingSenderFilter.value || undefined,
                    subject_filter: trainingSubjectFilter.value || undefined,
                    search: trainingSearchQuery.value || undefined,
                    sort_by: trainingSortKey.value,
                    sort_order: trainingSortOrder.value
                })
            ])

            triageTransactions.value = res.data.data.map((t: any) => ({
                ...t,
                category: t.category || 'Uncategorized',
                is_transfer: !!t.is_transfer,
                create_rule: false
            }))
            triagePagination.value.total = res.data.total
            selectedTriageIds.value = []

            unparsedMessages.value = trainingRes.data.data
            trainingPagination.value.total = trainingRes.data.total
            selectedTrainingIds.value = []

        } catch (e) {
            console.error('Failed to fetch triage', e)
        } finally {
            loading.value = false
        }
    }

    /**
     * Approve a triage transaction
    */
    async function approveTriage(txn: any) {
        try {
            const res = await financeApi.approveTriage(txn.id, {
                category: txn.category,
                is_transfer: txn.is_transfer,
                to_account_id: txn.to_account_id,
                exclude_from_reports: txn.exclude_from_reports,
                create_rule: false // Rule creation handled by prompt
            })
            notify.success('Transaction approved')

            // Smart Categorization Prompt Logic
            if (!txn.is_transfer && txn.category && txn.category !== 'Uncategorized') {
                const pattern = txn.recipient || txn.description
                const newTxnId = res.data.transaction_id

                smartPromptData.value = {
                    txnId: newTxnId,
                    category: txn.category,
                    pattern: pattern,
                    count: 0,
                    createRule: true,
                    applyToSimilar: false,
                    excludeFromReports: false
                }
                showSmartPrompt.value = true
            }

            fetchTriage()
            fetchData() // Refresh list view
        } catch (e) {
            notify.error('Approval failed')
        }
    }

    /**
     * Reject a triage transaction
     */
    async function rejectTriage(id: string) {
        triageIdToDiscard.value = id
        showDiscardConfirm.value = true
    }

    /**
     * Confirm discard of triage transaction
     */
    async function confirmDiscard() {
        if (!triageIdToDiscard.value) return
        try {
            await financeApi.rejectTriage(triageIdToDiscard.value, createIgnoreRule.value)
            if (createIgnoreRule.value) {
                notify.success('Pattern will be ignored in future')
            } else {
                notify.success('Transaction discarded')
            }
            fetchTriage()
            showDiscardConfirm.value = false
            triageIdToDiscard.value = null
            createIgnoreRule.value = false
        } catch (e) {
            notify.error('Failed to discard')
        }
    }

    /**
     * Bulk reject triage transactions
     */
    async function handleBulkRejectTriage() {
        if (selectedTriageIds.value.length === 0) return
        isProcessingBulk.value = true
        try {
            await financeApi.bulkRejectTriage(selectedTriageIds.value, createIgnoreRule.value)
            if (createIgnoreRule.value) {
                notify.success(`Ignored ${selectedTriageIds.value.length} patterns for the future`)
            } else {
                notify.success(`Discarded ${selectedTriageIds.value.length} items`)
            }
            createIgnoreRule.value = false
            showDiscardConfirm.value = false
            fetchTriage()
        } catch (e) {
            notify.error('Bulk reject failed')
        } finally {
            isProcessingBulk.value = false
        }
    }

    /**
     * Start labeling a training message
     */
    function startLabeling(msg: any) {
        selectedMessage.value = msg
        const content = msg.raw_content || ''

        // Smart extraction heuristics
        const amtMatch = content.match(/(?:Rs\.?|INR|₹|Amt)\s*([\d,]+(?:\.\d{1,2})?)/i)
        let suggestedAmt = 0
        if (amtMatch) {
            suggestedAmt = parseFloat(amtMatch[1].replace(/,/g, ''))
        }

        const accMatch = content.match(/(?:A\/c|Acct|ending|XX|card)\s*(\d{3,4})/i)
        const suggestedMask = accMatch ? accMatch[1] : ''

        const refMatch = content.match(/(?:Ref|UTR|TXN|ID)\s*:?\s*([A-Z0-9]{8,})/i)
        const suggestedRef = refMatch ? refMatch[1] : ''

        const isCredit = /credit|received|deposit|incoming|refund/i.test(content)
        const suggestedType = isCredit ? 'CREDIT' : 'DEBIT'

        const dateStr = msg.created_at ? localISOString(new Date(msg.created_at)) : localISOString()

        labelForm.value = {
            amount: suggestedAmt,
            balance: null,
            credit_limit: null,
            date: dateStr,
            account_mask: suggestedMask,
            recipient: '',
            ref_id: suggestedRef,
            category: 'Uncategorized',
            type: suggestedType,
            exclude_from_reports: false,
            generate_pattern: true
        }
        showLabelForm.value = true
    }

    /**
     * Submit label form
     */
    async function handleLabelSubmit() {
        if (!selectedMessage.value) return
        try {
            await financeApi.labelMessage(selectedMessage.value.id, labelForm.value)
            notify.success('Message labeled and moved to triage')
            showLabelForm.value = false
            selectedMessage.value = null
            fetchTriage()
        } catch (e) {
            notify.error('Failed to label message')
        }
    }

    /**
     * Dismiss a training message
     */
    async function dismissTraining(id: string) {
        trainingIdToDiscard.value = id
        showTrainingDiscardConfirm.value = true
    }

    /**
     * Confirm training message dismissal
     */
    async function confirmTrainingDiscard() {
        if (!trainingIdToDiscard.value) return
        try {
            await financeApi.dismissTrainingMessage(trainingIdToDiscard.value, createIgnoreRule.value)
            if (createIgnoreRule.value) {
                notify.success('Pattern will be ignored in future')
            } else {
                notify.success('Message dismissed')
            }
            fetchTriage()
            showTrainingDiscardConfirm.value = false
            trainingIdToDiscard.value = null
            createIgnoreRule.value = false
        } catch (e) {
            notify.error('Failed to dismiss')
        }
    }

    /**
     * Bulk dismiss training messages
     */
    async function handleBulkDismissTrainingConfirm() {
        if (selectedTrainingIds.value.length === 0) return
        try {
            await financeApi.bulkDismissTraining(selectedTrainingIds.value, createIgnoreRule.value)
            if (createIgnoreRule.value) {
                notify.success(`Ignored ${selectedTrainingIds.value.length} patterns for future`)
            } else {
                notify.success('Messages dismissed')
            }
            fetchTriage()
            createIgnoreRule.value = false
            selectedTrainingIds.value = []
        } catch (e) {
            notify.error('Bulk dismiss failed')
        }
    }

    /**
     * Handle bulk dismiss with modal
     */
    async function handleBulkDismissTraining() {
        if (selectedTrainingIds.value.length === 0) return
        trainingIdToDiscard.value = null
        showTrainingDiscardConfirm.value = true
    }

    /**
     * Confirm global training dismiss (handles both single and bulk)
     */
    async function handleConfirmGlobalTrainingDismiss() {
        if (trainingIdToDiscard.value) {
            await confirmTrainingDiscard()
        } else {
            await handleBulkDismissTrainingConfirm()
            showTrainingDiscardConfirm.value = false
        }
    }

    /**
     * Toggle select all triage
     */
    function toggleSelectAllTriage() {
        if (selectedTriageIds.value.length === triageTransactions.value.length) {
            selectedTriageIds.value = []
        } else {
            selectedTriageIds.value = triageTransactions.value.map(t => t.id)
        }
    }

    /**
     * Toggle select all training
     */
    function toggleSelectAllTraining() {
        if (selectedTrainingIds.value.length === unparsedMessages.value.length) {
            selectedTrainingIds.value = []
        } else {
            selectedTrainingIds.value = unparsedMessages.value.map(m => m.id)
        }
    }

    /**
     * Toggle training message expand/collapse
     */
    function toggleTrainingExpand(id: string) {
        if (expandedTrainingIds.value.has(id)) {
            expandedTrainingIds.value.delete(id)
        } else {
            expandedTrainingIds.value.add(id)
        }
    }

    /**
     * Mark message as spam (permanent block)
     */
    async function markAsSpam(id: string) {
        try {
            await financeApi.markAsSpam(id)
            notify.success('Marked as spam. Future messages from this sender will be blocked.')
            fetchTriage()
        } catch (e) {
            notify.error('Failed to mark as spam')
        }
    }

    /**
     * Fetch spam filters
     */
    async function fetchSpamFilters() {
        try {
            const res = await financeApi.getSpamFilters()
            spamFilters.value = res // Client now returns response.data.data
        } catch (e) {
            console.error('Failed to fetch spam filters')
        }
    }

    /**
     * Remove a spam filter
     */
    async function removeSpamFilter(id: string) {
        try {
            await financeApi.deleteSpamFilter(id)
            notify.success('Spam filter removed')
            fetchSpamFilters()
        } catch (e) {
            notify.error('Failed to remove filter')
        }
    }

    /**
     * Find similar messages (filter by sender)
     */
    function findSimilar(sender: string) {
        trainingSenderFilter.value = sender
        trainingPagination.value.skip = 0
        fetchTriage()
    }

    // Watchers
    watch([triageSortKey, triageSortOrder], () => {
        triagePagination.value.skip = 0
        fetchTriage()
    })

    watch([trainingSortKey, trainingSortOrder, trainingSenderFilter, trainingSubjectFilter], () => {
        trainingPagination.value.skip = 0
        fetchTriage()
    })

    // Watch source filter changes (immediate)
    watch(triageSourceFilter, () => {
        triagePagination.value.skip = 0
        fetchTriage()
    })

    // Watch search query changes (debounced)
    let searchDebounce: any = null
    watch(triageSearchQuery, () => {
        if (searchDebounce) clearTimeout(searchDebounce)
        searchDebounce = setTimeout(() => {
            triagePagination.value.skip = 0
            fetchTriage()
        }, 400)
    })

    watch(trainingSearchQuery, () => {
        if (searchDebounce) clearTimeout(searchDebounce)
        searchDebounce = setTimeout(() => {
            trainingPagination.value.skip = 0
            fetchTriage()
        }, 400)
    })

    return {
        // State
        triageTransactions,
        triagePagination,
        triageSearchQuery,
        triageSourceFilter,
        triageSortKey,
        triageSortOrder,
        selectedTriageIds,
        unparsedMessages,
        trainingPagination,
        trainingSearchQuery,
        trainingSortKey,
        trainingSortOrder,
        trainingSenderFilter,
        trainingSubjectFilter,
        selectedTrainingIds,
        expandedTrainingIds,
        spamFilters,
        showSpamManager,
        showDiscardConfirm,
        showTrainingDiscardConfirm,
        createIgnoreRule,
        triageIdToDiscard,
        trainingIdToDiscard,
        selectedMessage,
        showLabelForm,
        labelForm,
        loading,
        isProcessingBulk,

        // Methods
        fetchTriage,
        approveTriage,
        rejectTriage,
        confirmDiscard,
        handleBulkRejectTriage,
        startLabeling,
        handleLabelSubmit,
        dismissTraining,
        confirmTrainingDiscard,
        handleBulkDismissTrainingConfirm,
        handleBulkDismissTraining,
        handleConfirmGlobalTrainingDismiss,
        toggleSelectAllTriage,
        toggleSelectAllTraining,
        toggleTrainingExpand,
        markAsSpam,
        fetchSpamFilters,
        removeSpamFilter,
        findSimilar
    }
}
