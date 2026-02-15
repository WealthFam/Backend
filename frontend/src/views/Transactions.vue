<script setup lang="ts">
import { ref, onMounted, watch, reactive } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { useRoute } from 'vue-router'

import ImportModal from '@/components/ImportModal.vue'
import SmartPromptModal from '@/components/SmartPromptModal.vue'

import SpendingHeatmap from '@/components/SpendingHeatmap.vue'
import TransactionList from './transactions/TransactionList.vue'
import TransactionTriage from './transactions/TransactionTriage.vue'
import TransactionModal from './transactions/TransactionModal.vue'
import VendorAliasModal from '@/components/VendorAliasModal.vue'
import {
    LayoutList,
    Inbox,
    Map as MapIcon,
    Bot
} from 'lucide-vue-next'

// Composables

import { useTransactionState } from '@/composables/useTransactionState'
import { useTriageState } from '@/composables/useTriageState'
import { useTransactionModals } from '@/composables/useTransactionModals'
import { useAuthStore } from '@/stores/auth'
import { financeApi } from '@/api/client'

// Global State
const route = useRoute()

// const { formatAmount } = useCurrency()

// Master Data (shared across composables)
const accounts = ref<any[]>([])
const categories = ref<any[]>([])
const budgets = ref<any[]>([])
const loans = ref<any[]>([])
const expenseGroups = ref<any[]>([])

// UI State
const showImportModal = ref(false)
const activeTab = ref<'list' | 'analytics' | 'triage' | 'heatmap'>('list')
const activeTriageSubTab = ref<'pending' | 'training'>('pending')



// Smart Categorization Modal (shared between composables)
const showSmartPrompt = ref(false)
const smartPromptData = ref({
    txnId: '',
    category: '',
    pattern: '',
    count: 0,
    createRule: true,
    applyToSimilar: true,
    excludeFromReports: false
})



// Initialize Transaction State Composable
const {
    transactions,
    loading,
    total,
    selectedAccount,
    searchQuery,
    categoryFilter,
    startDate,
    endDate,
    selectedTimeRange,

    page,
    pageSize,
    txnSortKey,
    txnSortOrder,
    selectedIds,
    showDeleteConfirm,
    fetchData,
    handleTimeRangeChange,
    toggleTxnSort,
    refreshAccounts,
    confirmDelete
} = useTransactionState(route, accounts, categories, budgets, loans, expenseGroups)

const {
    triageTransactions,
    triagePagination,
    triageSearchQuery,
    triageSourceFilter,
    triageSortKey,
    triageSortOrder,
    selectedTriageIds,
    unparsedMessages,
    trainingPagination,
    trainingSortKey,
    trainingSortOrder,
    selectedTrainingIds,
    fetchTriage,
    approveTriage,
    rejectTriage,
    handleBulkRejectTriage,
    startLabeling,
    dismissTraining,
    handleBulkDismissTraining,
    showLabelForm,
    labelForm,
    handleLabelSubmit,
    selectedMessage,
    // Confirmation States
    showDiscardConfirm,
    showTrainingDiscardConfirm,
    createIgnoreRule,
    triageIdToDiscard,
    trainingIdToDiscard,
    // Methods
    confirmDiscard,
    confirmTrainingDiscard,
    handleConfirmGlobalTrainingDismiss
} = useTriageState(accounts, categories, showSmartPrompt, smartPromptData, fetchData)

// Initialize Modals Composable
const {
    showModal,
    isEditing,
    potentialMatches,
    isSearchingMatches,
    matchesSearched,
    form,
    openEditModal,
    handleSubmit,
    handleSmartCategorize,
    findMatches,
    selectMatch
} = useTransactionModals(selectedAccount, accounts, budgets, transactions, fetchData, showSmartPrompt, smartPromptData, refreshAccounts)


// Heatmap Data
const heatmapData = ref<any[]>([])
async function fetchHeatmap() {
    try {
        const res = await financeApi.getHeatmapData(startDate.value, endDate.value, auth.selectedMemberId || undefined)
        heatmapData.value = res.data
    } catch (e) {
        console.error('Failed to fetch heatmap', e)
    }
}





// Search debounce
let searchDebounce: any = null
watch(searchQuery, () => {
    if (searchDebounce) clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => {
        page.value = 1
        fetchData()
    }, 400)
})

// Watch for global member filter changes
const auth = useAuthStore()
watch(() => auth.selectedMemberId, () => {
    // Reset data and re-fetch everything
    accounts.value = [] // Force re-fetch of filtered accounts
    page.value = 1
    fetchData()
    fetchTriage()
    fetchHeatmap()
})

// --- Vendor Alias Logic ---
const showAliasModal = ref(false)
const aliasForm = reactive({
    pattern: '',
    alias: ''
})

function openAliasModal(txn: any) {
    aliasForm.pattern = txn.description || txn.recipient || ''
    aliasForm.alias = txn.recipient || ''
    showAliasModal.value = true
}

