<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import VendorAliasModal from '@/components/VendorAliasModal.vue'
import { useCurrency } from '@/composables/useCurrency'
// Props
const props = defineProps<{
    activeSubTab: 'pending' | 'training'
    accounts: any[]
    categories: any[]
    triageTransactions: any[]
    triagePagination: { total: number; limit: number; skip: number }
    triageSearchQuery: string
    triageSourceFilter: string
    triageSortKey: string
    triageSortOrder: 'asc' | 'desc'
    unparsedMessages: any[]
    trainingPagination: { total: number; limit: number; skip: number }
    trainingSortKey: string
    trainingSortOrder: 'asc' | 'desc'
    // Confirmation States
    showDiscardConfirm: boolean
    showTrainingDiscardConfirm: boolean
    createIgnoreRule: boolean
    triageIdToDiscard: string | null
    trainingIdToDiscard: string | null
}>()

// Emits
const emit = defineEmits<{
    'update:activeSubTab': [value: 'pending' | 'training']
    'update:triageSearchQuery': [value: string]
    'update:triageSourceFilter': [value: string]
    'update:triageSortKey': [value: string]
    'update:triageSortOrder': [value: 'asc' | 'desc']
    'update:triagePagination': [value: { total: number; limit: number; skip: number }]
    'update:trainingSortKey': [value: string]
    'update:trainingSortOrder': [value: 'asc' | 'desc']
    'update:trainingPagination': [value: { total: number; limit: number; skip: number }]
    'approveTriage': [txn: any]
    'rejectTriage': [id: string]
    'bulkRejectTriage': []
    'startLabeling': [msg: any]
    'dismissTraining': [id: string]
    'bulkDismissTraining': []
    'refreshTriage': []
    'update:showDiscardConfirm': [value: boolean]
    'update:showTrainingDiscardConfirm': [value: boolean]
    'update:createIgnoreRule': [value: boolean]
    'confirmDiscard': []
    'confirmTrainingDiscard': []
    'confirmBulkDiscard': []
    'confirmBulkTrainingDiscard': []
}>()

// Local State
const selectedTriageIds = defineModel<string[]>('selectedTriageIds', { default: [] })
const selectedTrainingIds = defineModel<string[]>('selectedTrainingIds', { default: [] })
// Computed Interface for Tabs
const activeTab = computed({
    get: () => props.activeSubTab,
    set: (val) => emit('update:activeSubTab', val)
})

const accountOptions = computed(() => {
    return props.accounts.map(a => ({ title: a.name, value: a.id }))
})

const categoryOptions = computed(() => {
    const list: any[] = []
    const flatten = (cats: any[], depth = 0) => {
        cats.forEach(c => {
            const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
            list.push({
                title: `${prefix}${c.icon || '🏷️'} ${c.name}`,
                value: c.name
            })
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories, depth + 1)
            }
        })
    }
    flatten(props.categories)
    if (!list.find(o => o.value === 'Uncategorized')) {
        list.push({ title: '🏷️ Uncategorized', value: 'Uncategorized' })
    }
    return list
})

const filteredTriageTransactions = computed(() => {
    let filtered = props.triageTransactions

    if (props.triageSearchQuery) {
        const q = props.triageSearchQuery.toLowerCase()
        filtered = filtered.filter(t =>
            (t.recipient && t.recipient.toLowerCase().includes(q)) ||
            (t.description && t.description.toLowerCase().includes(q)) ||
            (t.external_id && t.external_id.toLowerCase().includes(q)) ||
            (t.amount && String(t.amount).includes(q))
        )
    }

    if (props.triageSourceFilter && props.triageSourceFilter !== 'ALL') {
        filtered = filtered.filter(t => t.source === props.triageSourceFilter)
    }

    return filtered
})

const triageCurrentPage = computed({
    get: () => Math.floor(props.triagePagination.skip / props.triagePagination.limit) + 1,
    set: (val) => emit('update:triagePagination', { ...props.triagePagination, skip: (val - 1) * props.triagePagination.limit })
})

const trainingCurrentPage = computed({
    get: () => Math.floor(props.trainingPagination.skip / props.trainingPagination.limit) + 1,
    set: (val) => emit('update:trainingPagination', { ...props.trainingPagination, skip: (val - 1) * props.trainingPagination.limit })
})

const sortedTrainingMessages = computed(() => {
    let messages = [...props.unparsedMessages]
    const key = props.trainingSortKey as any
    messages.sort((a, b) => {
        const valA = a[key]
        const valB = b[key]
        if (valA < valB) return props.trainingSortOrder === 'asc' ? -1 : 1
        if (valA > valB) return props.trainingSortOrder === 'asc' ? 1 : -1
        return 0
    })
    return messages
})

// Methods
function getAccountName(id: string) {
    const acc = props.accounts.find(a => a.id === id)
    return acc ? acc.name : 'Unknown Account'
}

