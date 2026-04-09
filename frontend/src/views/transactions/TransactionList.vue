<template>
    <div class="transaction-list-container">
        <!-- Filter Bar -->
        <v-card class="premium-glass-card mb-6 pa-4 border-thin">
            <v-row align="center" no-gutters class="gap-4">
                <v-col cols="12" lg="auto">
                    <div class="d-flex align-center">
                        <span class="text-caption font-weight-bold text-uppercase opacity-70 mr-3">Account:</span>
                        <v-autocomplete :model-value="selectedAccount"
                            @update:model-value="emit('update:selectedAccount', $event)" :items="accountOptions"
                            item-title="title" item-value="value" placeholder="All Accounts" density="comfortable"
                            hide-details variant="outlined" class="account-select-premium font-weight-bold" rounded="lg"
                            bg-color="surface" />
                    </div>
                </v-col>

                <v-col cols="12" sm="6" md="3" lg="auto">
                    <div class="d-flex align-center">
                        <span class="text-caption font-weight-bold text-uppercase opacity-70 mr-3">Time:</span>
                        <v-autocomplete :model-value="selectedTimeRange" @update:model-value="handleTimeRangeChange"
                            :items="timeRangeOptions" item-title="title" item-value="value" density="comfortable"
                            hide-details variant="outlined" class="time-range-select-premium font-weight-bold"
                            rounded="lg" bg-color="surface" />
                    </div>
                </v-col>

                <v-col v-if="selectedTimeRange === 'custom'" cols="12" sm="6" md="3" lg="auto" class="animate-in">
                    <div class="d-flex align-center gap-2">
                        <v-text-field :model-value="startDate"
                            @update:model-value="emit('update:startDate', $event); emit('fetchData')" type="date"
                            density="comfortable" hide-details variant="outlined" rounded="lg"
                            class="date-input-premium font-weight-bold" bg-color="surface" />
                        <span class="text-caption opacity-50">to</span>
                        <v-text-field :model-value="endDate"
                            @update:model-value="emit('update:endDate', $event); emit('fetchData')" type="date"
                            density="comfortable" hide-details variant="outlined" rounded="lg"
                            class="date-input-premium font-weight-bold" bg-color="surface" />
                    </div>
                </v-col>

                <v-divider vertical class="d-none d-lg-block mx-2" />

                <v-col cols="12" md="4" lg="auto" class="flex-grow-1">
                    <v-text-field :model-value="searchQuery" @update:model-value="emit('update:searchQuery', $event)"
                        placeholder="Search description or recipient..." density="comfortable" hide-details
                        variant="outlined" rounded="lg" class="search-input-premium font-weight-bold" clearable
                        autocomplete="off" bg-color="surface">
                        <template v-slot:prepend-inner>
                            <Search :size="18" class="text-primary mr-2" />
                        </template>
                    </v-text-field>
                </v-col>

                <v-col cols="12" sm="6" md="3" lg="auto">
                    <v-autocomplete :model-value="categoryFilter"
                        @update:model-value="emit('update:categoryFilter', $event); emit('fetchData')"
                        :items="[{ title: 'All Categories', value: '' }, ...categoryOptions]" item-title="title"
                        item-value="value" placeholder="Category" density="comfortable" hide-details variant="outlined"
                        rounded="lg" class="category-select-premium font-weight-bold" bg-color="surface" />
                </v-col>

                <v-col cols="auto" v-if="startDate || endDate || searchQuery || categoryFilter">
                    <v-btn variant="text" size="small" color="primary" @click="handleReset" class="font-weight-bold">
                        Reset
                    </v-btn>
                </v-col>
            </v-row>
        </v-card>

        <!-- Bulk Actions & Info -->
        <div class="d-flex align-center justify-space-between mb-4 px-2">
            <div class="d-flex align-center gap-4">
                <span class="text-h6 font-weight-black">{{ total }} <span
                        class="text-subtitle-2 opacity-60">Transactions</span></span>

                <v-fade-transition>
                    <div v-if="selectedIds.size > 0" class="d-flex align-center gap-2">
                        <v-divider vertical class="mx-2" />
                        <span class="text-caption font-weight-bold text-primary">{{ selectedIds.size }} Selected</span>
                        <v-btn color="error" variant="tonal" size="x-small" @click="emit('deleteSelected')"
                            rounded="lg">
                            <template v-slot:prepend>
                                <Trash2 :size="14" />
                            </template>
                            Delete
                        </v-btn>
                    </div>
                </v-fade-transition>
            </div>

            <div class="d-flex align-center gap-2">
                <v-btn color="secondary" variant="tonal" size="small" @click="emit('importCsv')" rounded="lg">
                    <template v-slot:prepend>
                        <Upload :size="16" />
                    </template>
                    Import
                </v-btn>
                <v-btn color="primary" size="small" @click="emit('editTxn', null)" rounded="pill"
                    class="font-weight-black text-none">
                    <template v-slot:prepend>
                        <Plus :size="16" />
                    </template>
                    Add
                </v-btn>
            </div>
        </div>
        <!-- Transaction KPIs -->
        <v-row class="mb-6">
            <v-col cols="12" sm="4">
                <v-card class="glass-card pa-4 d-flex align-center border-thin" rounded="xl">
                    <v-avatar color="success" variant="tonal" class="mr-4" rounded="lg">
                        <TrendingUp :size="20" />
                    </v-avatar>
                    <div>
                        <div class="text-caption font-weight-bold opacity-60 text-uppercase">Income</div>
                        <div class="text-h6 font-weight-black text-success">{{
                            formatAmount(props.metrics.monthly_income) }}
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" sm="4">
                <v-card class="glass-card pa-4 d-flex align-center border-thin" rounded="xl">
                    <v-avatar color="error" variant="tonal" class="mr-4" rounded="lg">
                        <TrendingDown :size="20" />
                    </v-avatar>
                    <div>
                        <div class="text-caption font-weight-bold opacity-60 text-uppercase">Expenses</div>
                        <div class="text-h6 font-weight-black text-error">{{
                            formatAmount(Math.abs(props.metrics.monthly_spending)) }}
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" sm="4">
                <v-card class="glass-card pa-4 d-flex align-center border-thin" rounded="xl">
                    <v-avatar
                        :color="(props.metrics.monthly_income - props.metrics.monthly_spending) >= 0 ? 'primary' : 'warning'"
                        variant="tonal" class="mr-4" rounded="lg">
                        <Wallet :size="20" />
                    </v-avatar>
                    <div>
                        <div class="text-caption font-weight-bold opacity-60 text-uppercase">Net Flow</div>
                        <div class="text-h6 font-weight-black"
                            :class="(props.metrics.monthly_income - props.metrics.monthly_spending) >= 0 ? 'text-primary' : 'text-warning'">
                            {{ formatAmount(props.metrics.monthly_income - props.metrics.monthly_spending) }}
                        </div>
                    </div>
                </v-card>
            </v-col>
        </v-row>
        <!-- Transaction Table -->
        <v-card class="premium-glass-card overflow-hidden">
            <v-data-table-server v-model="tableSelection" :headers="headers" :items="transactions" :items-length="total"
                :loading="loading" :items-per-page="pageSize" :page="page" hover @update:options="handleOptionsUpdate"
                class="premium-table" density="comfortable" show-select
                :row-props="(data: any) => ({ class: { 'hidden-txn-row': data.item.exclude_from_reports } })">
                <!-- Selection Column Slot -->
                <template #[`item.data-table-select`]="{ item }">
                    <v-checkbox-btn :model-value="selectedIds.has(item.id)"
                        @update:model-value="toggleSelection(item.id)" color="primary" />
                </template>

                <!-- Date Column -->
                <template #[`item.date`]="{ item }">
                    <div class="date-cell">
                        <div class="text-subtitle-2 font-weight-bold">{{ formatDate(item.date).day }}</div>
                        <div class="text-caption opacity-50 font-weight-medium">{{ formatDate(item.date).meta }}</div>
                    </div>
                </template>

                <!-- Recipient Column -->
                <template #[`item.recipient`]="{ item }">
                    <div class="d-flex align-center gap-3 py-2">
                        <v-tooltip :text="getCategoryDisplay(item.category || '').text" location="top">
                            <template v-slot:activator="{ props }">
                                <v-avatar v-bind="props" size="36"
                                    :color="getCategoryDisplay(item.category || '').color + '20'" rounded="lg">
                                    <span class="text-h6 pb-1">{{ getCategoryDisplay(item.category || '').icon }}</span>
                                </v-avatar>
                            </template>
                        </v-tooltip>
                        <div>
                            <div class="text-subtitle-2 font-weight-bold text-truncate" style="max-width: 200px;">
                                <router-link v-if="item.recipient"
                                    :to="`/merchants/${encodeURIComponent(item.recipient || '')}`"
                                    class="text-decoration-none text-content hover-underline">
                                    {{ item.recipient }}
                                </router-link>
                                <span v-else>{{ item.description }}</span>
                            </div>
                            <div class="text-caption d-flex align-center gap-1 font-weight-bold" v-if="item.source">
                                <div class="d-flex align-center opacity-50">
                                    <span class="source-icon-mini">{{ item.source === 'SMS' ? '📱' : (item.source ===
                                        'EMAIL' ? '📧' : '⌨️') }}</span>
                                    {{ item.source }}
                                </div>
                                <v-tooltip text="Quick Insights" location="top">
                                    <template v-slot:activator="{ props }">
                                        <v-btn v-if="item.recipient" v-bind="props" icon variant="text" size="x-small" density="compact" class="ml-1" color="primary" @click.stop="emit('showVendorInsights', item.recipient || '')">
                                            <v-icon size="small" icon="$info"></v-icon>
                                        </v-btn>
                                    </template>
                                </v-tooltip>
                            </div>
                        </div>
                    </div>
                </template>

                <!-- Description Column -->
                <template #[`item.description`]="{ item }">
                    <div class="py-2">
                        <div class="text-body-2 text-medium-emphasis mb-1 d-flex align-center">
                            {{ item.description }}
                            <v-tooltip v-if="item.latitude || item.location_name"
                                :text="item.location_name || 'Location available'">
                                <template #activator="{ props }">
                                    <MapPin v-bind="props" :size="14" class="ml-1 text-primary" />
                                </template>
                            </v-tooltip>
                        </div>
                        <div class="d-flex align-center flex-wrap gap-1">
                            <v-chip size="x-small" variant="flat" color="surface-variant"
                                class="text-uppercase font-weight-black opacity-70">
                                {{ getAccountName(item.account_id) }}
                            </v-chip>

                            <v-chip v-if="item.is_ai_parsed" size="x-small" color="primary" variant="tonal"
                                class="font-weight-bold">
                                ✨ AI
                            </v-chip>
                            <v-chip v-if="item.is_transfer" size="x-small" color="success" variant="tonal"
                                class="font-weight-bold">
                                🔄 Transfer
                            </v-chip>
                            <v-chip v-if="item.exclude_from_reports" size="x-small" color="error" variant="tonal"
                                class="font-weight-bold">
                                🚫 Hidden
                            </v-chip>
                            <v-chip v-if="item.is_emi" size="x-small" color="info" variant="tonal"
                                class="font-weight-bold">
                                🏦 EMI
                            </v-chip>



                            <v-chip v-if="item.expense_group_id" size="x-small" color="secondary" variant="tonal"
                                class="font-weight-bold">
                                📁 {{ getExpenseGroupName(item.expense_group_id) }}
                            </v-chip>
                        </div>
                    </div>
                </template>

                <!-- Amount Column -->
                <template #[`item.amount`]="{ item }">
                    <div class="text-right">
                        <div :class="[
                            'text-subtitle-1 font-weight-black',
                            Number(item.amount) > 0 ? 'text-success' : 'text-error',
                            item.is_transfer ? 'opacity-70 text-medium-emphasis grayscale' : ''
                        ]">
                            <span v-if="item.is_transfer">🔄</span>
                            <span v-else-if="Number(item.amount) > 0">↓</span>
                            <span v-else>↑</span>
                            {{ formatAmount(Math.abs(Number(item.amount))) }}
                        </div>
                    </div>
                </template>

                <!-- Actions Column -->
                <template #[`item.actions`]="{ item }">
                    <div class="text-center">
                        <v-menu location="start">
                            <template v-slot:activator="{ props }">
                                <v-btn size="x-small" variant="text" color="medium-emphasis" v-bind="props">
                                    <MoreVertical :size="18" />
                                </v-btn>
                            </template>
                            <v-list density="compact" class="rounded-lg border" elevation="2">
                                <v-list-item @click="emit('editTxn', item)" title="Edit" value="edit">
                                    <template v-slot:prepend>
                                        <Pencil :size="16" class="mr-2" />
                                    </template>
                                </v-list-item>
                                <v-list-item @click="openAliasModal(item)" title="Map Merchant" value="map">
                                    <template v-slot:prepend>
                                        <MapPin :size="16" class="mr-2" />
                                    </template>
                                </v-list-item>
                                <v-divider class="my-1"></v-divider>
                                <v-list-item @click="() => { selectedIds = new Set([item.id]); emit('deleteSelected') }"
                                    title="Delete" value="delete" color="error">
                                    <template v-slot:prepend>
                                        <Trash2 :size="16" class="mr-2" />
                                    </template>
                                </v-list-item>
                            </v-list>
                        </v-menu>
                    </div>
                </template>

                <!-- Empty State -->
                <template #no-data>
                    <div class="d-flex flex-column align-center justify-center pa-10 text-center animate-in">
                        <v-avatar size="100" color="surface-variant" variant="tonal" class="mb-6">
                            <FileText :size="48" class="opacity-50" />
                        </v-avatar>
                        <h3 class="text-h5 font-weight-black mb-1">No Transactions Found</h3>
                        <p class="text-body-1 text-medium-emphasis">Adjust your filters or try a different search term.
                        </p>
                        <v-btn color="primary" variant="text" class="mt-4 font-weight-bold" @click="handleReset">Clear
                            All
                            Filters</v-btn>
                    </div>
                </template>

                <!-- Loading State -->
                <template #loading>
                    <div class="py-2">
                        <div v-for="i in 10" :key="i"
                            class="d-flex align-center px-4 py-3 border-b border-opacity-25 glass-loader-row">
                            <!-- Avatar Skeleton -->
                            <v-skeleton-loader type="avatar" size="40" class="mr-4 skeleton-glass"></v-skeleton-loader>

                            <!-- Title & Subtitle Skeleton -->
                            <div class="flex-grow-1 mr-4">
                                <v-skeleton-loader type="text" width="60%"
                                    class="mb-1 skeleton-glass"></v-skeleton-loader>
                                <v-skeleton-loader type="text" width="40%" height="12"
                                    class="skeleton-glass"></v-skeleton-loader>
                            </div>

                            <!-- Amount Skeleton -->
                            <div class="text-right">
                                <v-skeleton-loader type="text" width="80px" class="skeleton-glass"></v-skeleton-loader>
                            </div>
                        </div>
                    </div>
                </template>
            </v-data-table-server>
        </v-card>

        <MerchantAliasModal v-model="showAliasModal" :initial-pattern="aliasForm.pattern"
            :initial-alias="aliasForm.alias" @saved="() => { emit('fetchData') }" />
    </div>