onMounted(() => {
    fetchData()
    fetchTriage() // Pre-fetch count
})
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Premium Header -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="4">
                        <div class="d-flex align-center">
                            <h1 class="text-h6 font-weight-black text-content">Transactions</h1>
                        </div>
                        <p class="text-subtitle-2 text-medium-emphasis font-weight-bold mt-1 opacity-70">
                            Track and manage your family's spending
                        </p>
                    </v-col>

                    <v-col cols="12" md="8" class="d-flex flex-column flex-md-row align-md-center justify-end gap-3">
                        <!-- Navigation Tabs -->
                        <div class="premium-pill-tabs flex-grow-1 flex-md-grow-0 d-flex overflow-x-auto">
                            <v-tabs v-model="activeTab" color="primary" density="comfortable" hide-slider show-arrows
                                class="rounded-xl">
                                <v-tab value="list" class="premium-tab" rounded="xl" @click="fetchData">
                                    <div class="d-flex align-center gap-2">
                                        <LayoutList :size="16" />
                                        <span>List</span>
                                    </div>
                                </v-tab>
                                <v-tab value="triage" class="premium-tab" rounded="xl" @click="fetchTriage">
                                    <div class="d-flex align-center gap-2">
                                        <Inbox :size="16" />
                                        <span>Triage</span>
                                        <v-chip v-if="triagePagination.total > 0" size="x-small" color="primary"
                                            class="ml-1 font-weight-black">
                                            {{ triageTransactions.length }}
                                        </v-chip>
                                    </div>
                                </v-tab>
                                <v-tab value="heatmap" class="premium-tab" rounded="xl" @click="fetchHeatmap">
                                    <div class="d-flex align-center gap-2">
                                        <MapIcon :size="16" />
                                        <span>Heatmap</span>
                                    </div>
                                </v-tab>
                            </v-tabs>
                        </div>
                    </v-col>
                </v-row>

                <!-- CONTENT AREA -->
                <v-window v-model="activeTab" class="overflow-visible">
                    <v-window-item value="list">
                        <TransactionList v-bind="{
                            transactions, accounts, categories, expenseGroups,
                            loading, total, selectedAccount, categoryFilter,
                            searchQuery, startDate, endDate, selectedTimeRange,
                            page, pageSize, txnSortKey, txnSortOrder
                        }" v-model:selectedIds="selectedIds"
                            @update:selectedAccount="selectedAccount = $event; page = 1; fetchData()"
                            @update:categoryFilter="categoryFilter = $event; page = 1; fetchData()"
                            @update:searchQuery="searchQuery = $event"
                            @update:startDate="startDate = $event; page = 1; fetchData()"
                            @update:endDate="endDate = $event; page = 1; fetchData()"
                            @update:selectedTimeRange="selectedTimeRange = $event; handleTimeRangeChange($event)"
                            @update:page="page = $event; fetchData()"
                            @update:pageSize="pageSize = $event; page = 1; fetchData()" @sortChange="toggleTxnSort"
                            @editTxn="openEditModal" @mapVendor="openAliasModal"
                            @deleteSelected="showDeleteConfirm = true" @importCsv="showImportModal = true"
                            @fetchData="fetchData"
                            @resetFilters="selectedTimeRange = 'all'; startDate = ''; endDate = ''; searchQuery = ''; categoryFilter = ''; fetchData()" />
                    </v-window-item>

                    <v-window-item value="triage">
                        <TransactionTriage v-bind="{
                            activeSubTab: activeTriageSubTab, accounts, categories,
                            triageTransactions, triagePagination, triageSearchQuery,
                            triageSourceFilter, triageSortKey, triageSortOrder,
                            unparsedMessages, trainingPagination, trainingSortKey,
                            trainingSortOrder,
                            // Confirmation States
                            showDiscardConfirm, showTrainingDiscardConfirm, createIgnoreRule,
                            triageIdToDiscard, trainingIdToDiscard
                        }" v-model:selectedTriageIds="selectedTriageIds"
                            v-model:selectedTrainingIds="selectedTrainingIds"
                            @update:activeSubTab="activeTriageSubTab = $event"
                            @update:triageSearchQuery="triageSearchQuery = $event"
                            @update:triageSourceFilter="triageSourceFilter = $event as any"
                            @update:triageSortKey="triageSortKey = $event"
                            @update:triageSortOrder="triageSortOrder = $event"
                            @update:triagePagination="triagePagination = $event; fetchTriage()"
                            @update:trainingSortKey="trainingSortKey = $event"
                            @update:trainingSortOrder="trainingSortOrder = $event"
                            @update:trainingPagination="trainingPagination = $event; fetchTriage()"
                            @update:showDiscardConfirm="showDiscardConfirm = $event"
                            @update:showTrainingDiscardConfirm="showTrainingDiscardConfirm = $event"
                            @update:createIgnoreRule="createIgnoreRule = $event" @approveTriage="approveTriage"
                            @rejectTriage="rejectTriage" @bulkRejectTriage="handleBulkRejectTriage"
                            @startLabeling="startLabeling" @dismissTraining="dismissTraining"
                            @bulkDismissTraining="handleBulkDismissTraining" @confirmDiscard="confirmDiscard"
                            @confirmTrainingDiscard="confirmTrainingDiscard"
                            @confirmBulkDiscard="handleBulkRejectTriage"
                            @confirmBulkTrainingDiscard="handleConfirmGlobalTrainingDismiss"
                            @refreshTriage="() => { fetchTriage(); fetchData(); }" />
                    </v-window-item>

                    <v-window-item value="heatmap">
                        <div class="content-card pa-6 glass-card">
                            <SpendingHeatmap :data="heatmapData" />
                        </div>
                    </v-window-item>
                </v-window>
            </div>
        </v-container>

        <!-- Modals -->
        <ImportModal :isOpen="showImportModal" @close="showImportModal = false" @import-success="fetchData" />
        <SmartPromptModal :isOpen="showSmartPrompt" :data="smartPromptData" @close="showSmartPrompt = false"
            @confirm="handleSmartCategorize" />
        <TransactionModal :isOpen="showModal" :isEditing="isEditing" :form="form" :accounts="accounts"
            :categories="categories" :budgets="budgets" :expenseGroups="expenseGroups"
            :potentialMatches="potentialMatches" :isSearchingMatches="isSearchingMatches"
            :matchesSearched="matchesSearched" @close="showModal = false" @submit="handleSubmit"
            @findMatches="findMatches" @selectMatch="selectMatch" />

        <VendorAliasModal v-model="showAliasModal" :initial-pattern="aliasForm.pattern" :initial-alias="aliasForm.alias"
            @saved="() => { fetchData(); fetchTriage(); }" />

        <!-- Labeling Message Modal (Interactive Training) -->
        <v-dialog v-model="showLabelForm" persistent max-width="800">
            <v-card class="glass-card overflow-hidden" rounded="xl">
                <v-toolbar color="warning" density="compact">
                    <Bot :size="18" class="ml-4 text-primary" />
                    <v-toolbar-title class="text-subtitle-1 font-weight-bold">Train Transaction Parser</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-btn icon="X" variant="text" @click="showLabelForm = false"></v-btn>
                </v-toolbar>

                <div class="labeling-layout pa-4">
                    <!-- Left: Raw Message -->
                    <div class="labeling-raw h-100">
                        <div class="section-label mb-2">Message Content</div>
                        <div class="raw-content-box flex-grow-1 mb-4">
                            {{ selectedMessage?.raw_content || selectedMessage?.raw_message || 'N/A' }}
                        </div>
                        <div class="raw-meta">
                            <div class="mb-1"><span class="font-weight-bold">Sender:</span> {{ selectedMessage?.sender
                                }}
                            </div>
                            <div class="mb-1"><span class="font-weight-bold">Source:</span> {{ selectedMessage?.source
                                }}
                            </div>
                            <div><span class="font-weight-bold">Received:</span> {{
                                selectedMessage?.created_at ? new Date(selectedMessage.created_at).toLocaleString() :
                                    'N/A' }}</div>
                        </div>
                    </div>

                    <!-- Right: Form -->
                    <div class="labeling-form">
                        <div class="section-label mb-2">Extracted Information</div>
                        <v-row dense>
                            <v-col cols="12" md="6">
                                <v-text-field v-model.number="labelForm.amount" label="Amount" prefix="₹" type="number"
                                    density="comfortable" variant="outlined" hide-details class="mb-3"></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-select v-model="labelForm.type" label="Type" :items="['DEBIT', 'CREDIT']"
                                    density="comfortable" variant="outlined" hide-details class="mb-3"></v-select>
                            </v-col>
                            <v-col cols="12">
                                <v-text-field v-model="labelForm.recipient" label="Merchant / Recipient"
                                    placeholder="e.g. Amazon, Starbucks" density="comfortable" variant="outlined"
                                    hide-details class="mb-3"></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-text-field v-model="labelForm.account_mask" label="Account Mask"
                                    placeholder="Last 4 digits" density="comfortable" variant="outlined" hide-details
                                    class="mb-3"></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-text-field v-model="labelForm.ref_id" label="Reference ID" placeholder="Txn ID"
                                    density="comfortable" variant="outlined" hide-details class="mb-3"></v-text-field>
                            </v-col>

                            <v-divider class="my-2 w-100"></v-divider>
                            <v-col cols="12">
                                <p class="text-caption font-weight-bold text-warning mb-2">BALANCE ANCHORING (OPTIONAL)
                                </p>
                            </v-col>

                            <v-col cols="12" md="6">
                                <v-text-field v-model.number="labelForm.balance" label="Bank Balance"
                                    placeholder="Balance after txn" prefix="₹" type="number" density="comfortable"
                                    variant="outlined" hide-details class="mb-3"></v-text-field>
                            </v-col>
                            <v-col cols="12" md="6">
                                <v-text-field v-model.number="labelForm.credit_limit" label="Credit Limit"
                                    placeholder="If card txn" prefix="₹" type="number" density="comfortable"
                                    variant="outlined" hide-details class="mb-3"></v-text-field>
                            </v-col>

                            <v-col cols="12">
                                <v-divider class="my-2"></v-divider>
                            </v-col>

                            <v-col cols="12">
                                <v-checkbox v-model="labelForm.generate_pattern" label="Create Auto-Categorization Rule"
                                    density="compact" color="primary" hide-details></v-checkbox>
                            </v-col>
                        </v-row>

                        <div class="d-flex justify-end gap-2 mt-4">
                            <v-btn variant="text" @click="showLabelForm = false">Cancel</v-btn>
                            <v-btn color="warning" @click="handleLabelSubmit" prepend-icon="Brain">Train &
                                Approve</v-btn>
                        </div>
                    </div>
                </div>
            </v-card>
        </v-dialog>


        <!-- Delete Confirmation Dialog -->
        <v-dialog v-model="showDeleteConfirm" max-width="450">
            <v-card class="glass-card" rounded="xl">
                <v-card-text class="text-center pa-6">
                    <div class="text-h2 mb-4">🗑️</div>
                    <div class="text-h5 font-weight-bold mb-2">Delete Transactions?</div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        Are you sure you want to delete <span class="font-weight-bold text-primary">{{
                            selectedIds.size }}</span> selected
                        transactions? This action cannot be undone.
                    </p>

                    <div class="d-flex gap-3 justify-center">
                        <v-btn variant="text" @click="showDeleteConfirm = false" :disabled="loading" rounded="lg">
                            Cancel
                        </v-btn>
                        <v-btn color="error" @click="async () => { await confirmDelete(); fetchData() }"
                            :loading="loading" rounded="lg" prepend-icon="Trash2">
                            Delete Forever
                        </v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>
    </MainLayout>