function formatDate(dateStr: string) {
    if (!dateStr) return { day: 'N/A', meta: '' }

    const d = new Date(dateStr)
    if (isNaN(d.getTime())) {
        return { day: '?', meta: dateStr.split('T')[0] || dateStr }
    }

    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

    if (d.toDateString() === today.toDateString()) {
        return { day: 'Today', meta: time }
    }
    if (d.toDateString() === yesterday.toDateString()) {
        return { day: 'Yesterday', meta: time }
    }

    const currentYear = today.getFullYear()
    const txnYear = d.getFullYear()

    let formatOptions: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
    if (txnYear !== currentYear) {
        formatOptions.year = 'numeric'
    }

    const monthDay = d.toLocaleDateString('en-US', formatOptions)
    return {
        day: monthDay,
        meta: time
    }
}

function toggleSelectAllTriage() {
    if (selectedTriageIds.value.length === filteredTriageTransactions.value.length && filteredTriageTransactions.value.length > 0) {
        selectedTriageIds.value = []
    } else {
        selectedTriageIds.value = filteredTriageTransactions.value.map(t => t.id)
    }
}

function toggleSelectAllTraining() {
    if (selectedTrainingIds.value.length === props.unparsedMessages.length && props.unparsedMessages.length > 0) {
        selectedTrainingIds.value = []
    } else {
        selectedTrainingIds.value = props.unparsedMessages.map(m => m.id)
    }
}



function handleTriagePaginationLimitChange(newLimit: number) {
    emit('update:triagePagination', { ...props.triagePagination, limit: newLimit, skip: 0 })
}

function handleTrainingPaginationLimitChange(newLimit: number) {
    emit('update:trainingPagination', { ...props.trainingPagination, limit: newLimit, skip: 0 })
}

const showAliasModal = ref(false)
const aliasForm = reactive({
    pattern: '',
    alias: '',
    update_past: false
})

function openAliasModal(txn: any) {
    aliasForm.pattern = txn.description || txn.recipient || ''
    aliasForm.alias = txn.recipient || ''
    showAliasModal.value = true
}

// --- Triage Details Modal ---
const triageDetailsDialog = ref(false)
const selectedTriageTxn = ref<any>(null)

function openTriageDetails(txn: any) {
    selectedTriageTxn.value = JSON.parse(JSON.stringify(txn)) // Deep copy
    triageDetailsDialog.value = true
}

function saveTriageDetails() {
    if (!selectedTriageTxn.value) return
    // Find the original transaction in the list and update it
    const index = props.triageTransactions.findIndex(t => t.id === selectedTriageTxn.value.id)
    if (index !== -1) {
        // Since we shouldn't mutate props directly, we rely on the fact that 
        // the parent state is likely being updated or we can emit an update if necessary.
        // However, in this specific triage view, 'approveTriage' is the main action.
        // We can update the local reactive reference if one existed, but here we'll just
        // let the user close and confirm.
        // If we want the edit to persist on the card BEFORE confirm:
        Object.assign(props.triageTransactions[index], selectedTriageTxn.value)
    }
    triageDetailsDialog.value = false
}

const { formatAmount } = useCurrency()
</script>