</template>

<script setup lang="ts">
import { computed, ref, reactive } from 'vue'
import MerchantAliasModal from '@/components/MerchantAliasModal.vue'
import { useCurrency } from '@/composables/useCurrency'
import {
    Search,
    Trash2,
    Upload,
    Plus,
    MapPin,
    Pencil,
    MoreVertical,
    FileText,
    TrendingUp,
    TrendingDown,
    Wallet
} from 'lucide-vue-next'

const { formatAmount } = useCurrency()

export interface AccountItem {
    id: string
    name: string
    type?: string
    [key: string]: any
}

export interface CategoryItem {
    id: string
    name: string
    icon?: string
    color?: string
    parent_id?: string
    subcategories?: CategoryItem[]
    [key: string]: any
}

export interface ExpenseGroup {
    id: string
    name: string
    [key: string]: any
}

export interface TransactionItem {
    id: string
    date: string
    amount: number | string
    recipient?: string
    description?: string
    category?: string
    account_id: string
    source?: string
    is_ai_parsed?: boolean
    is_transfer?: boolean
    exclude_from_reports?: boolean
    is_emi?: boolean
    expense_group_id?: string
    latitude?: number
    location_name?: string
    [key: string]: any
}

// Props
const props = defineProps<{
    transactions: TransactionItem[]
    accounts: AccountItem[]
    categories: CategoryItem[]
    expenseGroups: ExpenseGroup[]
    total: number
    loading: boolean
    selectedAccount: string
    categoryFilter: string
    searchQuery: string
    startDate: string
    endDate: string
    selectedTimeRange: string
    page: number
    pageSize: number
    txnSortOrder: 'asc' | 'desc'
    metrics: {
        monthly_income: number
        monthly_spending: number
        breakdown: {
            net_worth: number
        }
    }
    txnSortKey: string
}>()