</template>

<style scoped>
.settings-page {
    min-height: calc(100vh - 64px);
    background: rgb(var(--v-theme-background));
    position: relative;
    overflow: hidden;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

/* Mesh Background */
.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    z-index: 1;
    border-radius: 50%;
    animation: blob-float 20s infinite alternate;
}

.blob-1 {
    background: rgb(var(--v-theme-primary));
    width: 600px;
    height: 600px;
    top: -200px;
    right: -100px;
}

.blob-2 {
    background: rgb(var(--v-theme-secondary));
    width: 400px;
    height: 400px;
    bottom: -100px;
    left: -100px;
    animation-delay: -5s;
}

.blob-3 {
    background: rgb(var(--v-theme-success));
    width: 300px;
    height: 300px;
    top: 40%;
    left: 30%;
    animation-delay: -8s;
}

@keyframes blob-float {
    0% {
        transform: translate(0, 0) scale(1);
    }

    100% {
        transform: translate(20px, -20px) scale(1.1);
    }
}

/* Premium Tabs */
.premium-pill-tabs {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(10px);
    padding: 6px;
    border-radius: 24px;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-tab {
    text-transform: none !important;
    letter-spacing: 0;
    font-weight: 700;
    font-size: 0.9rem;
    color: rgb(var(--v-theme-on-surface), 0.6);
    transition: all 0.3s ease;
    min-width: 120px;
}

.premium-tab.v-tab--selected {
    background: rgb(var(--v-theme-primary));
    color: white !important;
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 24px;
}



/* Triage Sub-Tabs */
.triage-tabs {
    display: flex;
    gap: 1rem;
    border-bottom: 2px solid rgba(var(--v-border-color), 0.05);
    padding-bottom: 0.1rem;
}

.triage-tab-btn {
    padding: 0.75rem 1.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface), 0.6);
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    transition: all 0.2s ease;
    margin-bottom: -2px;
}

.triage-tab-btn:hover {
    color: #4f46e5;
}

.triage-tab-btn.active {
    color: #4f46e5;
    border-bottom-color: #4f46e5;
}

/* Training Logic Styles */
.training-card {
    border-left: 4px solid #f59e0b;
}

.training-content {
    background: #fdfaf5;
    padding: 0.75rem;
    border-radius: 0.5rem;
    border: 1px dashed #fbbf24;
}

.training-sender,
.training-subject {
    font-size: 0.75rem;
    font-weight: 600;
    color: #92400e;
    margin-bottom: 0.25rem;
}

