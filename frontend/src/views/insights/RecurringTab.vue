<template>
    <div class="recurring-content px-0 pb-6">
        <div class="d-flex justify-end mb-6">
            <v-btn color="primary" @click="showAddModal = true" rounded="pill" height="44"
                class="text-none font-weight-black px-6" elevation="4">
                <template v-slot:prepend>
                    <Plus :size="18" stroke-width="3" />
                </template>
                Add Subscription
            </v-btn>
        </div>

        <!-- Smart Suggestions Section -->
        <div v-if="suggestions.length > 0" class="suggestions-section mb-10 mt-2">
            <div class="d-flex align-center mb-4">
                <div class="icon-orb mr-3"
                    style="width: 32px; height: 32px; background: rgba(var(--v-theme-primary), 0.1)">
                    <Sparkles :size="16" class="text-primary" />
                </div>
                <div>
                    <h3 class="text-subtitle-1 font-weight-black">Smart Suggestions</h3>
                    <p class="text-caption font-weight-bold opacity-60">Detected recurring patterns from your history
                    </p>
                </div>
            </div>

            <div class="suggestions-slider d-flex gap-4 overflow-x-auto pb-4 px-1" style="scrollbar-width: none;">
                <v-card v-for="(suggestion, idx) in suggestions" :key="idx" rounded="xl"
                    class="suggestion-card pa-4 border-premium flex-shrink-0" width="300" elevation="0">
                    <div class="d-flex justify-space-between align-start mb-3">
                        <v-avatar color="primary" variant="tonal" size="40" rounded="lg">
                            <component :is="getCategoryLucideIcon(suggestion.category)" :size="20" />
                        </v-avatar>
                        <v-chip size="x-small" color="success" class="font-weight-black" variant="tonal">
                            {{ (suggestion.confidence * 100).toFixed(0) }}% Match
                        </v-chip>
                    </div>

                    <div class="text-subtitle-2 font-weight-black mb-1 text-truncate">{{ suggestion.name }}</div>
                    <div class="text-h6 font-weight-black mb-3">{{ formatAmount(suggestion.amount) }}<span
                            class="text-caption opacity-60 ml-1">/ {{ suggestion.frequency.toLowerCase() }}</span></div>

                    <p class="text-caption opacity-70 mb-4 line-clamp-2" style="height: 32px;">{{ suggestion.reason }}
                    </p>

                    <v-btn block color="primary" variant="flat" size="small" rounded="lg"
                        class="text-none font-weight-black" @click="approveSuggestion(suggestion)">
                        Add Subscription
                    </v-btn>
                </v-card>
            </div>
        </div>
        <v-row v-if="store.recurringTransactions.length > 0">
            <v-col v-for="rec in store.recurringTransactions" :key="rec.id" cols="12" md="6" lg="4">
                <v-card rounded="xl" class="recurring-glass-card hover-elevate group">
                    <div class="pa-5 d-flex align-center justify-space-between">
                        <div class="d-flex align-center">
                            <v-avatar color="surface-variant" size="56" rounded="lg" class="mr-4 elevation-2">
                                <component :is="getCategoryLucideIcon(rec.category)" :size="24" class="text-primary" />
                            </v-avatar>
                            <div>
                                <h3 class="text-subtitle-1 font-weight-black mb-0">{{ rec.name }}</h3>
                                <p class="text-caption text-medium-emphasis font-weight-bold">
                                    {{ rec.frequency }} • Next: {{ new Date(rec.next_run_date).toLocaleDateString() }}
                                </p>
                                <v-chip v-if="rec.exclude_from_reports" color="error" size="x-small" label
                                    class="mt-1 font-weight-bold">
                                    EXCLUDED
                                </v-chip>
                            </div>
                        </div>
                        <div class="text-right">
                            <div class="text-h6 font-weight-black">{{ formatAmount(rec.amount) }}</div>
                            <v-btn variant="text" size="small" color="error" icon
                                class="opacity-0 group-hover-opacity-100 transition-all"
                                @click="deleteRecurrence(rec.id)">
                                <Trash2 :size="18" />
                            </v-btn>
                        </div>
                    </div>
                </v-card>
            </v-col>
        </v-row>
        <div v-else class="text-center py-16 empty-glass container">
            <CalendarClock :size="80" class="text-medium-emphasis mb-4 mx-auto" stroke-width="1.5" />
            <h3 class="text-h5 font-weight-black">No Active Subscriptions</h3>
            <p class="text-medium-emphasis mt-2">Manage your recurring bills and subscriptions here for better
                forecasting.</p>
            <v-btn color="primary" class="mt-6 text-none px-8" rounded="pill" height="48" @click="showAddModal = true">
                <template v-slot:prepend>
                    <Plus :size="18" stroke-width="3" />
                </template>
                Set Up First Subscription
            </v-btn>
        </div>

        <!-- Add Recurrence Modal (Integrated) -->
        <v-dialog v-model="showAddModal" max-width="500" persistent transition="dialog-bottom-transition">
            <v-card rounded="xl" class="glass-modal-card">
                <v-toolbar color="transparent" class="px-4">
                    <v-toolbar-title class="font-weight-black">New Subscription</v-toolbar-title>
                    <v-spacer />
                    <v-btn variant="text" @click="showAddModal = false" icon>
                        <X :size="20" />
                    </v-btn>
                </v-toolbar>

                <v-divider />

                <v-card-text class="pa-6">
                    <v-row dense>
                        <v-col cols="12">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">Subscription Name</label>
                            <v-text-field v-model="newRecurrence.name" placeholder="Netflix, Rent, Salary..."
                                variant="outlined" density="comfortable" flat rounded="lg">
                                <template v-slot:prepend-inner>
                                    <CreditCard :size="18" class="text-primary mr-2" />
                                </template>
                            </v-text-field>
                        </v-col>

                        <v-col cols="6">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">Amount</label>
                            <v-text-field v-model="newRecurrence.amount" type="number" prefix="₹" variant="outlined"
                                density="comfortable" flat rounded="lg" />
                        </v-col>

                        <v-col cols="6">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">Frequency</label>
                            <v-select v-model="newRecurrence.frequency" :items="frequencyOptions" variant="outlined"
                                density="comfortable" flat rounded="lg" menu-icon="">
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary opacity-70" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="6">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">First Payment</label>
                            <v-text-field v-model="newRecurrence.start_date" type="date" variant="outlined"
                                density="comfortable" flat rounded="lg" />
                        </v-col>

                        <v-col cols="6">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">Source Account</label>
                            <v-select v-model="newRecurrence.account_id"
                                :items="store.accounts.map(a => ({ title: a.name, value: a.id }))" variant="outlined"
                                density="comfortable" hide-details flat rounded="lg" class="premium-modal-select"
                                menu-icon="" style="background: rgba(var(--v-theme-surface), 0.7);">
                                <template v-slot:prepend-inner>
                                    <Wallet :size="18" class="text-primary mr-2" />
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary opacity-70" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12">
                            <label class="text-caption font-weight-bold text-uppercase ml-1">Category</label>
                            <v-select v-model="newRecurrence.category"
                                :items="store.categories.map(c => ({ title: c.name, value: c.name }))"
                                variant="outlined" density="comfortable" hide-details flat rounded="lg"
                                class="premium-modal-select" menu-icon=""
                                style="background: rgba(var(--v-theme-surface), 0.7);">
                                <template v-slot:prepend-inner>
                                    <component :is="getCategoryLucideIcon(newRecurrence.category)" :size="18"
                                        class="text-primary mr-2" />
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary opacity-70" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12">
                            <v-switch v-model="newRecurrence.exclude_from_reports" label="Protect from reports"
                                color="error" inset hide-details class="mt-2" />
                        </v-col>
                    </v-row>
                </v-card-text>

                <v-divider />

                <v-card-actions class="pa-6">
                    <v-spacer />
                    <v-btn variant="text" rounded="lg" class="px-6 text-none font-weight-bold"
                        @click="showAddModal = false">Cancel</v-btn>
                    <v-btn color="primary" variant="flat" rounded="lg" class="px-8 text-none font-weight-bold"
                        @click="saveRecurrence">Start Subscription</v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, defineExpose, onMounted } from 'vue'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import { useCurrency } from '@/composables/useCurrency'