// Emits
const emit = defineEmits<{
    'update:selectedAccount': [value: string]
    'update:categoryFilter': [value: string]
    'update:searchQuery': [value: string]
    'update:startDate': [value: string]
    'update:endDate': [value: string]
    'update:selectedTimeRange': [value: string]
    'update:page': [value: number]
    'update:pageSize': [value: number]
    'sortChange': [key: string]
    'editTxn': [txn: TransactionItem | null]
    'deleteSelected': []
    'importCsv': [],
    'fetchData': [],
    'resetFilters': [],
    'showVendorInsights': [vendorName: string]
}>()

// --- Merchant Alias Logic (Encapsulated) ---
const showAliasModal = ref(false)
const aliasForm = reactive({
    pattern: '',
    alias: ''
})

function openAliasModal(txn: TransactionItem) {
    aliasForm.pattern = txn.description || txn.recipient || ''
    aliasForm.alias = txn.recipient || ''
    showAliasModal.value = true
}

// Local State
const selectedIds = defineModel<Set<string>>('selectedIds', { default: () => new Set() })

// Headers for v-data-table
const headers = [
    { title: 'Date', key: 'date', sortable: true, width: '110px' },
    { title: 'Recipient / Source', key: 'recipient', sortable: true, width: '250px' },
    { title: 'Description', key: 'description', sortable: false },
    { title: 'Amount', key: 'amount', sortable: true, align: 'end' as const, width: '130px' },
    { title: '', key: 'actions', sortable: false, align: 'center' as const, width: '60px' },
]