.training-raw-preview-premium {
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: 0.75rem;
    line-height: 1.4;
    color: #4b5563;
    white-space: pre-wrap;
    margin: 0;
    max-height: 100px;
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.training-raw-preview-premium.expanded {
    max-height: 1000px;
}

.read-more-btn {
    background: none;
    border: none;
    color: #4f46e5;
    font-size: 0.7rem;
    font-weight: 700;
    cursor: pointer;
    padding: 0.25rem 0;
    margin-top: 0.25rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.read-more-btn:hover {
    text-decoration: underline;
}

.btn-label {
    background: #f59e0b;
    border-color: #f59e0b;
}

.btn-label:hover {
    background: #d97706;
}

/* Labeling Modal Layout */
.labeling-layout {
    display: grid;
    grid-template-columns: 1fr 1.2fr;
    gap: 1rem;
    padding: 1rem;
}

.labeling-raw {
    background: #f9fafb;
    border-radius: 0.75rem;
    padding: 0.75rem;
    border: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
}

.raw-content-box {
    background: white;
    padding: 0.875rem;
    border-radius: 0.5rem;
    font-family: monospace;
    font-size: 0.75rem;
    white-space: pre-wrap;
    border: 1px solid #f3f4f6;
    flex-grow: 1;
    overflow-y: auto;
    max-height: 300px;
    color: #111827;
}

.raw-meta {
    margin-top: 1rem;
    font-size: 0.75rem;
    color: #6b7280;
}

.section-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.5rem;
    letter-spacing: 0.05em;
}

.labeling-form .form-group {
    margin-bottom: 0.75rem;
}

.labeling-form .form-label {
    font-size: 0.75rem;
    margin-bottom: 2px;
}

.labeling-form .form-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
}

.check-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    background: #eef2ff;
    padding: 0.75rem;
    border-radius: 0.5rem;
    margin-top: 1rem;
}

.check-group input {
    width: 1.125rem;
    height: 1.125rem;
    cursor: pointer;
}

.check-group label {
    font-size: 0.8125rem;
    color: #4338ca;
    font-weight: 500;
    cursor: pointer;
}

/* Legacy styles below ... */
/* Modern Compact Design System */

/* Page Header */
.page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.header-left {
    display: flex;
    align-items: baseline;
    gap: 0.75rem;
}

.page-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface));
    margin: 0;
}

.transaction-count {
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: 400;
}

.header-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.account-select {
    min-width: 200px;
}

.account-select :deep(.select-trigger) {
    padding: 0.5rem 0.875rem;
    font-size: 0.875rem;
    display: flex;
    align-items: center;
}

/* Compact Buttons - match dropdown */
.btn-compact {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.5rem 0.875rem;
    font-size: 0.875rem;
    font-weight: 500;
    border-radius: 0.375rem;
    border: 1px solid transparent;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
}

.btn-compact svg {
    flex-shrink: 0;
}

.btn-compact:disabled {
    opacity: 0.5;
    cursor: not-allowed;
}

.btn-primary {
    background: #4f46e5;
    color: white;
    border-color: #4f46e5;
}

.btn-primary:hover:not(:disabled) {
    background: #4338ca;
    border-color: #4338ca;
}

.btn-secondary {
    background: white;
    color: #374151;
    border-color: #d1d5db;
}

.btn-secondary:hover:not(:disabled) {
    background: #f9fafb;
    border-color: #9ca3af;
}

.btn-danger {
    background: white;
    color: #dc2626;
    border-color: #fecaca;
}

.btn-danger:hover:not(:disabled) {
    background: #fef2f2;
    border-color: #fca5a5;
}

/* Loading State */
.loading-state {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 4rem 2rem;
    color: #6b7280;
    font-size: 0.875rem;
}

.spinner {
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid #e5e7eb;
    border-top-color: #4f46e5;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

/* Budget Preview Tag (Modal) */
.budget-preview-tag {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    padding: 0.125rem 0.625rem;
    background: #ecfdf5;
    color: #065f46;
    border-radius: 999px;
    font-size: 0.725rem;
    font-weight: 600;
    border: 1px solid #d1fae5;
    animation: slideInLeft 0.3s ease-out;
}

.budget-preview-tag.danger {
    background: #fef2f2;
    color: #991b1b;
    border-color: #fee2e2;
}

.budget-preview-tag .dot {
    width: 5px;
    height: 5px;
    background: currentColor;
    border-radius: 50%;
}

@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-10px);
    }

    to {
        opacity: 1;
        transform: translateX(0);
    }
}

/* Content Card */
.table-container {
    background: rgb(var(--v-theme-surface));
    border-radius: 0.75rem;
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06);
    overflow-x: auto;
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    margin-bottom: 1.5rem;
    position: relative;
}

/* Modern Table */
.modern-table {
    width: 100%;
    min-width: 900px;
    border-collapse: collapse;
    font-size: 0.875rem;
    table-layout: fixed;
}

.modern-table thead th {
    background: #f9fafb;
    padding: 0.5rem 0.6rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.7rem;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    border-bottom: 2px solid #e5e7eb;
    position: sticky;
    top: 0;
    z-index: 10;
}

.modern-table tbody td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid #f3f4f6;
    color: #374151;
    vertical-align: middle;
}

.modern-table tbody tr:last-child td {
    border-bottom: none;
}

/* Zebra striping */
.modern-table tbody tr:nth-child(even) {
    background: #fafafa;
}

.modern-table tbody tr:hover {
    background: #f3f4f6;
}

.modern-table tbody tr.row-selected {
    background: #eff6ff;
}

.modern-table tbody tr.row-selected:hover {
    background: #dbeafe;
}

/* Column Sizing */
.col-checkbox {
    width: 40px;
    text-align: center;
    padding-left: 1rem !important;
}

.col-icon {
    width: 36px;
    text-align: center;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
}

.col-date {
    width: 110px;
    min-width: 110px;
    font-variant-numeric: tabular-nums;
}

.col-recipient {
    width: 250px;
    min-width: 200px;
    font-weight: 500;
}

.col-description {
    width: auto;
    min-width: 300px;
    color: #4b5563;
}

.col-amount {
    width: 120px;
    text-align: right;
    padding-right: 1.5rem !important;
}

.col-actions {
    width: 50px;
    text-align: center;
    padding-right: 1rem !important;
}

/* Table Elements */
.source-icon {
    font-size: 1.125rem;
    opacity: 0.7;
}

/* Date Cell */
.date-cell {
    line-height: 1.3;
}

.date-day {
    font-size: 0.875rem;
    font-weight: 600;
    color: #111827;
}

.date-meta {
    font-size: 0.65rem;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 0.025em;
}

/* Transaction Description */
.txn-description {
    line-height: 1.4;
}

.txn-primary {
    color: #111827;
    font-weight: 600;
    font-size: 0.875rem;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 0rem;
}

.txn-description-text {
    font-size: 0.75rem;
    color: #6b7280;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    margin-bottom: 0.125rem;
}

.txn-meta-row {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
}

.account-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    background: #f1f5f9;
    color: #475569;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid #e2e8f0;
}

.txn-source-meta {
    font-size: 0.65rem;
    color: #94a3b8;
    margin-top: 2px;
    display: flex;
    align-items: center;
    gap: 4px;
    font-weight: 500;
}

