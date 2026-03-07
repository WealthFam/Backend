<template>
    <v-dialog :model-value="modelValue" @update:model-value="handleClose" max-width="650"
        transition="dialog-bottom-transition" persistent>
        <v-card rounded="xl" class="bg-surface elevation-24 overflow-hidden modal-height">
            <!-- Header -->
            <div class="bg-background px-6 py-4 d-flex flex-column border-b">
                <div class="d-flex justify-space-between align-start mb-4">
                    <div>
                        <div class="text-overline font-weight-black text-primary mb-0 letter-spacing-2"
                            style="font-size: 0.65rem;">
                            {{ isEditing ? 'Edit Group' : 'New Group' }}
                        </div>
                        <h2 class="text-h5 font-weight-black">
                            {{ isEditing ? 'Refine Details' : 'Create Bucket' }}
                        </h2>
                    </div>
                    <v-btn icon variant="tonal" @click="handleClose" color="primary" rounded="pill" size="small">
                        <X :size="18" />
                    </v-btn>
                </div>

                <!-- Navigation Tabs -->
                <div class="premium-pill-tabs d-flex overflow-x-auto w-100">
                    <v-tabs v-model="activeTab" color="primary" density="comfortable" hide-slider show-arrows
                        class="rounded-xl flex-grow-1">
                        <v-tab value="details" class="premium-tab flex-grow-1" rounded="xl">
                            <div class="d-flex align-center ga-2">
                                <InfoIcon :size="16" />
                                <span>Details</span>
                            </div>
                        </v-tab>
                        <v-tab value="transactions" class="premium-tab flex-grow-1" rounded="xl"
                            :disabled="!dateRange || !dateRange[0] || !dateRange[1]">
                            <div class="d-flex align-center ga-2">
                                <ListIcon :size="16" />
                                <span>Transactions</span>
                                <v-chip v-if="selectedTransactionIds.length" size="x-small" color="primary"
                                    class="ml-1 font-weight-black">
                                    {{ selectedTransactionIds.length }}
                                </v-chip>
                            </div>
                        </v-tab>
                    </v-tabs>
                </div>
            </div>

            <v-card-text class="pa-0 flex-grow-1 overflow-hidden d-flex flex-column" style="min-height: 0;">
                <v-form @submit.prevent="handleSubmit" class="h-100 d-flex flex-column overflow-hidden"
                    style="min-height: 0;">
                    <v-window v-model="activeTab" class="flex-grow-1 overflow-hidden d-flex flex-column"
                        style="min-height: 0; width: 100%;" :touch="false" :transition="false"
                        :reverse-transition="false">
                        <v-window-item value="details"
                            class="h-100 w-100 flex-column overflow-y-auto custom-scrollbar bg-surface pa-5">
                            <div class="d-flex flex-column ga-3 pb-6">
                                <!-- Name and Icon Section -->
                                <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                    <div class="d-flex align-center ga-4 mb-3">
                                        <v-menu :close-on-content-click="false" location="bottom">
                                            <template v-slot:activator="{ props }">
                                                <v-avatar size="56" v-bind="props"
                                                    :style="{ background: generateColor(form.name).bg }" variant="flat"
                                                    class="elevation-2 border cursor-pointer">
                                                    <span class="text-h4">{{ form.icon || '?' }}</span>
                                                    <v-overlay activator="parent" location="center"
                                                        class="align-center justify-center" opacity="0.1">
                                                        <Pencil :size="16" class="text-white" />
                                                    </v-overlay>
                                                </v-avatar>
                                            </template>
                                            <v-card rounded="xl" class="pa-4 bg-surface elevation-12" min-width="300">
                                                <div class="text-subtitle-2 font-weight-black mb-3 px-2">Choose an
                                                    Identity</div>
                                                <div class="emoji-grid">
                                                    <v-btn v-for="emoji in emojis" :key="emoji" icon variant="tonal"
                                                        size="small"
                                                        :color="form.icon === emoji ? 'primary' : 'medium-emphasis'"
                                                        class="emoji-btn-mini" @click="form.icon = emoji">
                                                        <span>{{ emoji }}</span>
                                                    </v-btn>
                                                </div>
                                            </v-card>
                                        </v-menu>

                                        <div class="flex-grow-1">
                                            <v-text-field v-model="form.name" label="Bucket Name"
                                                placeholder="e.g. Thailand Trip" variant="underlined" density="compact"
                                                hide-details class="font-weight-black text-h6" autofocus>
                                            </v-text-field>
                                        </div>
                                    </div>

                                    <v-textarea v-model="form.description" label="Notes" rows="1" auto-grow
                                        variant="solo-filled" flat density="compact" hide-details rounded="lg"
                                        class="text-body-2 mb-3" bg-color="surface"
                                        placeholder="What is this bucket for?" />

                                    <v-divider class="mb-3 opacity-5" />

                                    <div class="d-flex justify-space-between align-center">
                                        <div class="d-flex align-center ga-2">
                                            <Activity :size="16" class="text-primary" />
                                            <span
                                                class="text-subtitle-2 font-weight-black text-uppercase letter-spacing-1">Active
                                                Status</span>
                                        </div>
                                        <v-switch v-model="form.is_active" color="success" hide-details
                                            density="compact" inset>
                                            <template v-slot:label>
                                                <span class="text-caption font-weight-black ml-1">
                                                    {{ form.is_active ? 'ENABLED' : 'DISABLED' }}
                                                </span>
                                            </template>
                                        </v-switch>
                                    </div>
                                </v-card>

                                <!-- Financial Target Section -->
                                <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                    <div class="d-flex align-center justify-space-between mb-2">
                                        <div class="d-flex align-center ga-2">
                                            <Wallet :size="16" class="text-primary" />
                                            <div class="text-subtitle-2 font-weight-black text-uppercase letter-spacing-1"
                                                style="font-size: 0.7rem !important;">
                                                Financial Target</div>
                                        </div>
                                        <v-chip v-if="form.budget > 0" size="x-small"
                                            :color="selectedTransactionsTotal > form.budget ? 'error' : 'success'"
                                            variant="tonal" class="font-weight-black">
                                            {{ Math.round((selectedTransactionsTotal / form.budget) * 100)
                                            }}% Consumed
                                        </v-chip>
                                    </div>

                                    <v-text-field v-model.number="form.budget" label="Budget Limit" type="number"
                                        prefix="₹" variant="solo-filled" flat density="compact" rounded="lg"
                                        class="font-weight-black" bg-color="surface" color="primary" hide-details
                                        placeholder="0.00">
                                    </v-text-field>

                                    <div v-if="form.budget > 0" class="mt-3">
                                        <v-progress-linear
                                            :model-value="(selectedTransactionsTotal / form.budget) * 100"
                                            :color="selectedTransactionsTotal > form.budget ? 'error' : 'primary'"
                                            height="8" rounded="pill" class="mb-1"></v-progress-linear>
                                        <div class="d-flex justify-space-between text-tiny font-weight-bold opacity-70">
                                            <span>{{ formatAmount(selectedTransactionsTotal) }} used</span>
                                            <span>{{ formatAmount(Math.max(0, form.budget -
                                                selectedTransactionsTotal)) }} left</span>
                                        </div>
                                    </div>
                                </v-card>

                                <!-- Tracking Period Section -->
                                <v-card variant="flat" rounded="xl" class="bg-background border-thin pa-4">
                                    <div class="d-flex align-center ga-2 mb-2">
                                        <Calendar :size="16" class="text-primary" />
                                        <div class="text-subtitle-2 font-weight-black text-uppercase letter-spacing-1"
                                            style="font-size: 0.7rem !important;">
                                            Tracking Period</div>
                                    </div>
                                    <VueDatePicker v-model="dateRange" range :dark="isDark" auto-apply
                                        :enable-time-picker="false" placeholder="Select Date Range" :teleport="true">
                                        <template #trigger>
                                            <v-text-field :model-value="dateRangeDisplay" label="Duration"
                                                variant="solo-filled" flat density="compact" rounded="lg"
                                                class="font-weight-black" readonly bg-color="surface" color="primary"
                                                prepend-inner-icon="mdi-calendar" hide-details>
                                            </v-text-field>
                                        </template>
                                    </VueDatePicker>
                                </v-card>
                            </div>
                        </v-window-item>

                        <!-- TAB: TRANSACTIONS -->
                        <v-window-item value="transactions"
                            class="h-100 w-100 flex-column bg-background overflow-hidden">
                            <!-- Transactions Header -->
                            <div
                                class="px-6 py-4 border-b bg-surface d-flex align-center justify-space-between flex-shrink-0 z-10">
                                <div>
                                    <div class="d-flex align-center ga-2">
                                        <Activity :size="18" class="text-primary" />
                                        <h3 class="text-subtitle-2 font-weight-black text-uppercase">Link
                                            Transactions
                                        </h3>
                                    </div>
                                    <div class="text-tiny font-weight-bold opacity-60 mt-0.5">
                                        {{ pinnedTxns.length }} linked • {{ unpinnedTxns.length }} available
                                    </div>
                                </div>
                                <v-btn v-if="dateRange" color="primary" variant="tonal" size="small" rounded="pill"
                                    class="font-weight-black" :loading="loadingTransactions"
                                    @click="fetchEligibleTransactions">
                                    Refresh
                                </v-btn>
                            </div>

                            <div class="flex-grow-1 overflow-hidden d-flex flex-column" style="min-height: 0;">
                                <template v-if="transactionsLoaded">
                                    <div
                                        class="px-6 py-2 bg-background border-b d-flex align-center ga-2 flex-shrink-0 z-10">
                                        <v-text-field v-model="txnSearch" placeholder="Search..." variant="plain"
                                            density="compact" hide-details class="text-body-2" style="max-width: 40%;">
                                            <template v-slot:prepend-inner>
                                                <Search :size="16" class="mr-2" />
                                            </template>
                                        </v-text-field>

                                        <v-select v-model="accountFilter" :items="accounts" item-title="name"
                                            item-value="id" placeholder="All Accounts" variant="plain" density="compact"
                                            hide-details class="text-body-2 flex-grow-1" clearable>
                                        </v-select>
                                    </div>

                                    <div class="flex-grow-1 overflow-y-auto custom-scrollbar bg-surface pb-16"
                                        id="txn-list-container">
                                        <!-- Pinned / Selected Section -->
                                        <div v-if="pinnedTxns.length > 0" class="bg-primary-lighten-5 py-2">
                                            <div class="px-6 py-2 d-flex align-center ga-2">
                                                <CheckCircle2 :size="12" class="text-primary" />
                                                <span
                                                    class="text-tiny font-weight-black text-primary text-uppercase letter-spacing-1">Linked
                                                    Transactions ({{ pinnedTxns.length }})</span>
                                            </div>
                                            <v-list density="comfortable" class="pa-0 bg-transparent">
                                                <v-list-item v-for="txn in pinnedTxns" :key="txn.id"
                                                    @click="toggleTxn(txn.id)"
                                                    class="py-2 px-4 txn-card-premium selected-txn">
                                                    <template v-slot:prepend>
                                                        <v-checkbox-btn :model-value="true" color="primary" hide-details
                                                            density="compact" />
                                                    </template>
                                                    <div
                                                        class="ml-3 d-flex align-center justify-space-between flex-grow-1">
                                                        <div class="d-flex align-center ga-3 overflow-hidden">
                                                            <v-avatar size="20"
                                                                :color="getCategoryDisplay(txn.category).color + '20'"
                                                                rounded="sm" class="flex-shrink-0">
                                                                <span class="text-caption"
                                                                    style="font-size: 0.7rem !important;">{{
                                                                        getCategoryDisplay(txn.category).icon }}</span>
                                                            </v-avatar>
                                                            <div class="d-flex flex-column" style="min-width: 0;">
                                                                <span
                                                                    class="text-subtitle-2 font-weight-black text-truncate">
                                                                    {{ txn.description || txn.recipient || 'Unnamed'
                                                                    }}
                                                                </span>
                                                                <div class="d-flex align-center ga-2">
                                                                    <span
                                                                        class="text-tiny font-weight-bold opacity-70">{{
                                                                            getAccountName(txn.account_id) }}</span>
                                                                    <span class="text-tiny opacity-50">• {{
                                                                        formatDateShort(txn.date) }}</span>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <span
                                                            class="text-subtitle-2 font-weight-black ml-2 flex-shrink-0"
                                                            :class="txn.amount > 0 ? 'text-success' : 'text-error'">
                                                            {{ formatAmount(txn.amount) }}
                                                        </span>
                                                    </div>
                                                </v-list-item>
                                            </v-list>
                                            <v-divider class="my-2 opacity-10" />
                                        </div>

                                        <!-- Results / Available Section -->
                                        <div class="px-6 py-2 d-flex align-center ga-2 mt-2">
                                            <Inbox :size="12" class="opacity-50" />
                                            <span
                                                class="text-tiny font-weight-black text-medium-emphasis text-uppercase letter-spacing-1">Available
                                                Results</span>
                                        </div>
                                        <v-list density="comfortable" class="pa-0 bg-transparent">
                                            <v-list-item v-for="txn in unpinnedTxns" :key="txn.id"
                                                @click="toggleTxn(txn.id)" class="py-2 px-4 txn-card-premium">
                                                <template v-slot:prepend>
                                                    <v-checkbox-btn :model-value="false" color="primary" hide-details
                                                        density="compact" />
                                                </template>
                                                <div class="ml-3 d-flex align-center justify-space-between flex-grow-1">
                                                    <div class="d-flex align-center ga-3 overflow-hidden">
                                                        <v-avatar size="20"
                                                            :color="getCategoryDisplay(txn.category).color + '20'"
                                                            rounded="sm" class="flex-shrink-0">
                                                            <span class="text-caption"
                                                                style="font-size: 0.7rem !important;">{{
                                                                    getCategoryDisplay(txn.category).icon }}</span>
                                                        </v-avatar>
                                                        <div class="d-flex flex-column" style="min-width: 0;">
                                                            <span
                                                                class="text-subtitle-2 font-weight-black text-truncate">
                                                                {{ txn.description || txn.recipient || 'Unnamed' }}
                                                            </span>
                                                            <div class="d-flex align-center ga-2">
                                                                <span class="text-tiny font-weight-bold opacity-70">{{
                                                                    getAccountName(txn.account_id)
                                                                    }}</span>
                                                                <span class="text-tiny opacity-50">• {{
                                                                    formatDateShort(txn.date) }}</span>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <span class="text-subtitle-2 font-weight-black ml-2 flex-shrink-0"
                                                        :class="txn.amount > 0 ? 'text-success' : 'text-error'">
                                                        {{ formatAmount(txn.amount) }}
                                                    </span>
                                                </div>
                                            </v-list-item>

                                            <!-- Load More Pagination -->
                                            <v-list-item v-if="displayLimit < (filteredTxns.length - pinnedTxns.length)"
                                                class="text-center py-6">
                                                <v-btn variant="tonal" size="small" color="primary" rounded="pill"
                                                    class="px-8 font-weight-black" @click="displayLimit += 100">
                                                    Load More
                                                </v-btn>
                                            </v-list-item>

                                            <v-list-item v-if="filteredTxns.length === 0" class="text-center py-16">
                                                <div class="d-flex flex-column align-center opacity-30 ga-2">
                                                    <Search :size="32" />
                                                    <span class="font-weight-bold text-caption">No matching
                                                        items</span>
                                                </div>
                                            </v-list-item>

                                            <!-- extremely generous padding to ensure bottom transactions are reachable -->
                                            <div class="py-16 my-8"></div>
                                        </v-list>
                                    </div>
                                </template>

                                <template v-else-if="!loadingTransactions">
                                    <div
                                        class="h-100 d-flex flex-column align-center justify-center pa-12 text-center ga-6">
                                        <v-avatar color="primary" variant="tonal" size="80">
                                            <Activity :size="40" class="text-primary" />
                                        </v-avatar>
                                        <div>
                                            <h3 class="text-h6 font-weight-black text-primary mb-2">Track Your
                                                Spending
                                            </h3>
                                            <p class="text-body-2 font-weight-medium text-medium-emphasis mx-auto"
                                                style="max-width: 300px">
                                                Select a date range on the left and fetch transactions to start
                                                linking
                                                them
                                                to this bucket.
                                            </p>
                                        </div>
                                    </div>
                                </template>

                                <template v-else>
                                    <div class="h-100 d-flex align-center justify-center">
                                        <v-progress-circular indeterminate color="primary" size="48" />
                                    </div>
                                </template>
                            </div>
                        </v-window-item>
                    </v-window>
                </v-form>
            </v-card-text>

            <!-- Actions -->
            <v-card-actions class="px-6 py-4 bg-surface border-t z-10">
                <v-btn variant="text" @click="handleClose" height="44" rounded="xl"
                    class="px-6 font-weight-black text-none text-medium-emphasis">
                    Discard
                </v-btn>
                <v-spacer />
                <v-btn color="primary" variant="flat" rounded="xl" height="44"
                    class="px-8 font-weight-black text-none elevation-8" @click="handleSubmit" :loading="saving">
                    {{ isEditing ? 'Update Group' : 'Create Group' }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { X, Pencil, Activity, Wallet, Calendar, Search, CheckCircle2, Inbox, Info as InfoIcon, List as ListIcon } from 'lucide-vue-next'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useNotificationStore } from '@/stores/notification'
