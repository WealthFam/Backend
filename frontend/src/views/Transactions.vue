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
                                <v-tab value="pending" class="premium-tab" rounded="xl" @click="fetchTriage">
                                    <div class="d-flex align-center gap-2">
                                        <Inbox :size="16" />
                                        <span>Inbox</span>
                                        <v-chip v-if="triagePagination.total > 0" size="x-small" color="primary"
                                            class="ml-1 font-weight-black">
                                            {{ triagePagination.total }}
                                        </v-chip>
                                    </div>
                                </v-tab>
                                <v-tab value="training" class="premium-tab" rounded="xl" @click="fetchTriage">
                                    <div class="d-flex align-center gap-2">
                                        <Target :size="16" />
                                        <span>Training</span>
                                        <v-chip v-if="trainingPagination.total > 0" size="x-small" color="primary"
                                            class="ml-1 font-weight-black">
                                            {{ trainingPagination.total }}
                                        </v-chip>
                                    </div>
                                </v-tab>
                                <v-tab value="heatmap" class="premium-tab" rounded="xl">
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
                        <!-- QUICK CHART ROW -->
                        <v-card v-if="forecastData && forecastData.trend.length > 0"
                            class="glass-card mb-6 overflow-hidden" rounded="xl">
                            <div class="pa-5 pb-0">
                                <div class="d-flex align-center justify-space-between">
                                    <h3 class="text-subtitle-1 font-weight-black d-flex align-center gap-2">
                                        <Activity :size="20" class="text-primary" />
                                        Spending Velocity & Forecast
                                    </h3>
                                    <div
                                        class="text-tiny font-weight-black bg-primary-lighten-5 px-3 py-1 rounded-pill text-primary">
                                        AVG ₹{{ Math.round(metrics.avg_daily_spending || 0) }}/DAY
                                    </div>
                                </div>
                            </div>

                            <div v-if="forecastData" ref="chartContainer" class="py-8"
                                style="height: 180px; width: 100%;">
                                <SpendingForecastChart :trend="forecastData.trend" :user-names="forecastData.user_names"
                                    :height="120" :width="chartWidth" />
                            </div>
                        </v-card>

                        <TransactionList v-bind="{
                            transactions, accounts, categories, expenseGroups,
                            loading, total, selectedAccount, categoryFilter,
                            searchQuery, startDate, endDate, selectedTimeRange,
                            page, pageSize, txnSortKey, txnSortOrder, metrics,
                            dailyTrend: forecastData?.trend
                        }" v-model:selectedIds="selectedIds"
                            @update:selectedAccount="selectedAccount = $event; page = 1; fetchData()"
                            @update:categoryFilter="categoryFilter = $event; page = 1; fetchData()"
                            @update:searchQuery="searchQuery = $event"
                            @update:startDate="startDate = $event; page = 1; fetchData()"
                            @update:endDate="endDate = $event; page = 1; fetchData()"
                            @update:selectedTimeRange="selectedTimeRange = $event; handleTimeRangeChange($event)"
                            @update:page="page = $event; fetchData()"
                            @update:pageSize="pageSize = $event; page = 1; fetchData()" @sortChange="toggleTxnSort"
                            @editTxn="(t) => { fetchModalData(); openEditModal(t) }"
                            @deleteSelected="showDeleteConfirm = true" @importCsv="showImportModal = true"
                            @fetchData="fetchData" @showVendorInsights="openVendorInsights"
                            @resetFilters="selectedTimeRange = 'all'; startDate = ''; endDate = ''; searchQuery = ''; categoryFilter = ''; fetchData()" />
                    </v-window-item>

                    <v-window-item value="pending">
                        <TransactionTriage v-bind="{
                            activeSubTab: 'pending', accounts, categories,
                            triageTransactions, triagePagination, triageSearchQuery,
                            triageSourceFilter, triageSortKey, triageSortOrder,
                            unparsedMessages, trainingPagination, trainingSearchQuery,
                            trainingSortKey, trainingSortOrder,
                            // Confirmation States
                            showDiscardConfirm, showTrainingDiscardConfirm, createIgnoreRule,
                            triageIdToDiscard, trainingIdToDiscard,
                            showLabelForm, selectedMessage, labelForm
                        }" v-model:selectedTriageIds="selectedTriageIds"
                            v-model:selectedTrainingIds="selectedTrainingIds"
                            @update:activeSubTab="activeTriageSubTab = $event"
                            @update:triageSearchQuery="triageSearchQuery = $event"
                            @update:triageSourceFilter="triageSourceFilter = $event as any"
                            @update:triageSortKey="triageSortKey = $event"
                            @update:triageSortOrder="triageSortOrder = $event"
                            @update:triagePagination="triagePagination = $event; fetchTriage()"
                            @update:trainingSearchQuery="trainingSearchQuery = $event"
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
                            @refreshTriage="() => { fetchTriage(); fetchData(); }"
                            @update:showLabelForm="showLabelForm = $event" @handleLabelSubmit="handleLabelSubmit"
                            :training-sender-filter="trainingSenderFilter" :training-subject-filter="trainingSubjectFilter"
                            :spam-filters="spamFilters" :show-spam-manager="showSpamManager"
                            @update:trainingSenderFilter="trainingSenderFilter = $event"
                            @update:trainingSubjectFilter="trainingSubjectFilter = $event"
                            @update:showSpamManager="showSpamManager = $event"
                            @markAsSpam="markAsSpam" @findSimilar="findSimilar"
                            @removeSpamFilter="removeSpamFilter" @fetchSpamFilters="fetchSpamFilters" />
                    </v-window-item>

                    <v-window-item value="training">
                        <TransactionTriage v-bind="{
                            activeSubTab: 'training', accounts, categories,
                            triageTransactions, triagePagination, triageSearchQuery,
                            triageSourceFilter, triageSortKey, triageSortOrder,
                            unparsedMessages, trainingPagination, trainingSearchQuery,
                            trainingSortKey, trainingSortOrder,
                            // Confirmation States
                            showDiscardConfirm, showTrainingDiscardConfirm, createIgnoreRule,
                            triageIdToDiscard, trainingIdToDiscard,
                            showLabelForm, selectedMessage, labelForm
                        }" v-model:selectedTriageIds="selectedTriageIds"
                            v-model:selectedTrainingIds="selectedTrainingIds"
                            @update:activeSubTab="activeTriageSubTab = $event"
                            @update:triageSearchQuery="triageSearchQuery = $event"
                            @update:triageSourceFilter="triageSourceFilter = $event as any"
                            @update:triageSortKey="triageSortKey = $event"
                            @update:triageSortOrder="triageSortOrder = $event"
                            @update:triagePagination="triagePagination = $event; fetchTriage()"
                            @update:trainingSearchQuery="trainingSearchQuery = $event"
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
                            @refreshTriage="() => { fetchTriage(); fetchData(); }"
                            @update:showLabelForm="showLabelForm = $event" @handleLabelSubmit="handleLabelSubmit"
                            :training-sender-filter="trainingSenderFilter" :training-subject-filter="trainingSubjectFilter"
                            :spam-filters="spamFilters" :show-spam-manager="showSpamManager"
                            @update:trainingSenderFilter="trainingSenderFilter = $event"
                            @update:trainingSubjectFilter="trainingSubjectFilter = $event"
                            @update:showSpamManager="showSpamManager = $event"
                            @markAsSpam="markAsSpam" @findSimilar="findSimilar"
                            @removeSpamFilter="removeSpamFilter" @fetchSpamFilters="fetchSpamFilters" />
                    </v-window-item>

                    <v-window-item value="heatmap">
                        <div class="content-card pa-6 glass-card">
                            <SpendingHeatmap :start-date="startDate" :end-date="endDate" />
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

        <VendorInsightsModal v-model="showVendorModal" :vendor-name="selectedVendorForInsights" />




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

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { useRoute } from 'vue-router'