.source-icon-mini {
    font-size: 0.75rem;
}

.location-trigger {
    cursor: help;
    font-size: 0.8rem;
    margin-left: 4px;
    opacity: 0.8;
}

.txn-secondary {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    background: #fef3c7;
    color: #92400e;
    border-radius: 9999px;
    font-size: 0.65rem;
    text-transform: uppercase;
    font-weight: 500;
    letter-spacing: 0.025em;
    white-space: nowrap;
}

/* Category Pill */
.category-pill-wrapper {
    display: inline-block;
}

.category-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.15rem 0.6rem;
    background: #ffffff;
    color: #334155;
    border-radius: 6px;
    font-size: 0.725rem;
    font-weight: 600;
    white-space: nowrap;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.category-icon {
    font-size: 0.8rem;
}

.ai-badge-mini.active-transfer {
    background: #ecfdf5;
    color: #059669;
    border-color: #a7f3d0;
}

.ai-badge-mini.active-hidden {
    background: #fff1f2;
    color: #e11d48;
    border-color: #fecdd3;
}

.ai-badge-mini.active-emi {
    background: #eff6ff;
    color: #2563eb;
    border-color: #bfdbfe;
}

/* Amount Cell with Icon */
.amount-cell {
    display: flex;
    align-items: center;
    justify-content: flex-end;
    gap: 0.375rem;
}

.amount-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.125rem;
    height: 1.125rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 700;
}

.amount-cell.is-income .amount-icon {
    background: #d1fae5;
    color: #059669;
}

.amount-cell.is-expense .amount-icon {
    background: #fee2e2;
    color: #dc2626;
}

.amount-value {
    font-variant-numeric: tabular-nums;
    font-weight: 600;
    font-size: 0.875rem;
}

.amount-cell.is-income .amount-value {
    color: #059669;
}

.amount-cell.is-expense .amount-value {
    color: #374151;
}

/* Remove old amount styling */
.amount-positive {
    color: #059669;
    font-weight: 600;
}

.amount-negative {
    color: #374151;
    font-weight: 500;
}

/* Filter Bar */
.filter-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
    padding: 0.625rem 1rem;
    background: rgba(var(--v-theme-on-surface), 0.02);
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 0.75rem;
    margin-bottom: 1.25rem;
}

.filter-main {
    display: flex;
    align-items: center;
    gap: 1.25rem;
}

.filter-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.list-search-container {
    position: relative;
    display: flex;
    align-items: center;
}

.search-icon-small {
    position: absolute;
    left: 0.75rem;
    font-size: 0.8rem;
    color: #9ca3af;
}

.list-search-input {
    padding: 0.45rem 0.75rem 0.45rem 2rem;
    font-size: 0.8125rem;
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    background: white;
    width: 220px;
    outline: none;
    transition: all 0.2s;
}

.list-search-input:focus {
    border-color: #6366f1;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.category-filter-select {
    min-width: 180px;
}

.filter-label {
    font-size: 0.7rem;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    white-space: nowrap;
}

.filter-divider {
    width: 1px;
    height: 24px;
    background: #e5e7eb;
    margin: 0 0.25rem;
}

.range-pill-group {
    display: flex;
    gap: 0.375rem;
    background: #f3f4f6;
    padding: 2px;
    border-radius: 0.5rem;
    height: 36px;
    box-sizing: border-box;
    align-items: center;
}

.range-pill {
    padding: 0 0.75rem;
    height: 32px;
    border: none;
    background: transparent;
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface), 0.7);
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
    display: flex;
    align-items: center;
}

.range-pill:hover:not(.active) {
    color: #111827;
    background: #e5e7eb;
}

.range-pill.active {
    background: white;
    color: #4f46e5;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.filter-divider {
    width: 1px;
    height: 1.5rem;
    background: #e5e7eb;
}

.date-input {
    height: 36px;
    padding: 0 0.625rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    color: #374151;
    background: white;
    outline: none;
    transition: border-color 0.2s;
    box-sizing: border-box;
}

.date-input:focus {
    border-color: #4f46e5;
}

.filter-separator {
    font-size: 0.75rem;
    color: #9ca3af;
    font-weight: 500;
}

.animate-in {
    animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateX(-10px);
    }

    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.header-divider {
    width: 1px;
    height: 1.5rem;
    background: #e5e7eb;
    margin: 0 0.5rem;
}

.btn-link {
    background: none;
    border: none;
    color: #4f46e5;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0.5rem;
    border-radius: 0.375rem;
    transition: background 0.2s;
}

.btn-link:hover {
    background: #eff6ff;
}

/* Icon Button */
.icon-btn-edit {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    padding: 0;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 0.5rem;
    color: #64748b;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.icon-btn-edit:hover {
    background: #f8fafc;
    color: #4f46e5;
    border-color: #4f46e5;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Empty State */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 2rem;
    color: #9ca3af;
    gap: 0.75rem;
}

.empty-state svg {
    opacity: 0.5;
}

.empty-state p {
    margin: 0;
    font-size: 0.875rem;
}

/* Pagination Bar */
.pagination-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    background: rgba(var(--v-theme-on-surface), 0.02);
}

.page-info {
    font-size: 0.875rem;
    color: #6b7280;
}

.pagination-controls {
    display: flex;
    gap: 0.25rem;
}

.page-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    padding: 0;
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 0.375rem;
    color: #374151;
    cursor: pointer;
    transition: all 0.15s ease;
}

.page-btn:hover:not(:disabled) {
    background: #f9fafb;
    border-color: #d1d5db;
}

.page-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}

/* Modal Button Overrides for Existing Modals */
.btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.5rem 0.875rem;
    border-radius: 0.375rem;
    font-weight: 500;
    font-size: 0.875rem;
    cursor: pointer;
    transition: all 0.15s ease;
    border: 1px solid transparent;
}

.btn-outline {
    background: white;
    color: #374151;
    border-color: #d1d5db;
}

.btn-outline:hover {
    background: #f9fafb;
    border-color: #9ca3af;
}

/* Form Styles */
.form-layout-row {
    display: flex;
    gap: 1.5rem;
}

.half {
    flex: 1;
}

.bulk-action-bar {
    position: fixed;
    bottom: 2rem;
    left: 50%;
    transform: translateX(-50%);
    background: #1e293b;
    color: white;
    padding: 0.75rem 1.5rem;
    border-radius: 9999px;
    display: flex;
    align-items: center;
    gap: 1.5rem;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
    z-index: 100;
}

.bulk-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.bulk-count {
    background: #4f46e5;
    color: white;
    font-weight: 700;
    font-size: 0.75rem;
    width: 1.5rem;
    height: 1.5rem;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
}