<template>
    <div class="triage-view animate-in">
        <!-- Vuetify Tabs -->
        <v-tabs v-model="activeTab" color="primary" align-tabs="start" class="mb-6 rounded-lg bg-surface-light">
            <v-tooltip text="Review and categorize auto-detected transactions" location="bottom" open-delay="400">
                <template v-slot:activator="{ props }">
                    <v-tab v-bind="props" value="pending">
                        <v-icon start icon="Inbox" class="mr-2"></v-icon>
                        Pending Inbox
                        <v-chip size="x-small" color="primary" class="ml-2" variant="flat">
                            {{ triagePagination.total }}
                        </v-chip>
                    </v-tab>
                </template>
            </v-tooltip>
            <v-tooltip text="Label unparsed messages to train the detection engine" location="bottom" open-delay="400">
                <template v-slot:activator="{ props }">
                    <v-tab v-bind="props" value="training">
                        <v-icon start icon="Bot" class="mr-2"></v-icon>
                        Training Area
                        <v-chip size="x-small" color="warning" class="ml-2" variant="flat">
                            {{ trainingPagination.total }}
                        </v-chip>
                    </v-tab>
                </template>
            </v-tooltip>
        </v-tabs>

        <v-window v-model="activeTab">
            <!-- PENDING TAB -->
            <v-window-item value="pending">
                <v-alert icon="ShieldAlert" type="info" variant="tonal" class="mb-1" border="start" density="compact">
                    <strong>Review Intake</strong>: These transactions were auto-detected but require
                    categorization or confirmation before affecting your balance.
                </v-alert>

                <!-- Filters Toolbar -->
                <v-card class="premium-glass-card mb-4 pa-3 no-hover" style="border-radius: 20px !important;">
                    <v-row align="center" no-gutters class="gap-3 px-0">
                        <v-col cols="12" lg="auto" class="flex-grow-1">
                            <v-text-field :model-value="triageSearchQuery"
                                @update:model-value="emit('update:triageSearchQuery', $event)"
                                placeholder="Search description or recipient..." density="compact" hide-details
                                variant="solo" rounded="lg" prepend-inner-icon="Search" class="search-input-premium"
                                clearable autocomplete="off" />
                        </v-col>

                        <v-divider vertical class="d-none d-lg-block mx-1" />

                        <v-col cols="auto">
                            <v-btn-toggle :model-value="triageSourceFilter"
                                @update:model-value="emit('update:triageSourceFilter', $event || 'ALL')"
                                density="compact" color="primary" variant="tonal" divided mandatory
                                class="rounded-lg border-thin">
                                <v-btn value="ALL" size="small" class="px-4">All</v-btn>
                                <v-btn value="SMS" size="small" class="px-4">SMS</v-btn>
                                <v-btn value="EMAIL" size="small" class="px-4">Email</v-btn>
                            </v-btn-toggle>
                        </v-col>

                        <v-divider vertical class="d-none d-lg-block mx-1" />

                        <v-col cols="12" md="auto" class="d-flex align-center gap-2">
                            <v-select :model-value="triageSortKey"
                                @update:model-value="emit('update:triageSortKey', $event)"
                                :items="[{ title: 'Date', value: 'date' }, { title: 'Amount', value: 'amount' }, { title: 'Description', value: 'description' }]"
                                item-title="title" item-value="value" hide-details density="compact" variant="solo"
                                label="Sort" style="width: 140px" rounded="lg" class="filter-field-premium"></v-select>

                            <v-tooltip :text="`Sort by ${triageSortOrder === 'asc' ? 'Descending' : 'Ascending'}`"
                                location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props"
                                        @click="emit('update:triageSortOrder', triageSortOrder === 'asc' ? 'desc' : 'asc')"
                                        variant="tonal" size="small" height="40" width="40" color="primary"
                                        class="rounded-lg" :icon="triageSortOrder === 'asc' ? 'ArrowUp' : 'ArrowDown'">
                                    </v-btn>
                                </template>
                            </v-tooltip>
                        </v-col>
                    </v-row>
                </v-card>

                <!-- Bulk Actions -->
                <div class="d-flex align-center justify-space-between mb-4 px-2">
                    <div class="d-flex align-center gap-4">
                        <v-checkbox-btn
                            :model-value="selectedTriageIds.length === filteredTriageTransactions.length && filteredTriageTransactions.length > 0"
                            @update:model-value="toggleSelectAllTriage" color="primary" label="Select All Filtered"
                            hide-details density="compact" class="ml-1"></v-checkbox-btn>

                        <v-fade-transition>
                            <v-tooltip v-if="selectedTriageIds.length > 0"
                                :text="`Discard ${selectedTriageIds.length} selected transactions`" location="top"
                                open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props" color="error" variant="tonal" size="small"
                                        prepend-icon="Trash2" @click="emit('update:showDiscardConfirm', true)"
                                        rounded="lg">
                                        Discard {{ selectedTriageIds.length }}
                                    </v-btn>
                                </template>
                            </v-tooltip>
                        </v-fade-transition>
                    </div>
                    <v-tooltip text="Refresh triage data" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" icon="RotateCw" variant="text" size="small"
                                @click="emit('refreshTriage')"></v-btn>
                        </template>
                    </v-tooltip>
                </div>

                <!-- Transactions Grid -->
                <v-row>
                    <v-col v-for="txn in filteredTriageTransactions" :key="txn.id" cols="12" md="6" lg="4">
                        <v-card class="premium-glass-card"
                            :class="{ 'is-selected': selectedTriageIds.includes(txn.id), 'is-debit': txn.amount < 0, 'is-credit': txn.amount >= 0 }">

                            <!-- Dynamic Accent Glow -->
                            <div class="card-glow-accent"></div>

                            <div class="card-modern-header px-4 pt-4 pb-2">
                                <div class="d-flex align-left gap-3 overflow-hidden">
                                    <v-checkbox-btn v-model="selectedTriageIds" :value="txn.id" color="primary"
                                        density="compact" hide-details class="mt-n1"></v-checkbox-btn>

                                    <div class="flex-grow-1 min-width-0">
                                        <div class="text-subtitle-2 font-weight-black text-truncate modern-header-title mb-0"
                                            :title="txn.recipient || txn.description">
                                            {{ txn.recipient || txn.description }}
                                        </div>
                                        <div class="text-caption opacity-60 font-weight-bold text-truncate">
                                            {{ formatDate(txn.date).day }} • {{ txn.source }}
                                        </div>
                                    </div>

                                </div>
                            </div>

                            <!-- Amount Hero Section -->
                            <div class="amount-hero-section px-4 py-4 d-flex align-center justify-center">
                                <div class="text-center">
                                    <div class="modern-amount-display amount-hero-text"
                                        :class="txn.amount < 0 ? 'text-error' : 'text-success'">
                                        {{ formatAmount(Math.abs(txn.amount)) }}
                                    </div>
                                    <div
                                        class="text-caption font-weight-black opacity-40 text-uppercase tracking-widest mt-n1">
                                        {{ txn.amount < 0 ? 'Debit' : 'Credit' }} </div>
                                    </div>
                                </div>

                                <!-- Card Body -->
                                <v-card-text class="flex-grow-1 px-4 py-2 d-flex flex-column gap-3">
                                    <div class="modern-metadata">
                                        <div
                                            class="d-flex align-center gap-2 text-caption font-weight-bold opacity-60 mb-2">
                                            <v-icon size="14">Landmark</v-icon>
                                            {{ getAccountName(txn.account_id) }}
                                        </div>

                                        <div v-if="txn.raw_message" class="modern-message-container pa-3">
                                            <div class="text-caption message-content">
                                                {{ txn.raw_message }}
                                            </div>
                                        </div>
                                    </div>

                                    <div class="d-flex align-center gap-2 mt-auto">
                                        <v-tooltip text="Mark as a transfer between your own accounts" location="top"
                                            open-delay="400">
                                            <template v-slot:activator="{ props }">
                                                <v-btn-toggle v-bind="props" :model-value="txn.is_transfer"
                                                    density="compact" variant="flat"
                                                    class="tactile-toggle-group transfer-toggle"
                                                    @update:model-value="txn.is_transfer = !!$event; if ($event) txn.exclude_from_reports = true">
                                                    <v-btn :value="true" size="x-small"
                                                        class="text-none px-3 rounded-pill"
                                                        :color="txn.is_transfer ? 'blue-darken-1' : ''"
                                                        prepend-icon="ArrowLeftRight">
                                                        Transfer
                                                    </v-btn>
                                                </v-btn-toggle>
                                            </template>
                                        </v-tooltip>

                                        <v-tooltip text="Exclude this transaction from your budget and reports"
                                            location="top" open-delay="400">
                                            <template v-slot:activator="{ props }">
                                                <v-btn-toggle v-bind="props" :model-value="txn.exclude_from_reports"
                                                    density="compact" variant="flat"
                                                    class="tactile-toggle-group hide-toggle"
                                                    @update:model-value="txn.exclude_from_reports = !!$event">
                                                    <v-btn :value="true" size="x-small"
                                                        class="text-none px-3 rounded-pill"
                                                        :color="txn.exclude_from_reports ? 'grey-darken-2' : ''"
                                                        prepend-icon="EyeOff">
                                                        Hide
                                                    </v-btn>
                                                </v-btn-toggle>
                                            </template>
                                        </v-tooltip>
                                    </div>

                                    <div class="modern-category-select pt-1">
                                        <div class="d-flex align-center gap-2">
                                            <span class="text-caption font-weight-black opacity-60 flex-shrink-0"
                                                style="width: 70px">Category</span>
                                            <v-autocomplete v-model="txn.category" :items="categoryOptions"
                                                item-title="title" item-value="value" placeholder="Select Category"
                                                variant="solo-filled" density="compact" rounded="lg" hide-details
                                                prepend-inner-icon="Tag" class="flex-grow-1"></v-autocomplete>
                                        </div>
                                    </div>

                                    <!-- Target Account (Conditional) -->
                                    <v-expand-transition>
                                        <div v-if="txn.is_transfer" class="modern-transfer-select pt-1">
                                            <div class="d-flex align-center gap-2">
                                                <span class="text-caption font-weight-black opacity-60 flex-shrink-0"
                                                    style="width: 70px">To</span>
                                                <v-select v-model="txn.to_account_id"
                                                    :items="accountOptions.filter(a => a.value !== txn.account_id)"
                                                    item-title="title" item-value="value" placeholder="Target Account"
                                                    variant="solo-filled" density="compact" rounded="lg" hide-details
                                                    class="flex-grow-1"></v-select>
                                            </div>
                                        </div>
                                    </v-expand-transition>
                                </v-card-text>

                                <!-- Tooling Footer -->
                                <div class="modern-card-footer px-3 py-2 d-flex align-center gap-1 border-t">
                                    <v-tooltip text="Discard this transaction" location="top" open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="error"
                                                @click="emit('rejectTriage', txn.id)"
                                                class="rounded-lg footer-action-btn">
                                                <v-icon size="16">Trash2</v-icon>
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-tooltip text="Map this vendor to an alias for better categorization"
                                        location="top" open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="primary"
                                                @click="openAliasModal(txn)" class="rounded-lg footer-action-btn">
                                                <v-icon size="16">MapPin</v-icon>
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-tooltip text="View full transaction details and raw message" location="top"
                                        open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" variant="tonal" size="small" color="secondary"
                                                @click="openTriageDetails(txn)" class="rounded-lg footer-action-btn">
                                                <v-icon size="16">Info</v-icon>
                                            </v-btn>
                                        </template>
                                    </v-tooltip>

                                    <v-spacer></v-spacer>

                                    <v-tooltip text="Approve and confirm this transaction" location="top"
                                        open-delay="400">
                                        <template v-slot:activator="{ props }">
                                            <v-btn v-bind="props" color="primary" variant="tonal" size="small"
                                                class="rounded-lg footer-action-btn"
                                                :disabled="!txn.category || txn.category === 'Uncategorized'"
                                                @click="emit('approveTriage', txn)">
                                                <v-icon size="16">Check</v-icon>
                                            </v-btn>
                                        </template>
                                    </v-tooltip>
                                </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="triagePagination.total === 0" class="text-center py-12">
                    <v-icon size="64" color="success" class="mb-4">CheckCircle2</v-icon>
                    <h3 class="text-h5 font-weight-bold">Inbox Zero!</h3>
                    <p class="text-medium-emphasis">No new transactions waiting for review.</p>
                </div>

                <v-row v-if="triagePagination.total > 0" class="mt-4 align-center">
                    <v-col cols="12" md="4" class="text-caption text-medium-emphasis">
                        Showing {{ triagePagination.skip + 1 }}-{{ Math.min(triagePagination.skip +
                            triagePagination.limit,
                            triagePagination.total) }} of {{ triagePagination.total }}
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex justify-center">
                        <v-pagination v-model="triageCurrentPage"
                            :length="Math.ceil(triagePagination.total / triagePagination.limit)" :total-visible="5"
                            density="compact" active-color="primary" variant="text"
                            class="modern-pagination"></v-pagination>
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex justify-end align-center gap-2">
                        <span class="text-caption mr-2">Rows per page:</span>
                        <v-select :model-value="triagePagination.limit"
                            @update:model-value="handleTriagePaginationLimitChange($event)" :items="[12, 24, 60]"
                            density="compact" variant="plain" hide-details class="rounded-lg rows-per-page-select"
                            style="width: 75px"></v-select>
                    </v-col>
                </v-row>
            </v-window-item>

            <!-- TRAINING TAB -->
            <v-window-item value="training">
                <v-alert icon="Bot" type="warning" variant="tonal" class="mb-4" border="start" density="compact">
                    <strong>Interactive Training</strong>: These messages look like transactions but could
                    not be parsed. Label them to help the system learn!
                </v-alert>

                <!-- Training Toolbar -->
                <v-card class="premium-glass-card mb-4 pa-3 no-hover" style="border-radius: 20px !important;">
                    <v-row align="center" no-gutters class="gap-3 px-2">
                        <v-col cols="auto" class="d-flex align-center gap-3">
                            <v-checkbox-btn
                                :model-value="selectedTrainingIds.length === unparsedMessages.length && unparsedMessages.length > 0"
                                @update:model-value="toggleSelectAllTraining" color="warning" label="Select All"
                                hide-details density="compact" class="ml-1"></v-checkbox-btn>

                            <v-fade-transition>
                                <v-tooltip v-if="selectedTrainingIds.length > 0"
                                    :text="`Dismiss ${selectedTrainingIds.length} selected messages`" location="top"
                                    open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" color="error" variant="tonal" size="small"
                                            prepend-icon="Trash2" @click="emit('bulkDismissTraining')" rounded="lg">
                                            Dismiss {{ selectedTrainingIds.length }}
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                            </v-fade-transition>
                        </v-col>

                        <v-spacer></v-spacer>
                        <v-divider vertical class="d-none d-md-block mx-1" />

                        <v-col cols="12" md="auto" class="d-flex align-center gap-2">
                            <v-select :model-value="trainingSortKey"
                                @update:model-value="emit('update:trainingSortKey', $event)"
                                :items="[{ title: 'Date', value: 'created_at' }, { title: 'Sender', value: 'sender' }]"
                                item-title="title" item-value="value" hide-details density="compact" variant="solo"
                                label="Sort" style="width: 140px" rounded="lg" class="filter-field-premium"></v-select>

                            <v-tooltip :text="`Sort by ${trainingSortOrder === 'asc' ? 'Descending' : 'Ascending'}`"
                                location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props"
                                        @click="emit('update:trainingSortOrder', trainingSortOrder === 'asc' ? 'desc' : 'asc')"
                                        variant="tonal" size="small" height="40" width="40" color="warning"
                                        class="rounded-lg"
                                        :icon="trainingSortOrder === 'asc' ? 'ArrowUp' : 'ArrowDown'">
                                    </v-btn>
                                </template>
                            </v-tooltip>
                            <v-tooltip text="Refresh training data" location="top" open-delay="400">
                                <template v-slot:activator="{ props }">
                                    <v-btn v-bind="props" icon="RefreshCcw" variant="text" size="small"
                                        @click="emit('refreshTriage')"></v-btn>
                                </template>
                            </v-tooltip>
                        </v-col>
                    </v-row>
                </v-card>

                <!-- Training Grid -->
                <v-row>
                    <v-col v-for="msg in sortedTrainingMessages" :key="msg.id" cols="12" md="6" lg="6">
                        <v-card class="premium-glass-card training-card" variant="flat">
                            <!-- Dynamic Accent Glow (Warning for Training) -->
                            <div class="card-glow-accent training-glow"></div>

                            <div class="card-modern-header px-4 pt-4 pb-2">
                                <div class="d-flex align-center gap-3 overflow-hidden">
                                    <v-checkbox-btn v-model="selectedTrainingIds" :value="msg.id" color="warning"
                                        density="compact" hide-details class="mt-n1"></v-checkbox-btn>

                                    <div class="flex-grow-1 min-width-0">
                                        <div
                                            class="text-subtitle-2 font-weight-black text-truncate modern-header-title mb-1">
                                            {{ msg.sender || 'Unknown Sender' }}
                                        </div>
                                        <div class="d-flex flex-wrap align-center gap-2 text-caption opacity-70">
                                            <span class="font-weight-bold">{{ formatDate(msg.created_at).day }}</span>
                                            <span class="opacity-30">•</span>
                                            <span class="text-uppercase tracking-wider font-weight-black opacity-50">{{
                                                msg.source }}</span>
                                            <v-chip color="warning" size="x-small" variant="flat" class="ml-auto">Needs
                                                Training</v-chip>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <v-card-text class="flex-grow-1 px-4 py-2 d-flex flex-column gap-3">
                                <div v-if="msg.subject" class="text-caption font-weight-bold opacity-60">
                                    Subject: <span class="text-on-surface opacity-100">{{ msg.subject }}</span>
                                </div>

                                <div class="modern-message-container training-message-box pa-3">
                                    <div class="text-caption message-content training-content">
                                        {{ msg.raw_content }}
                                    </div>
                                </div>
                            </v-card-text>

                            <div class="modern-card-footer px-3 py-2 d-flex align-center gap-1 border-t mt-auto">
                                <v-tooltip text="Dismiss this message" location="top" open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" variant="tonal" color="grey" size="small"
                                            class="rounded-lg footer-action-btn"
                                            @click="emit('dismissTraining', msg.id)">
                                            <v-icon size="16">Trash2</v-icon>
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                                <v-spacer></v-spacer>
                                <v-tooltip text="Label this message as a transaction to train the system" location="top"
                                    open-delay="400">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-bind="props" color="warning" variant="tonal" size="small"
                                            class="rounded-lg footer-action-btn" @click="emit('startLabeling', msg)">
                                            <v-icon size="16">Sparkles</v-icon>
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="trainingPagination.total === 0" class="text-center py-12">
                    <v-icon size="64" color="success" class="mb-4">ShieldCheck</v-icon>
                    <h3 class="text-h5 font-weight-bold">All Clear!</h3>
                    <p class="text-medium-emphasis">No unparsed messages waiting for training.</p>
                </div>

                <v-row v-if="trainingPagination.total > 0" class="mt-4 align-center">
                    <v-col cols="12" md="4" class="text-caption text-medium-emphasis">
                        Showing {{ trainingPagination.skip + 1 }}-{{ Math.min(trainingPagination.skip +
                            trainingPagination.limit,
                            trainingPagination.total) }} of {{ trainingPagination.total }}
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex justify-center">
                        <v-pagination v-model="trainingCurrentPage"
                            :length="Math.ceil(trainingPagination.total / trainingPagination.limit)" :total-visible="5"
                            density="compact" active-color="warning" variant="text"
                            class="modern-pagination"></v-pagination>
                    </v-col>
                    <v-col cols="12" md="4" class="d-flex justify-end align-center gap-2">
                        <span class="text-caption mr-2">Rows per page:</span>
                        <v-select :model-value="trainingPagination.limit"
                            @update:model-value="handleTrainingPaginationLimitChange($event)" :items="[12, 24, 60]"
                            density="compact" variant="plain" hide-details class="d-inline-block rows-per-page-select"
                            style="width: 70px"></v-select>
                    </v-col>
                </v-row>
            </v-window-item>
        </v-window>

        <!-- Details Modal -->
        <v-dialog v-model="triageDetailsDialog" max-width="600" persistent transition="dialog-bottom-transition">
            <v-card v-if="selectedTriageTxn" class="rounded-xl overflow-hidden">
                <v-toolbar color="primary" density="compact">
                    <v-toolbar-title class="text-subtitle-1 font-weight-bold">Transaction Details</v-toolbar-title>
                    <v-spacer></v-spacer>
                    <v-tooltip text="Close details" location="bottom" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" icon variant="text" @click="triageDetailsDialog = false">
                                <v-icon>X</v-icon>
                            </v-btn>
                        </template>
                    </v-tooltip>
                </v-toolbar>

                <v-card-text class="pt-6">
                    <div class="d-flex align-center justify-space-between mb-6">
                        <div>
                            <div class="text-h6 font-weight-black">{{ selectedTriageTxn.recipient ||
                                selectedTriageTxn.description }}</div>
                            <div class="text-caption text-medium-emphasis">
                                {{ formatDate(selectedTriageTxn.date).day }} • {{
                                    formatDate(selectedTriageTxn.date).meta }}
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-h5 font-weight-black"
                                :class="selectedTriageTxn.amount < 0 ? 'text-error' : 'text-success'">
                                {{ formatAmount(Math.abs(selectedTriageTxn.amount)) }}
                            </div>
                            <div class="text-caption text-medium-emphasis">{{ selectedTriageTxn.amount < 0 ? 'DEBIT'
                                : 'CREDIT' }}</div>
                            </div>
                        </div>

                        <v-divider class="mb-6"></v-divider>

                        <v-row>
                            <v-col cols="12">
                                <v-label class="text-caption font-weight-bold mb-2">Account</v-label>
                                <v-select v-model="selectedTriageTxn.account_id" :items="accountOptions"
                                    item-title="title" item-value="value" density="compact" variant="outlined"
                                    hide-details prepend-inner-icon="Landmark"></v-select>
                            </v-col>

                            <v-col cols="12">
                                <v-autocomplete v-model="selectedTriageTxn.category" :items="categoryOptions"
                                    item-title="title" item-value="value" placeholder="Select Category"
                                    variant="solo-filled" density="compact" rounded="lg" hide-details
                                    prepend-inner-icon="Tag"></v-autocomplete>
                            </v-col>

                            <v-col v-if="selectedTriageTxn.is_transfer" cols="12">
                                <v-label class="text-caption font-weight-bold mb-2">
                                    {{ selectedTriageTxn.amount < 0 ? 'Transfer To' : 'Transfer From' }} </v-label>
                                        <v-select v-model="selectedTriageTxn.to_account_id"
                                            :items="accountOptions.filter(a => a.value !== selectedTriageTxn.account_id)"
                                            item-title="title" item-value="value" density="compact" variant="outlined"
                                            hide-details></v-select>
                            </v-col>
                        </v-row>

                        <v-divider class="my-6"></v-divider>

                        <div class="d-flex flex-column gap-3">
                            <v-switch v-model="selectedTriageTxn.is_transfer" color="info" label="Internal Transfer"
                                density="compact" hide-details inset
                                @update:model-value="selectedTriageTxn.exclude_from_reports = selectedTriageTxn.is_transfer"></v-switch>

                            <v-switch v-model="selectedTriageTxn.exclude_from_reports" color="warning"
                                label="Hide in Reports" density="compact" hide-details inset></v-switch>
                        </div>

                        <div v-if="selectedTriageTxn.raw_message" class="mt-6">
                            <v-label class="text-caption font-weight-bold mb-2">Raw Message</v-label>
                            <div class="bg-grey-lighten-4 pa-4 rounded-lg text-caption italic border">
                                {{ selectedTriageTxn.raw_message }}
                            </div>
                        </div>
                </v-card-text>

                <v-divider></v-divider>

                <v-card-actions class="pa-4">
                    <v-spacer></v-spacer>
                    <v-tooltip text="Discard changes and close" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" variant="text" color="grey-darken-1"
                                @click="triageDetailsDialog = false" class="text-none">
                                Close
                            </v-btn>
                        </template>
                    </v-tooltip>
                    <v-tooltip text="Save changes and return to triage" location="top" open-delay="400">
                        <template v-slot:activator="{ props }">
                            <v-btn v-bind="props" color="primary" variant="elevated" class="text-none px-6 rounded-lg"
                                @click="saveTriageDetails">
                                Apply Changes
                            </v-btn>
                        </template>
                    </v-tooltip>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Add Alias Modal -->
        <VendorAliasModal v-model="showAliasModal" :initial-pattern="aliasForm.pattern" :initial-alias="aliasForm.alias"
            @saved="emit('refreshTriage')" />

        <!-- Discard Confirmation Dialog (Triage) -->
        <v-dialog :model-value="showDiscardConfirm" @update:model-value="emit('update:showDiscardConfirm', $event)"
            max-width="450">
            <v-card class="rounded-xl pa-4">
                <v-card-text class="text-center">
                    <div class="text-h3 mb-4">🗑️</div>
                    <div class="text-h6 font-weight-bold mb-2">
                        {{ triageIdToDiscard ? 'Discard Transaction?' : `Discard ${selectedTriageIds.length}
                        Transactions?` }}
                    </div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        This will remove the transaction(s) from your inbox. This action is permanent.
                    </p>

                    <v-checkbox :model-value="createIgnoreRule"
                        @update:model-value="emit('update:createIgnoreRule', !!$event)"
                        label="Ignore this pattern in future" color="primary" density="compact" hide-details
                        class="mb-4"></v-checkbox>

                    <div class="d-flex gap-3 justify-center">
                        <v-tooltip text="Keep these transactions" location="top" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="text" @click="emit('update:showDiscardConfirm', false)"
                                    rounded="lg">Cancel</v-btn>
                            </template>
                        </v-tooltip>
                        <v-tooltip text="Permanently remove selected items" location="top" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" color="error" variant="elevated" rounded="lg" class="px-6"
                                    @click="triageIdToDiscard ? emit('confirmDiscard') : emit('confirmBulkDiscard')">
                                    Confirm Discard
                                </v-btn>
                            </template>
                        </v-tooltip>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Discard Confirmation Dialog (Training) -->
        <v-dialog :model-value="showTrainingDiscardConfirm"
            @update:model-value="emit('update:showTrainingDiscardConfirm', $event)" max-width="450">
            <v-card class="rounded-xl pa-4">
                <v-card-text class="text-center">
                    <div class="text-h3 mb-4">👋</div>
                    <div class="text-h6 font-weight-bold mb-2">
                        {{ trainingIdToDiscard ? 'Dismiss Message?' : `Dismiss ${selectedTrainingIds.length} Messages?`
                        }}
                    </div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        Are you sure you want to dismiss these unparsed messages?
                    </p>

                    <v-checkbox :model-value="createIgnoreRule"
                        @update:model-value="emit('update:createIgnoreRule', !!$event)"
                        label="Don't show this sender again" color="primary" density="compact" hide-details
                        class="mb-4"></v-checkbox>

                    <div class="d-flex gap-3 justify-center">
                        <v-tooltip text="Keep these messages" location="top" open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="text"
                                    @click="emit('update:showTrainingDiscardConfirm', false)"
                                    rounded="lg">Cancel</v-btn>
                            </template>
                        </v-tooltip>
                        <v-tooltip text="Dismiss these messages and clear them from training" location="top"
                            open-delay="400">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" color="warning" variant="elevated" rounded="lg" class="px-6"
                                    @click="trainingIdToDiscard ? emit('confirmTrainingDiscard') : emit('confirmBulkTrainingDiscard')">
                                    Dismiss
                                </v-btn>
                            </template>
                        </v-tooltip>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<style scoped>