import { financeApi } from '@/api/client'
import { useConfirmStore } from '@/stores/confirm'
import { Plus, X, ChevronDown, CalendarClock, Trash2, Wallet, CreditCard, Sparkles } from 'lucide-vue-next'
import { getCategoryLucideIcon } from '@/utils/iconMapping'

const store = useFinanceStore()
const authStore = useAuthStore()
const confirmDialog = useConfirmStore()
const { formatAmount } = useCurrency()

const showAddModal = ref(false)
const suggestions = ref<any[]>([])
const loadingSuggestions = ref(false)

onMounted(() => {
    fetchSuggestions()
})

async function fetchSuggestions() {
    loadingSuggestions.value = true
    try {
        const res = await financeApi.getRecurringSuggestions()
        suggestions.value = res.data
    } catch (e) {
        console.error("Failed to fetch recurring suggestions", e)
    } finally {
        loadingSuggestions.value = false
    }
}

async function approveSuggestion(suggestion: any) {
    try {
        await financeApi.createRecurringTransaction({
            name: suggestion.name,
            amount: suggestion.amount,
            category: suggestion.category,
            account_id: suggestion.account_id,
            frequency: suggestion.frequency,
            start_date: suggestion.last_date,
            next_run_date: new Date().toISOString(), // Default to today or next expected
            type: 'DEBIT',
            is_active: true,
            exclude_from_reports: false
        })
        // Refresh everything
        await store.fetchRecurring(authStore.selectedMemberId || undefined)
        await fetchSuggestions()
    } catch (e) {
        console.error("Failed to approve suggestion", e)
    }
}


