<script setup lang="ts">
import { computed } from 'vue'
import CustomSelect from '@/components/CustomSelect.vue'
import { useCurrency } from '@/composables/useCurrency'

const { formatAmount } = useCurrency()

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
    return props.accounts.map(a => ({ label: a.name, value: a.id }))
})

const categoryOptions = computed(() => {
    const list: any[] = []
    const flatten = (cats: any[], depth = 0) => {
        cats.forEach(c => {
            const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
            list.push({
                label: `${prefix}${c.icon || '🏷️'} ${c.name}`,
                value: c.name
            })
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories, depth + 1)
            }
        })
    }
    flatten(props.categories)
    if (!list.find(o => o.value === 'Uncategorized')) {
        list.push({ label: '🏷️ Uncategorized', value: 'Uncategorized' })
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

const sortedTrainingMessages = computed(() => {
    const sorted = [...props.unparsedMessages]
    sorted.sort((a, b) => {
        let aVal, bVal
        if (props.trainingSortKey === 'created_at') {
            aVal = new Date(a.created_at).getTime()
            bVal = new Date(b.created_at).getTime()
        } else if (props.trainingSortKey === 'sender') {
            aVal = (a.sender || '').toLowerCase()
            bVal = (b.sender || '').toLowerCase()
        } else {
            return 0
        }

        if (props.trainingSortOrder === 'asc') {
            return aVal > bVal ? 1 : -1
        } else {
            return aVal < bVal ? 1 : -1
        }
    })
    return sorted
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

function handleTriagePaginationPrev() {
    emit('update:triagePagination', { ...props.triagePagination, skip: props.triagePagination.skip - props.triagePagination.limit })
}

function handleTriagePaginationNext() {
    emit('update:triagePagination', { ...props.triagePagination, skip: props.triagePagination.skip + props.triagePagination.limit })
}

function handleTrainingPaginationLimitChange(newLimit: number) {
    emit('update:trainingPagination', { ...props.trainingPagination, limit: newLimit, skip: 0 })
}

function handleTrainingPaginationPrev() {
    emit('update:trainingPagination', { ...props.trainingPagination, skip: props.trainingPagination.skip - props.trainingPagination.limit })
}

function handleTrainingPaginationNext() {
    emit('update:trainingPagination', { ...props.trainingPagination, skip: props.trainingPagination.skip + props.trainingPagination.limit })
}
</script>

<template>
    <div class="triage-view animate-in">
        <!-- Vuetify Tabs -->
        <v-tabs v-model="activeTab" color="primary" align-tabs="start" class="mb-6 rounded-lg bg-surface-light">
            <v-tab value="pending">
                <v-icon start icon="mdi-inbox-arrow-down" class="mr-2"></v-icon>
                Pending Inbox
                <v-chip size="x-small" color="primary" class="ml-2" variant="flat">
                    {{ triagePagination.total }}
                </v-chip>
            </v-tab>
            <v-tab value="training">
                <v-icon start icon="mdi-robot" class="mr-2"></v-icon>
                Training Area
                <v-chip size="x-small" color="warning" class="ml-2" variant="flat">
                    {{ trainingPagination.total }}
                </v-chip>
            </v-tab>
        </v-tabs>

        <v-window v-model="activeTab">
            <!-- PENDING TAB -->
            <v-window-item value="pending">
                <v-alert icon="mdi-shield-lock" type="info" variant="tonal" class="mb-4" border="start"
                    density="compact">
                    <strong>Review Intake</strong>: These transactions were auto-detected but require
                    categorization or confirmation before affecting your balance.
                </v-alert>

                <!-- Filters Toolbar -->
                <div class="d-flex flex-wrap align-center gap-3 mb-4 glass-card pa-3 rounded-lg">
                    <v-text-field :model-value="triageSearchQuery"
                        @update:model-value="emit('update:triageSearchQuery', $event)"
                        prepend-inner-icon="mdi-text-search" placeholder="Search merchant, ID or amount..." hide-details
                        density="compact" variant="outlined" bg-color="surface" class="flex-grow-1"
                        style="min-width: 250px; max-width: 400px"></v-text-field>

                    <v-btn-toggle :model-value="triageSourceFilter"
                        @update:model-value="emit('update:triageSourceFilter', $event || 'ALL')" density="compact"
                        color="primary" variant="outlined" divided mandatory class="rounded">
                        <v-btn value="ALL" size="small" class="px-4">All</v-btn>
                        <v-btn value="SMS" size="small" class="px-4">SMS</v-btn>
                        <v-btn value="EMAIL" size="small" class="px-4">Email</v-btn>
                    </v-btn-toggle>

                    <v-spacer></v-spacer>

                    <div class="d-flex align-center gap-2">
                        <v-select :model-value="triageSortKey"
                            @update:model-value="emit('update:triageSortKey', $event)"
                            :items="[{ title: 'Date', value: 'date' }, { title: 'Amount', value: 'amount' }, { title: 'Description', value: 'description' }]"
                            hide-details density="compact" variant="outlined" label="Sort by" style="width: 160px"
                            bg-color="surface"></v-select>

                        <v-btn @click="emit('update:triageSortOrder', triageSortOrder === 'asc' ? 'desc' : 'asc')"
                            variant="outlined" size="small" height="40" width="40" color="medium-emphasis"
                            class="rounded" :icon="triageSortOrder === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down'">
                        </v-btn>
                    </div>
                </div>

                <!-- Bulk Actions -->
                <div class="d-flex align-center justify-space-between mb-4">
                    <div class="d-flex align-center ga-4">
                        <v-checkbox-btn
                            :model-value="selectedTriageIds.length === filteredTriageTransactions.length && filteredTriageTransactions.length > 0"
                            @update:model-value="toggleSelectAllTriage" color="primary" label="Select All Filtered"
                            hide-details density="compact" class="ml-1"></v-checkbox-btn>

                        <v-scale-transition>
                            <v-btn v-if="selectedTriageIds.length > 0" color="error" variant="tonal" size="small"
                                prepend-icon="mdi-delete" @click="emit('bulkRejectTriage')">
                                Discard {{ selectedTriageIds.length }}
                            </v-btn>
                        </v-scale-transition>
                    </div>
                    <v-btn icon="mdi-refresh" variant="text" size="small" @click="emit('refreshTriage')"></v-btn>
                </div>

                <!-- Transactions Grid -->
                <v-row>
                    <v-col v-for="txn in filteredTriageTransactions" :key="txn.id" cols="12" md="6" lg="4">
                        <v-card class="h-100 d-flex flex-column glass-card"
                            :class="{ 'border-primary': selectedTriageIds.includes(txn.id) }" variant="flat"
                            :ripple="false">

                            <!-- Header -->
                            <v-card-item class="pb-0">
                                <template v-slot:prepend>
                                    <v-checkbox-btn v-model="selectedTriageIds" :value="txn.id" density="compact"
                                        hide-details></v-checkbox-btn>
                                </template>
                                <v-card-title class="text-subtitle-1 font-weight-bold">
                                    {{ txn.recipient || txn.description }}
                                </v-card-title>
                                <v-card-subtitle class="d-flex align-center">
                                    <v-chip size="x-small" label class="mr-2 text-caption">{{ txn.source }}</v-chip>
                                    {{ formatDate(txn.date).day }} • {{ formatDate(txn.date).meta }}
                                </v-card-subtitle>
                                <template v-slot:append>
                                    <div class="text-right">
                                        <div class="text-h6 font-weight-black"
                                            :class="txn.amount < 0 ? 'text-error' : 'text-success'">
                                            {{ formatAmount(Math.abs(txn.amount)) }}
                                        </div>
                                        <div class="text-caption text-medium-emphasis">{{ txn.amount < 0 ? 'Debit'
                                            : 'Credit' }}</div>
                                        </div>
                                </template>
                            </v-card-item>

                            <v-divider class="my-3 opacity-20"></v-divider>

                            <!-- Body -->
                            <v-card-text class="flex-grow-1 pt-0">
                                <div class="d-flex flex-wrap gap-2 mb-3">
                                    <v-chip v-if="txn.is_ai_parsed" size="x-small" color="purple" variant="flat"
                                        prepend-icon="mdi-auto-fix">AI
                                        Verified</v-chip>
                                    <v-chip v-if="txn.is_transfer" size="x-small" color="info" variant="flat"
                                        prepend-icon="mdi-bank-transfer">Self-Transfer</v-chip>
                                    <v-chip v-if="txn.external_id" size="x-small" variant="outlined"
                                        class="text-caption">ID: {{ txn.external_id
                                        }}</v-chip>
                                </div>

                                <div class="text-body-2 mb-2">
                                    <v-icon size="small" color="grey" start>mdi-bank</v-icon>
                                    {{ getAccountName(txn.account_id) }}
                                </div>
                                <div v-if="txn.raw_message"
                                    class="bg-grey-lighten-4 pa-2 rounded text-caption text-medium-emphasis mb-2 text-truncate">
                                    "{{ txn.raw_message }}"
                                </div>

                                <!-- Controls -->
                                <div class="d-flex flex-column gap-2 mt-4">
                                    <div class="d-flex align-center justify-space-between">
                                        <v-switch v-model="txn.is_transfer" color="info" label="Internal Transfer"
                                            density="compact" hide-details inset
                                            @change="txn.exclude_from_reports = txn.is_transfer"></v-switch>
                                        <v-switch v-model="txn.exclude_from_reports" color="error"
                                            label="Exclude from Reports" density="compact" hide-details
                                            inset></v-switch>
                                    </div>


                                    <v-select v-if="txn.is_transfer" v-model="txn.to_account_id"
                                        :items="accountOptions.filter(a => a.value !== txn.account_id)"
                                        item-title="label" item-value="value"
                                        :label="txn.amount < 0 ? 'To Account' : 'From Account'" density="compact"
                                        variant="outlined" hide-details></v-select>
                                    <CustomSelect v-else v-model="txn.category" :options="categoryOptions"
                                        placeholder="Assign Category" class="mt-2" />
                                </div>
                            </v-card-text>

                            <!-- Actions -->
                            <v-card-actions class="pa-4 pt-0">
                                <v-btn variant="text" color="grey" @click="emit('rejectTriage', txn.id)">Discard</v-btn>
                                <v-spacer></v-spacer>
                                <v-btn color="primary" variant="elevated"
                                    @click="emit('approveTriage', txn)">Confirm</v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="triagePagination.total === 0" class="text-center py-12">
                    <v-icon size="64" color="success" class="mb-4">mdi-check-circle-outline</v-icon>
                    <h3 class="text-h5 font-weight-bold">Inbox Zero!</h3>
                    <p class="text-medium-emphasis">No new transactions waiting for review.</p>
                </div>

                <!-- Pagination -->
                <v-row v-if="triagePagination.total > 0" class="mt-4 align-center">
                    <v-col cols="12" md="6" class="text-caption text-medium-emphasis">
                        Showing {{ triagePagination.skip + 1 }}-{{ Math.min(triagePagination.skip +
                            triagePagination.limit,
                            triagePagination.total) }} of {{ triagePagination.total }}
                    </v-col>
                    <v-col cols="12" md="6" class="d-flex justify-end align-center gap-2">
                        <span class="text-caption mr-2">Rows per page:</span>
                        <v-select :model-value="triagePagination.limit"
                            @update:model-value="handleTriagePaginationLimitChange($event)" :items="[12, 24, 60]"
                            density="compact" variant="outlined" hide-details class="d-inline-block"
                            style="width: 85px"></v-select>

                        <v-btn size="small" variant="text" :disabled="triagePagination.skip === 0"
                            @click="handleTriagePaginationPrev">Prev</v-btn>
                        <v-btn size="small" variant="text"
                            :disabled="triagePagination.skip + triagePagination.limit >= triagePagination.total"
                            @click="handleTriagePaginationNext">Next</v-btn>
                    </v-col>
                </v-row>
            </v-window-item>

            <!-- TRAINING TAB -->
            <v-window-item value="training">
                <v-alert icon="mdi-robot" type="warning" variant="tonal" class="mb-4" border="start" density="compact">
                    <strong>Interactive Training</strong>: These messages look like transactions but could
                    not be parsed. Label them to help the system learn!
                </v-alert>

                <!-- Training Toolbar -->
                <div class="d-flex align-center justify-space-between mb-4">
                    <div class="d-flex align-center ga-4">
                        <v-checkbox-btn
                            :model-value="selectedTrainingIds.length === unparsedMessages.length && unparsedMessages.length > 0"
                            @update:model-value="toggleSelectAllTraining" color="warning" label="Select All"
                            hide-details density="compact" class="ml-1"></v-checkbox-btn>

                        <v-scale-transition>
                            <v-btn v-if="selectedTrainingIds.length > 0" color="warning" variant="tonal" size="small"
                                prepend-icon="mdi-delete" @click="emit('bulkDismissTraining')">
                                Dismiss {{ selectedTrainingIds.length }}
                            </v-btn>
                        </v-scale-transition>
                    </div>

                    <div class="d-flex align-center gap-2">
                        <v-select :model-value="trainingSortKey"
                            @update:model-value="emit('update:trainingSortKey', $event)"
                            :items="[{ title: 'Date', value: 'created_at' }, { title: 'Sender', value: 'sender' }]"
                            hide-details density="compact" variant="outlined" label="Sort by" style="width: 160px"
                            bg-color="surface"></v-select>

                        <v-btn @click="emit('update:trainingSortOrder', trainingSortOrder === 'asc' ? 'desc' : 'asc')"
                            variant="outlined" size="small" height="40" width="40" color="medium-emphasis"
                            class="rounded" :icon="trainingSortOrder === 'asc' ? 'mdi-arrow-up' : 'mdi-arrow-down'">
                        </v-btn>
                        <v-btn icon="mdi-refresh" variant="text" size="small" @click="emit('refreshTriage')"></v-btn>
                    </div>
                </div>

                <!-- Training Grid -->
                <v-row>
                    <v-col v-for="msg in sortedTrainingMessages" :key="msg.id" cols="12" md="6">
                        <v-card class="h-100 d-flex flex-column glass-card" variant="flat">
                            <v-card-item>
                                <template v-slot:prepend>
                                    <v-checkbox-btn v-model="selectedTrainingIds" :value="msg.id" density="compact"
                                        hide-details></v-checkbox-btn>
                                </template>
                                <v-card-title class="text-subtitle-1">
                                    {{ msg.sender || 'Unknown Sender' }}
                                </v-card-title>
                                <v-card-subtitle>
                                    {{ formatDate(msg.created_at).day }} • {{ msg.source }}
                                </v-card-subtitle>
                                <template v-slot:append>
                                    <v-chip color="warning" size="small" variant="flat">Needs Training</v-chip>
                                </template>
                            </v-card-item>

                            <v-divider></v-divider>

                            <v-card-text class="flex-grow-1">
                                <div v-if="msg.subject" class="mb-2 text-body-2 font-weight-bold">
                                    Subject: <span class="text-medium-emphasis font-weight-regular">{{ msg.subject
                                        }}</span>
                                </div>
                                <div class="bg-grey-lighten-5 pa-3 rounded border text-caption font-mono"
                                    style="white-space: pre-wrap; max-height: 200px; overflow-y: auto;">
                                    {{ msg.raw_content }}
                                </div>
                            </v-card-text>

                            <v-card-actions class="pa-4 pt-0">
                                <v-btn variant="text" color="grey"
                                    @click="emit('dismissTraining', msg.id)">Dismiss</v-btn>
                                <v-spacer></v-spacer>
                                <v-btn color="warning" variant="elevated" @click="emit('startLabeling', msg)">Label
                                    Fields</v-btn>
                            </v-card-actions>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-if="trainingPagination.total === 0" class="text-center py-12">
                    <v-icon size="64" color="success" class="mb-4">mdi-shield-check</v-icon>
                    <h3 class="text-h5 font-weight-bold">All Clear!</h3>
                    <p class="text-medium-emphasis">No unparsed messages waiting for training.</p>
                </div>

                <!-- Training Pagination -->
                <v-row v-if="trainingPagination.total > 0" class="mt-4 align-center">
                    <v-col cols="12" md="6" class="text-caption text-medium-emphasis">
                        Showing {{ trainingPagination.skip + 1 }}-{{ Math.min(trainingPagination.skip +
                            trainingPagination.limit,
                            trainingPagination.total) }} of {{ trainingPagination.total }}
                    </v-col>
                    <v-col cols="12" md="6" class="d-flex justify-end align-center gap-2">
                        <span class="text-caption mr-2">Rows per page:</span>
                        <v-select :model-value="trainingPagination.limit"
                            @update:model-value="handleTrainingPaginationLimitChange($event)" :items="[12, 24, 60]"
                            density="compact" variant="outlined" hide-details class="d-inline-block"
                            style="width: 85px"></v-select>
                        <v-btn size="small" variant="text" :disabled="trainingPagination.skip === 0"
                            @click="handleTrainingPaginationPrev">Prev</v-btn>
                        <v-btn size="small" variant="text"
                            :disabled="trainingPagination.skip + trainingPagination.limit >= trainingPagination.total"
                            @click="handleTrainingPaginationNext">Next</v-btn>
                    </v-col>
                </v-row>
            </v-window-item>
        </v-window>
    </div>
</template>

<style scoped>
.glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.12);
    transition: all 0.2s ease;
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

.gap-2 {
    gap: 0.5rem;
}
</style>