// Adaptation for v-data-table selection (array based) vs parent's Set based
const tableSelection = computed({
    get: () => Array.from(selectedIds.value),
    set: (newSelection: any[]) => {
        selectedIds.value = new Set(newSelection)
    }
})

// Computed
const accountOptions = computed(() => {
    return [{ title: 'All Accounts', value: '' }, ...props.accounts.map(a => ({ title: a.name, value: a.id }))]
})

const flatCategories = computed(() => {
    const list: CategoryItem[] = []
    const flatten = (cats: CategoryItem[]) => {
        cats.forEach(c => {
            list.push(c)
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories)
            }
        })
    }
    flatten(props.categories)
    return list
})

const categoryOptions = computed(() => {
    const options = flatCategories.value.map(c => {
        // Find depth for indentation
        let depth = 0
        let current = c
        while (current.parent_id) {
            depth++
            const parent = flatCategories.value.find(p => p.id === current.parent_id)
            if (!parent) break
            current = parent
        }

        const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
        return {
            title: `${prefix}${c.icon || '🏷️'} ${c.name}`,
            value: c.name
        }
    })

    if (!options.find(o => o.value === 'Uncategorized')) {
        options.push({ title: '🏷️ Uncategorized', value: 'Uncategorized' })
    }
    return options
})