import { useFinanceStore } from '@/stores/finance'
import { useTheme } from 'vuetify'

const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)

const props = defineProps<{
    modelValue: boolean
    isEditing: boolean
    groupData: any | null
}>()

const emit = defineEmits(['update:modelValue', 'saved'])

const notify = useNotificationStore()
const financeStore = useFinanceStore()
const { formatAmount } = useCurrency()

const activeTab = ref<'details' | 'transactions'>('details')
const saving = ref(false)
const form = ref({
    name: '',
    description: '',
    is_active: true,
    budget: 0,
    start_date: '',
    end_date: '',
    icon: ''
})

const dateRange = ref<[Date, Date] | null>(null)
const eligibleTransactions = ref<any[]>([])
const selectedTransactionIds = ref<string[]>([])
const loadingTransactions = ref(false)
const transactionsLoaded = ref(false)
const txnSearch = ref('')
const accountFilter = ref<string | null>(null)
const accounts = ref<any[]>([])
const displayLimit = ref(50)

const emojis = ['✈️', '🏠', '🍔', '🛒', '💊', '🎓', '🎮', '🎁', '💸', '💼', '🚗', '👶', '🏖️', '🍽️', '👗', '🚲', '🐶', '⚽', '💻', '🎨']

const dateRangeDisplay = computed(() => {
    if (form.value.start_date && form.value.end_date) {
        return `${formatDateShort(form.value.start_date)} - ${formatDateShort(form.value.end_date)}`
    }
    return ''
})