.bulk-text {
    font-size: 0.875rem;
    font-weight: 500;
}

.bulk-actions {
    display: flex;
    gap: 0.75rem;
}

.bulk-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: white;
    padding: 0.375rem 1rem;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}

.bulk-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(255, 255, 255, 0.4);
}

.bulk-btn.danger:hover {
    background: #ef4444;
    border-color: #ef4444;
}

.form-input {
    width: 100%;
    padding: 0.625rem 0.875rem;
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    border-radius: 0.375rem;
    font-size: 0.875rem;
    transition: all 0.15s;
    background: rgb(var(--v-theme-surface));
    color: rgb(var(--v-theme-on-surface));
}

.form-input:focus {
    border-color: #4f46e5;
    outline: none;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.icon-spacer {
    margin-right: 0.5rem;
}


/* Tabs Styling */
.header-tabs {
    display: flex;
    gap: 0.25rem;
    background: rgba(var(--v-theme-on-surface), 0.05);
    padding: 0.25rem;
    border-radius: 0.5rem;
    margin: 0 1rem;
}

.tab-btn {
    padding: 0.375rem 1rem;
    border: none;
    background: transparent;
    border-radius: 0.375rem;
    font-size: 0.8125rem;
    font-weight: 600;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s;
}

.tab-btn:hover:not(.active) {
    color: #111827;
}

.tab-btn.active {
    background: white;
    color: #4f46e5;
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

/* Analytics Dashboard */
.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.summary-card {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 1.5rem;
    background: rgb(var(--v-theme-surface));
    border-radius: 1rem;
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    transition: transform 0.2s;
}

.summary-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.card-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 3rem;
    height: 3rem;
    border-radius: 0.75rem;
    font-size: 1.5rem;
}

.income .card-icon {
    background: #ecfdf5;
}

.expense .card-icon {
    background: #fef2f2;
}

.net .card-icon {
    background: #eff6ff;
}

.net.is-negative .card-icon {
    background: #fff7ed;
}

.card-label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.25rem;
}

.card-value {
    display: block;
    font-size: 1.5rem;
    font-weight: 700;
    color: #111827;
}

.income .card-value {
    color: #059669;
}

.expense .card-value {
    color: #dc2626;
}

.net.is-negative .card-value {
    color: #d97706;
}

.analytics-main-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.5rem;
}

.analytics-card {
    background: rgb(var(--v-theme-surface));
    padding: 1.5rem;
    border-radius: 1rem;
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
}

.card-title {
    font-size: 1rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
    margin-bottom: 1.5rem;
}

/* Category List */
.category-list {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

.category-info {
    display: flex;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}

.cat-name {
    font-size: 0.875rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface), 0.7);
}

.cat-value {
    font-size: 0.875rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
}

.progress-bar-bg {
    height: 0.5rem;
    background: rgba(var(--v-theme-on-surface), 0.05);
    border-radius: 9999px;
    overflow: hidden;
}

.progress-bar-fill {
    height: 100%;
    background: #4f46e5;
    border-radius: 9999px;
    transition: width 0.3s ease;
}

.type-bar {
    background: #8b5cf6;
}

/* Credit Utilization Box */
.credit-preview-box {
    background: rgba(var(--v-theme-on-surface), 0.02);
    padding: 1rem;
    border-radius: 0.75rem;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.credit-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.75rem;
}

.credit-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
}

.credit-val {
    font-size: 0.8125rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
}

.credit-bar-container {
    height: 0.5rem;
    background: rgba(var(--v-theme-on-surface), 0.1);
    border-radius: 999px;
    margin-bottom: 0.75rem;
    overflow: hidden;
}

.credit-bar-fill {
    height: 100%;
    border-radius: 999px;
    transition: width 0.3s ease;
}

.credit-bar-fill.safe {
    background: #10b981;
}

.credit-bar-fill.warning {
    background: #f59e0b;
}

.credit-bar-fill.danger {
    background: #ef4444;
}

.credit-footer {
    display: flex;
    justify-content: space-between;
    font-size: 0.75rem;
    color: #64748b;
}

.mt-6 {
    margin-top: 1.5rem;
}

.progress-bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #4f46e5, #818cf8);
    border-radius: 9999px;
    transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Trend Chart */
.trend-chart-container {
    height: 200px;
    display: flex;
    align-items: flex-end;
    padding-top: 1rem;
}

.trend-bars {
    display: flex;
    align-items: flex-end;
    gap: 0.5rem;
    width: 100%;
    height: 100%;
}

.trend-bar-wrapper {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
    height: 100%;
    justify-content: flex-end;
}

.trend-bar {
    width: 100%;
    background: rgba(var(--v-theme-primary), 0.2);
    border-radius: 0.25rem 0.25rem 0 0;
    min-height: 2px;
    transition: all 0.3s;
    cursor: help;
}

.trend-bar:hover {
    background: #4f46e5;
}

.trend-date {
    font-size: 0.65rem;
    color: #9ca3af;
    font-weight: 500;
}

.empty-small {
    padding: 3rem;
    text-align: center;
    color: #9ca3af;
    font-size: 0.875rem;
}

@media (max-width: 1024px) {
    .analytics-main-grid {
        grid-template-columns: 1fr;
    }
}

/* Merchant List */
.merchant-list {
    display: flex;
    flex-direction: column;
    gap: 0.875rem;
}

.merchant-item {
    display: flex;
    justify-content: space-between;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.merchant-item:last-child {
    border-bottom: none;
}

.m-name {
    font-size: 0.875rem;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface), 0.7);
}

.m-value {
    font-size: 0.875rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
}

/* Spending Insights */
.insights-content {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.insight-subtitle {
    font-size: 0.75rem;
    font-weight: 700;
    color: #6b7280;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 1rem;
}

.account-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.account-item {
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
}

.acc-info {
    display: flex;
    justify-content: space-between;
    font-size: 0.8125rem;
    font-weight: 500;
    color: #4b5563;
}

.mini-bar-bg {
    height: 4px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    border-radius: 2px;
}

.mini-bar-fill {
    height: 100%;
    background: #4f46e5;
    border-radius: 2px;
}

.insight-divider {
    height: 1px;
    background: rgba(var(--v-border-color), 0.1);
}

.pattern-bars {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
}

.pattern-label {
    display: flex;
    justify-content: space-between;
    font-size: 0.8125rem;
    font-weight: 600;
    margin-bottom: 0.5rem;
}

.pattern-bar-bg {
    height: 8px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    border-radius: 4px;
    overflow: hidden;
}

.pattern-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.8s ease;
}