const timeRangeOptions = [
    { title: 'All Time', value: 'all' },
    { title: 'Today', value: 'today' },
    { title: 'This Week', value: 'this-week' },
    { title: 'This Month', value: 'this-month' },
    { title: 'Last Month', value: 'last-month' },
    { title: 'Custom Range', value: 'custom' }
]

// Methods
function handleOptionsUpdate(options: any) {
    if (options.sortBy && options.sortBy.length > 0) {
        const field = options.sortBy[0].key
        if (field !== props.txnSortKey) {
            emit('sortChange', field)
        }
    }
    if (options.page !== props.page) {
        emit('update:page', options.page)
    }
    if (options.itemsPerPage !== props.pageSize) {
        emit('update:pageSize', options.itemsPerPage)
    }
}

function toggleSelection(id: string) {
    const newSet = new Set(selectedIds.value)
    if (newSet.has(id)) {
        newSet.delete(id)
    } else {
        newSet.add(id)
    }
    selectedIds.value = newSet
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

function getAccountName(id: string) {
    const acc = props.accounts.find(a => a.id === id)
    return acc ? acc.name : 'Unknown Account'
}

function getCategoryDisplay(name: string) {
    if (!name || name === 'Uncategorized') return { icon: '🏷️', text: 'Uncategorized', color: '#9ca3af' }

    const cat = flatCategories.value.find(c => c.name === name)
    if (cat) {
        let text = cat.name
        // Try to find parent name from flat list
        const parent = cat.parent_id ? flatCategories.value.find(p => p.id === cat.parent_id) : null
        if (parent) {
            text = `${parent.name} › ${cat.name}`
        }
        return { icon: cat.icon || '🏷️', text: text, color: cat.color || '#3B82F6' }
    }

    return { icon: '🏷️', text: name, color: '#9ca3af' }
}

function getExpenseGroupName(id: string) {
    if (!id) return null
    const group = props.expenseGroups.find(g => g.id === id)
    return group ? group.name : null
}

function handleTimeRangeChange(val: string) {
    emit('update:selectedTimeRange', val)
}

function handleReset() {
    emit('resetFilters')
}
</script>

<style scoped>
/* Skeleton Loader Overrides */
.skeleton-glass {
    background: transparent !important;
}

.skeleton-glass :deep(.v-skeleton-loader__bone) {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
    border-radius: 8px;
}

.skeleton-glass :deep(.v-skeleton-loader__avatar) {
    border-radius: 12px;
}

.glass-loader-row {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: .5;
    }
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 24px;
}

.glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.date-cell {
    line-height: 1.3;
}

.source-icon-mini {
    font-size: 0.75rem;
}

.hidden-txn-row {
    opacity: 0.5;
    filter: grayscale(0.5);
    background: rgba(var(--v-theme-on-surface), 0.02);
}

.hover-underline:hover {
    text-decoration: underline !important;
}

.animate-in {
    animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.gap-1 {
    gap: 4px;
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
}

/* Custom Scrollbar for the table if needed */
.premium-table :deep(.v-table__wrapper) {
    scrollbar-width: thin;
    scrollbar-color: rgba(var(--v-theme-on-surface), 0.1) transparent;
}
</style>