const filteredTxns = computed(() => {
    let result = eligibleTransactions.value

    if (txnSearch.value) {
        const q = txnSearch.value.toLowerCase()
        result = result.filter(t =>
            (t.description && t.description.toLowerCase().includes(q)) ||
            (t.recipient && t.recipient.toLowerCase().includes(q)) ||
            (t.category && t.category.toLowerCase().includes(q))
        )
    }

    // Filter out hidden and transfers
    result = result.filter(t => !t.exclude_from_reports && !t.is_transfer)

    if (accountFilter.value) {
        result = result.filter(t => t.account_id === accountFilter.value)
    }

    return result
})

// Pinned transactions (selected ones)
const pinnedTxns = computed(() => {
    return filteredTxns.value.filter(t => selectedTransactionIds.value.includes(t.id))
})

// Unpinned transactions (not selected)
const unpinnedTxns = computed(() => {
    const unpinned = filteredTxns.value.filter(t => !selectedTransactionIds.value.includes(t.id))
    return unpinned.slice(0, displayLimit.value)
})

const selectedTransactionsTotal = computed(() => {
    return eligibleTransactions.value
        .filter(t => selectedTransactionIds.value.includes(t.id) && (t.amount || 0) < 0)
        .reduce((sum, t) => sum + Math.abs(t.amount || 0), 0)
})