/* VIBRANT GLASSMORPHISM DESIGN SYSTEM */
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(10px) !important;
    -webkit-backdrop-filter: blur(10px) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07) !important;
    transition: all 0.4s cubic-bezier(0.23, 1, 0.32, 1);
    position: relative;
    overflow: hidden;
    min-height: 32px;
    display: flex;
    flex-direction: column
}

.premium-glass-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0) 100%);
    pointer-events: none;
    z-index: 1;
}

.premium-glass-card.is-selected {
    border: 2px solid rgb(var(--v-theme-primary)) !important;
    background: rgba(var(--v-theme-primary), 0.05) !important;
}

.premium-glass-card:hover {
    transform: translateY(-4px) scale(1.01);
    box-shadow: 0 12px 24px -10px rgba(0, 0, 0, 0.15) !important;
}

/* Dynamic Accent Glow */
.card-glow-accent {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: transparent;
    transition: all 0.3s ease;
    z-index: 2;
}

.is-debit .card-glow-accent {
    background: linear-gradient(90deg, rgba(var(--v-theme-error), 0.8), transparent);
    box-shadow: 0 0 15px rgba(var(--v-theme-error), 0.4);
}

.is-credit .card-glow-accent {
    background: linear-gradient(90deg, rgba(var(--v-theme-success), 0.8), transparent);
    box-shadow: 0 0 15px rgba(var(--v-theme-success), 0.4);
}