.pattern-bar-fill.weekday {
    background: #4f46e5;
}

.pattern-bar-fill.weekend {
    background: #f59e0b;
}

/* Triage Area Styles */
.tab-badge {
    background: #ef4444;
    color: white;
    font-size: 0.7rem;
    padding: 0.1rem 0.4rem;
    border-radius: 999px;
    margin-left: 0.3rem;
    font-weight: 700;
}



/* --- Premium Triage Card Styling --- */
.triage-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
    gap: 1.5rem;
}

.triage-card {
    display: flex;
    flex-direction: column;
    padding: 0 !important;
    overflow: visible;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(12px);
    z-index: 1;
    /* Establish base level */
}

.triage-card:hover,
.triage-card:focus-within {
    z-index: 50;
    /* Rise above neighbors when interactive */
}

.triage-card:hover {
    transform: translateY(-6px) scale(1.01);
    box-shadow: 0 16px 32px rgba(0, 0, 0, 0.12), 0 4px 8px rgba(0, 0, 0, 0.04);
}

.triage-card.is-transfer-active {
    border-color: rgba(99, 102, 241, 0.3);
    background: linear-gradient(to bottom right, rgba(255, 255, 255, 0.95), rgba(238, 242, 255, 0.5));
}

.triage-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.25rem;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
    background: rgba(var(--v-theme-on-surface), 0.01);
    border-top-left-radius: 1.25rem;
    border-top-right-radius: 1.25rem;
}

.header-left {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.triage-date {
    font-size: 0.75rem;
    font-weight: 500;
    color: var(--color-text-muted);
}

.date-sep {
    opacity: 0.3;
    margin: 0 4px;
}

.triage-card-body {
    padding: 1.25rem;
    flex-grow: 1;
}

.triage-main-content {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    margin-bottom: 1.25rem;
}

.triage-amount-display {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-width: 110px;
    padding: 1rem;
    border-radius: 16px;
    position: relative;
}

.currency-symbol {
    font-size: 0.875rem;
    opacity: 0.6;
    margin-bottom: -4px;
}

.amount-val {
    font-size: 1.5rem;
    font-weight: 800;
    letter-spacing: -0.02em;
}

.amount-indicator {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-top: 4px;
}

/* Themes */
.debit-theme .triage-amount-display {
    background: rgba(239, 68, 68, 0.08);
    color: #dc2626;
}

.credit-theme .triage-amount-display {
    background: rgba(16, 185, 129, 0.08);
    color: #059669;
}

.triage-details-info {
    flex-grow: 1;
}

.triage-title {
    font-size: 1.125rem;
    font-weight: 700;
    margin-bottom: 0.35rem;
    color: rgb(var(--v-theme-on-surface));
}

.triage-account-info {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.875rem;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface), 0.6);
}

.acc-indicator {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: currentColor;
    opacity: 0.5;
}

.triage-meta-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 1.25rem;
}

.meta-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    border-radius: 100px;
    font-size: 0.75rem;
    font-weight: 500;
    color: rgb(var(--v-theme-on-surface), 0.7);
}

.meta-pill.highlight {
    background: rgba(99, 102, 241, 0.06);
    color: #4f46e5;
}

.triage-raw-box {
    padding: 0.75rem;
    background: rgba(var(--v-theme-on-surface), 0.02);
    border-radius: 10px;
    border: 1px dashed rgba(var(--v-border-color), 0.1);
}

.raw-label {
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    color: var(--color-text-muted);
    margin-bottom: 4px;
}

.raw-content-text {
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    color: rgb(var(--v-theme-on-surface), 0.6);
    line-height: 1.4;
    white-space: pre-wrap;
    word-break: break-all;
}

.triage-card-actions {
    padding: 1rem 1.25rem;
    background: rgba(var(--v-theme-on-surface), 0.015);
    border-top: 1px solid rgba(var(--v-border-color), 0.05);
    display: flex;
    flex-direction: column;
    gap: 1rem;
    border-bottom-left-radius: 1.25rem;
    border-bottom-right-radius: 1.25rem;
}

.action-top-row {
    display: flex;
    align-items: center;
}

.triage-input-group {
    display: flex;
    align-items: center;
    gap: 1rem;
    width: 100%;
}

.toggle-control {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    min-width: 140px;
}

.toggle-text {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
}

.select-container {
    flex-grow: 1;
}

.triage-select-premium {
    width: 100%;
}

.triage-select-premium :deep(.select-trigger) {
    background: rgb(var(--v-theme-surface));
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 12px;
    padding: 0.625rem 1rem;
    font-size: 0.875rem;
    font-weight: 500;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.triage-select-premium :deep(.select-trigger:focus-within) {
    border-color: #6366f1;
    box-shadow: 0 0 0 4px rgba(99, 102, 241, 0.15);
}

.action-bottom-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

/* Premium Buttons & Switches */
.btn-triage-primary {
    padding: 0.625rem 1.5rem;
    background: linear-gradient(135deg, #4f46e5 0%, #3730a3 100%);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 0.875rem;
    font-weight: 700;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: all 0.2s;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3);
}

.btn-triage-primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(79, 70, 229, 0.4);
}

.btn-triage-primary:active {
    transform: translateY(0);
}

.btn-shimmer {
    position: absolute;
    top: 0;
    left: -100%;
    width: 50%;
    height: 100%;
    background: linear-gradient(to right,
            rgba(255, 255, 255, 0) 0%,
            rgba(255, 255, 255, 0.2) 50%,
            rgba(255, 255, 255, 0) 100%);
    transform: skewX(-25deg);
    transition: none;
}

.btn-triage-primary:hover .btn-shimmer {
    animation: shimmer 1.5s infinite;
}

@keyframes shimmer {
    100% {
        left: 150%;
    }
}

.approval-cluster {
    display: flex;
    align-items: center;
    gap: 1.25rem;
}

.btn-triage-secondary {
    background: none;
    border: none;
    color: var(--color-text-muted);
    font-size: 0.875rem;
    font-weight: 600;
    cursor: pointer;
    transition: color 0.2s;
}

.btn-triage-secondary:hover {
    color: #dc2626;
}

.cache-checkbox {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
}

.cache-checkbox input {
    display: none;
}

.checkbox-box {
    width: 28px;
    height: 28px;
    border-radius: 8px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
}

.checkbox-text {
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-muted);
}

.cache-checkbox input:checked+.checkbox-box {
    background: #eef2ff;
    color: #4f46e5;
    transform: scale(1.1);
}

.checkbox-icon {
    font-size: 1rem;
    filter: grayscale(1);
    opacity: 0.5;
}