const handleClose = () => {
    emit('update:modelValue', false)
}

// Initialize form when modal opens or groupData changes
watch(() => props.modelValue, (newVal) => {
    if (newVal) {
        activeTab.value = 'details'
        if (props.isEditing && props.groupData) {
            form.value = {
                name: props.groupData.name,
                description: props.groupData.description || '',
                is_active: props.groupData.is_active,
                budget: props.groupData.budget || 0,
                start_date: props.groupData.start_date?.split('T')[0] || '',
                end_date: props.groupData.end_date?.split('T')[0] || '',
                icon: props.groupData.icon || ''
            }
            if (form.value.start_date && form.value.end_date) {
                initializing.value = true
                const [sy, sm, sd] = form.value.start_date.split('-').map(Number)
                const [ey, em, ed] = form.value.end_date.split('-').map(Number)
                dateRange.value = [new Date(sy, sm - 1, sd), new Date(ey, em - 1, ed)]
                initializing.value = false
                fetchExistingLinks()
            }
        } else {
            resetForm()
        }
    }
})

// Reset display limit when search or filter changes
watch([txnSearch, accountFilter], () => {
    displayLimit.value = 50
})

const initializing = ref(false)

watch(dateRange, (newRange) => {
    if (!newRange || !newRange[0] || !newRange[1]) {
        form.value.start_date = ''
        form.value.end_date = ''
        checkDateStatus()
        return
    }
    form.value.start_date = newRange[0].toISOString().split('T')[0]
    form.value.end_date = newRange[1].toISOString().split('T')[0]
    checkDateStatus()
    if (!initializing.value) {
        fetchEligibleTransactions()
    }
})