import ImportModal from '@/components/ImportModal.vue'
import SmartPromptModal from '@/components/SmartPromptModal.vue'

import SpendingHeatmap from '@/components/SpendingHeatmap.vue'
import TransactionList from './transactions/TransactionList.vue'
import TransactionTriage from './transactions/TransactionTriage.vue'
import TransactionModal from './transactions/TransactionModal.vue'
import VendorInsightsModal from '@/components/transactions/VendorInsightsModal.vue'
import {
    LayoutList,
    Inbox,
    Map as MapIcon,
    Activity,
    Target
} from 'lucide-vue-next'
import SpendingForecastChart from '@/components/SpendingForecastChart.vue'


// Composables

import { useTransactionState } from '@/composables/useTransactionState'
import { useTriageState } from '@/composables/useTriageState'
import { useTransactionModals } from '@/composables/useTransactionModals'
import { useAuthStore } from '@/stores/auth'
import { useFinanceStore } from '@/stores/finance'
import { useBudgetStore } from '@/stores/finance/budgets'
import { useExpenseGroupStore } from '@/stores/expenseGroups'

// Global State
const route = useRoute()
const financeStore = useFinanceStore()
const budgetStore = useBudgetStore()
const groupStore = useExpenseGroupStore()

// Master Data (shared across composables, backed by stores)
const accounts = computed(() => financeStore.accounts)
const categories = computed(() => financeStore.categories)
const budgets = computed(() => budgetStore.budgets)
const expenseGroups = computed(() => groupStore.groups)

// UI State
const showImportModal = ref(false)
const activeTab = ref<'list' | 'analytics' | 'pending' | 'training' | 'heatmap'>('list')
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

const showVendorModal = ref(false)
const selectedVendorForInsights = ref('')

function openVendorInsights(name: string) {
    selectedVendorForInsights.value = name
    showVendorModal.value = true
}



// Initialize Transaction State Composable
const {
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

    page,
    pageSize,
    txnSortKey,
    txnSortOrder,
    selectedIds,
    showDeleteConfirm,
    fetchData,
    fetchModalData, // [NEW] Lazy load budgets/loans
    handleTimeRangeChange,
    toggleTxnSort,
    refreshAccounts,
    confirmDelete
} = useTransactionState(route, accounts)

// Chart Responsiveness
const chartContainer = ref<HTMLElement | null>(null)
const chartWidth = ref(1200)

watch(chartContainer, (el) => {
    if (el) {
        chartWidth.value = el.clientWidth
        const observer = new ResizeObserver((entries) => {
            if (entries[0]) {
                chartWidth.value = entries[0].contentRect.width
            }
        })
        observer.observe(el)
    }
})

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
    trainingSearchQuery,
    trainingSortKey,
    trainingSortOrder,
    trainingSenderFilter,
    trainingSubjectFilter,
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
    // Spam
    spamFilters,
    showSpamManager,
    markAsSpam,
    fetchSpamFilters,
    removeSpamFilter,
    findSimilar,
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
} = useTransactionModals(selectedAccount, accounts, budgets, transactions, fetchData, showSmartPrompt,
    smartPromptData, refreshAccounts)


// Search debounce
let searchDebounce: ReturnType<typeof setTimeout> | null = null
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
    // Reset page and re-fetch. Stores handle their own member-specific caching/resets.
    page.value = 1
    fetchData()
    fetchTriage()
})

onMounted(() => {
    fetchData()
    fetchTriage() // Pre-fetch count
})
</script>

<style scoped>
.dashboard-page {
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
</style>