const newRecurrence = ref({
    name: '',
    amount: 0,
    category: '',
    account_id: '',
    frequency: 'MONTHLY',
    start_date: new Date().toISOString().slice(0, 10),
    type: 'DEBIT',
    exclude_from_reports: false
})

async function saveRecurrence() {
    try {
        await financeApi.createRecurringTransaction({
            ...newRecurrence.value,
            next_run_date: newRecurrence.value.start_date
        })
        showAddModal.value = false
        await store.fetchRecurring(authStore.selectedMemberId || undefined)
    } catch (e) {
        console.error(e)
    }
}

async function deleteRecurrence(id: string) {
    const isConfirmed = await confirmDialog.prompt("Stop this subscription?", "Stop Subscription", "Stop", "Keep")
    if (!isConfirmed) return;
    financeApi.deleteRecurring(id).then(() => store.fetchRecurring(authStore.selectedMemberId || undefined))
}

const frequencyOptions = ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']

// Expose modal control to parent
defineExpose({
    openAddModal: () => { showAddModal.value = true }
})
</script>

<style scoped>
.recurring-glass-card {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.recurring-glass-card:hover {
    background: rgba(var(--v-theme-surface), 0.9);
}

.opacity-0 {
    opacity: 0;
}

.group:hover .opacity-0 {
    opacity: 1;
}

.glass-modal-card {
    background: rgba(var(--v-theme-surface), 0.9);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-modal-select :deep(.v-field__outline) {
    --v-field-border-opacity: 0.1;
}

.premium-modal-select:hover :deep(.v-field__outline) {
    --v-field-border-opacity: 0.4;
    border-color: rgb(var(--v-theme-primary)) !important;
}

.suggestion-card {
    background: rgba(var(--v-theme-primary), 0.03) !important;
    border: 1px solid rgba(var(--v-theme-primary), 0.1) !important;
    transition: all 0.3s ease;
}

.suggestion-card:hover {
    background: rgba(var(--v-theme-primary), 0.06) !important;
    transform: translateY(-4px);
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.suggestions-slider::-webkit-scrollbar {
    display: none;
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.border-premium {
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
}

.icon-orb {
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}
</style>