const resetForm = () => {
    form.value = {
        name: '',
        description: '',
        is_active: true,
        budget: 0,
        start_date: '',
        end_date: '',
        icon: ''
    }
    dateRange.value = null
    selectedTransactionIds.value = []
    eligibleTransactions.value = []
    transactionsLoaded.value = false
    activeTab.value = 'details'
}

const checkDateStatus = () => {
    if (!form.value.end_date) return
    const endDate = new Date(form.value.end_date)
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    form.value.is_active = endDate >= today
}

const fetchEligibleTransactions = async () => {
    if (!form.value.start_date || !form.value.end_date) return
    loadingTransactions.value = true
    try {
        const res = await financeApi.getTransactions(
            undefined, 1, 2000,
            form.value.start_date,
            form.value.end_date,
            undefined, undefined, 'date', 'desc',
            financeStore.selectedMemberId || undefined
        )
        eligibleTransactions.value = res.data.items || []

        // Auto-select previously pinned transactions for THIS group if edited
        if (props.isEditing && props.groupData?.id) {
            const groupTxns = (res.data.items || []).filter((t: any) => t.expense_group_id === props.groupData.id)
            groupTxns.forEach((t: any) => {
                if (!selectedTransactionIds.value.includes(t.id)) {
                    selectedTransactionIds.value.push(t.id)
                }
            })
        }

        transactionsLoaded.value = true
    } catch (e) {
        notify.error("Failed to fetch transactions")
    } finally {
        loadingTransactions.value = false
    }
}