.cache-checkbox input:checked+.checkbox-box .checkbox-icon {
    filter: grayscale(0);
    opacity: 1;
}

/* Premium Slider */
.premium-switch {
    position: relative;
    display: inline-block;
    width: 40px;
    height: 22px;
}

.premium-switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.premium-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #e2e8f0;
    transition: .4s;
    border-radius: 34px;
}

.premium-slider:before {
    position: absolute;
    content: "";
    height: 16px;
    width: 16px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

input:checked+.premium-slider {
    background-color: #4f46e5;
}

input:checked+.premium-slider:before {
    transform: translateX(18px);
}

/* Badges */
.transfer-badge-mini {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: #ecfdf5;
    color: #059669;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 700;
    border: 1px solid rgba(5, 150, 105, 0.2);
}

.pulse {
    animation: pulse-animation 2s infinite;
}

@keyframes pulse-animation {
    0% {
        transform: scale(1);
        opacity: 1;
    }

    50% {
        transform: scale(1.05);
        opacity: 0.8;
    }

    100% {
        transform: scale(1);
        opacity: 1;
    }
}

/* Transfer Active State Decoration */
.is-transfer-active.triage-card {
    border: 1px solid rgba(16, 185, 129, 0.2);
    box-shadow: 0 0 0 1px rgba(16, 185, 129, 0.1);
}

.training-theme.triage-card {
    border-left: 4px solid #f59e0b;
}

.training-header {
    margin-bottom: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
}

.training-sender,
.training-subject {
    font-size: 0.8rem;
    color: var(--color-text-primary);
    font-weight: 500;
}

.training-sender .label,
.training-subject .label {
    color: var(--color-text-muted);
    font-weight: 600;
    margin-right: 4px;
}

.training-raw-preview-premium {
    background: #1e293b;
    color: #e2e8f0;
    padding: 1rem;
    border-radius: 12px;
    font-size: 0.75rem;
    font-family: 'JetBrains Mono', monospace;
    max-height: 120px;
    overflow-y: auto;
    border: 1px solid rgba(255, 255, 255, 0.1);
    line-height: 1.5;
}

.empty-state-triage {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 5rem 2rem;
    text-align: center;
}

.empty-glow-icon {
    font-size: 3rem;
    margin-bottom: 1rem;
    text-shadow: 0 0 20px rgba(16, 185, 129, 0.4);
}

.alert-info-glass {
    display: flex;
    gap: 0.75rem;
    padding: 1rem;
    background: rgba(59, 130, 246, 0.05);
    border: 1px solid rgba(59, 130, 246, 0.1);
    border-radius: 12px;
    align-items: center;
}

.alert-icon {
    font-size: 1.25rem;
}

.alert-text {
    font-size: 0.875rem;
    color: #1e40af;
}

.ref-id-pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    background: #eef2ff;
    /* Light Indigo */
    border: 1px solid #c7d2fe;
    border-radius: 100px;
    font-size: 10px;
    font-family: inherit;
    color: var(--color-text-muted);
    letter-spacing: 0.02em;
    font-weight: 500;
}

.ref-id-pill.small {
    padding: 1px 6px;
    font-size: 9px;
}

.ref-icon {
    font-size: 10px;
    filter: grayscale(1) opacity(0.7);
}

.ai-badge-mini {
    display: inline-flex;
    align-items: center;
    gap: 2px;
    background: #eef2ff;
    color: #4f46e5;
    padding: 0px 6px;
    border-radius: 4px;
    font-size: 0.65rem;
    font-weight: 700;
    text-transform: uppercase;
    border: 1px solid rgba(79, 70, 229, 0.2);
    cursor: help;
}

/* --- Transfer & Toggle Logic CSS --- */
.approval-form {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.transfer-manual-toggle {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
}

.toggle-label {
    font-size: 0.75rem;
    color: var(--color-text-muted);
}

.rule-toggle {
    display: flex;
    align-items: center;
    cursor: pointer;
}

.rule-toggle input {
    display: none;
}

.rule-toggle label {
    cursor: pointer;
    font-size: 1rem;
    opacity: 0.3;
    transition: all 0.2s;
}

.rule-toggle input:checked+label {
    opacity: 1;
    transform: scale(1.2);
}

/* Switch UI */
.switch {
    position: relative;
    display: inline-block;
    width: 28px;
    height: 16px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #cbd5e1;
    -webkit-transition: .4s;
    transition: .4s;
}

.slider:before {
    position: absolute;
    content: "";
    height: 12px;
    width: 12px;
    left: 2px;
    bottom: 2px;
    background-color: white;
    -webkit-transition: .4s;
    transition: .4s;
}

input:checked+.slider {
    background-color: var(--brand-primary, #6366f1);
}

input:focus+.slider {
    box-shadow: 0 0 1px var(--brand-primary, #6366f1);
}

input:checked+.slider:before {
    -webkit-transform: translateX(12px);
    -ms-transform: translateX(12px);
    transform: translateX(12px);
}

.slider.round {
    border-radius: 34px;
}

.slider.round:before {
    border-radius: 50%;
}

.amount-cell.is-transfer {
    color: #64748b;
    /* Slate 500 */
    background: #f1f5f9;
    font-style: italic;
}

.triage-card.selected {
    border: 1px solid var(--brand-primary, #6366f1);
    background: rgba(99, 102, 241, 0.05);
}

.triage-filter-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1.5rem;
    background: white;
    padding: 0.75rem 1rem;
    border-radius: 1rem;
    border: 1px solid #e5e7eb;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.triage-search-box {
    position: relative;
    flex: 1;
    max-width: 400px;
}

.search-icon-mini {
    position: absolute;
    left: 0.875rem;
    top: 50%;
    transform: translateY(-50%);
    opacity: 0.4;
    font-size: 0.875rem;
}

.triage-search-input-premium {
    width: 100%;
    padding: 0.625rem 0.625rem 0.625rem 2.25rem;
    border: 1px solid #f3f4f6;
    background: #f9fafb;
    border-radius: 0.75rem;
    font-size: 0.8125rem;
    outline: none;
    transition: all 0.2s;
}

.triage-search-input-premium:focus {
    background: white;
    border-color: #4f46e5;
    box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}

.source-toggle-group {
    display: flex;
    gap: 0.25rem;
    background: #f3f4f6;
    padding: 0.25rem;
    border-radius: 0.625rem;
}

.source-chip {
    padding: 0.375rem 0.875rem;
    border: none;
    background: transparent;
    border-radius: 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    cursor: pointer;
    transition: all 0.2s;
}

.source-chip:hover:not(.active) {
    color: #111827;
}

.source-chip.active {
    background: white;
    color: #4f46e5;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}
</style>