.training-glow {
    background: linear-gradient(90deg, rgba(var(--v-theme-warning), 0.8), transparent) !important;
    box-shadow: 0 0 15px rgba(var(--v-theme-warning), 0.4) !important;
}


.modern-header-title {
    color: rgba(var(--v-theme-on-surface), 0.9);
    letter-spacing: -0.3px;
    line-height: 1.2;
    text-align: left !important;
}

.modern-amount-display {
    font-family: 'Inter', sans-serif;
    letter-spacing: -1.5px;
    font-size: 1.8rem !important;
    font-weight: 900 !important;
}

.amount-hero-section {
    background: rgba(var(--v-theme-on-surface), 0.02);
    border-top: 1px solid rgba(var(--v-border-color), 0.05);
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.amount-hero-text {
    font-size: 2.2rem !important;
    line-height: 1;
    filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.05));
}

.modern-message-container {
    background: rgba(var(--v-theme-on-surface), 0.03);
    border-radius: 16px;
    border: 1px dashed rgba(var(--v-border-color), 0.2);
    position: relative;
    overflow: hidden;
}

.training-message-box {
    background: rgba(var(--v-theme-warning), 0.03) !important;
    border: 1px solid rgba(var(--v-theme-warning), 0.1) !important;
}

.message-content {
    font-family: 'Inter', sans-serif;
    line-height: 1.5;
    color: rgba(var(--v-theme-on-surface), 0.7);
    font-style: italic;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.training-content {
    font-family: 'Fira Code', 'Courier New', monospace !important;
    font-style: normal !important;
    -webkit-line-clamp: 5 !important;
}

/* Tactile Toggles */
.tactile-toggle-group {
    background: rgba(var(--v-theme-on-surface), 0.04);
    padding: 3px;
    border-radius: 50px;
    border: 1px solid rgba(var(--v-border-color), 0.05) !important;
}

.tactile-toggle-group :deep(.v-btn) {
    height: 28px !important;
    font-size: 11px !important;
    font-weight: 800 !important;
    letter-spacing: 0.5px;
    border: none !important;
    transition: all 0.3s cubic-bezier(0.18, 0.89, 0.32, 1.28);
}

.tactile-toggle-group :deep(.v-btn--active) {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
}

.modern-card-footer {
    background: rgba(var(--v-theme-on-surface), 0.02);
    backdrop-filter: blur(5px);
}

.footer-action-btn {
    transition: all 0.2s ease;
}

.footer-action-btn:hover {
    transform: scale(1.1);
}

/* Pagination Styling */
.modern-pagination :deep(.v-pagination__item) {
    border-radius: 12px !important;
    font-weight: 800;
    background: rgba(var(--v-theme-surface), 0.5) !important;
}

.rows-per-page-select :deep(.v-field__input) {
    font-weight: 800;
    font-family: 'Inter';
}

.gap-3 {
    gap: 12px;
}

.filter-field-premium :deep(.v-field),
.search-input-premium :deep(.v-field),
.rows-per-page-select :deep(.v-field) {
    background: rgba(var(--v-theme-surface), 0.5) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    box-shadow: none !important;
    font-weight: 600;
}

:deep(.v-field--variant-solo),
:deep(.v-field--variant-solo-filled) {
    box-shadow: none !important;
}

.border-thin {
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
}

.tracking-wider {
    letter-spacing: 1px;
}
</style>