const fetchExistingLinks = async () => {
    if (!props.groupData?.id) return
    loadingTransactions.value = true
    try {
        const res = await financeApi.getTransactions(
            undefined, 1, 2000,
            form.value.start_date,
            form.value.end_date,
            undefined, undefined, 'date', 'desc',
            financeStore.selectedMemberId || undefined
        )
        eligibleTransactions.value = res.data.items || []
        selectedTransactionIds.value = res.data.items
            .filter((t: any) => t.expense_group_id === props.groupData.id)
            .map((t: any) => t.id)
        transactionsLoaded.value = true
    } catch (e) {
        console.error("Failed to fetch linked transactions", e)
    } finally {
        loadingTransactions.value = false
    }
}

const toggleTxn = (id: string) => {
    const idx = selectedTransactionIds.value.indexOf(id)
    if (idx === -1) selectedTransactionIds.value.push(id)
    else selectedTransactionIds.value.splice(idx, 1)
}

const handleSubmit = async () => {
    if (!form.value.name || !form.value.start_date || !form.value.end_date) {
        notify.error("Name and dates are required")
        return
    }

    saving.value = true
    try {
        let groupId = props.isEditing ? props.groupData.id : null

        if (props.isEditing && groupId) {
            await financeApi.updateExpenseGroup(groupId, form.value)
        } else {
            const res = await financeApi.createExpenseGroup(form.value)
            groupId = res.data.id
        }

        if (groupId) {
            await financeApi.linkExpenseGroupTransactions(groupId, selectedTransactionIds.value)
        }

        notify.success(`Group ${props.isEditing ? 'updated' : 'created'} successfully`)
        emit('saved')
        emit('update:modelValue', false)
    } catch (e) {
        notify.error("Failed to save group")
    } finally {
        saving.value = false
    }
}

function getAccountName(id: string) {
    const acc = accounts.value.find(a => a.id === id)
    return acc ? acc.name : 'Unknown'
}

function getCategoryDisplay(name: string) {
    if (!name || name === 'Uncategorized') return { icon: '🏷️', color: '#9ca3af' }
    const cat = financeStore.categories.flatMap(c => [c, ...(c.subcategories || [])]).find(c => c.name === name)
    return {
        icon: cat?.icon || '🏷️',
        color: cat?.color || '#3B82F6'
    }
}

function formatDateShort(dateStr: string) {
    if (!dateStr) return '-'
    const parts = dateStr.split('T')[0].split('-').map(Number)
    return new Date(parts[0], parts[1] - 1, parts[2]).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const generateColor = (name: string) => {
    const colors = ['#eff6ff', '#f0fdf4', '#fef2f2', '#fff7ed', '#f0f9ff', '#faf5ff']
    const textColors = ['#1d4ed8', '#15803d', '#b91c1c', '#c2410c', '#0369a1', '#7e22ce']
    let hash = 0
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
    const index = Math.abs(hash) % colors.length
    return { bg: colors[index], text: textColors[index] }
}

const fetchAccounts = async () => {
    try {
        const res = await financeApi.getAccounts()
        accounts.value = res.data
    } catch (e) {
        console.error("Failed to fetch accounts", e)
    }
}

onMounted(() => {
    fetchAccounts()
})
</script>

<style scoped>
.txn-card-premium {
    transition: all 0.2s ease;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.txn-card-premium:hover {
    background: rgba(var(--v-theme-primary), 0.05);
}

.selected-txn {
    background: rgba(var(--v-theme-primary), 0.08) !important;
}

.letter-spacing-1 {
    letter-spacing: 0.1em;
}

.letter-spacing-2 {
    letter-spacing: 0.2em;
}

.bg-primary-lighten-5 {
    background: rgba(var(--v-theme-primary), 0.03);
}

.bg-surface {
    background: rgb(var(--v-theme-surface));
}

.bg-background {
    background: rgb(var(--v-theme-background));
}

.modal-height {
    height: 90vh;
    max-height: 850px;
    display: flex;
    flex-direction: column;
}

:deep(.v-window__container) {
    height: 100%;
    min-height: 0;
}

:deep(.v-window-item.v-window-item--active) {
    display: flex !important;
    flex-direction: column;
    height: 100%;
    width: 100%;
}

.custom-scrollbar {
    overflow-y: auto !important;
    padding-bottom: 24px !important;
}

.custom-scrollbar::-webkit-scrollbar {
    width: 6px;
}

.custom-scrollbar::-webkit-scrollbar-track {
    background: transparent;
}

.custom-scrollbar::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 10px;
}

.custom-scrollbar::-webkit-scrollbar-thumb:hover {
    background: rgba(var(--v-theme-primary), 0.3);
}

.emoji-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 8px;
    padding: 8px;
}

.emoji-btn-mini {
    width: 40px !important;
    height: 40px !important;
    font-size: 1.2rem !important;
}

.text-tiny {
    font-size: 0.75rem;
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
}

.premium-tab.v-tab--selected {
    background: rgb(var(--v-theme-primary));
    color: white !important;
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

:deep(.dp__main) {
    font-family: inherit;
}

:deep(.dp__input) {
    border-radius: 12px;
    height: 48px;
    border-color: rgba(var(--v-border-color), 0.2);
    font-weight: 600;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}
</style>
