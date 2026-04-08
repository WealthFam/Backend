<template>
    <div class="recurring-content px-0 pb-12">
        <!-- Dashboard Header -->
        <div class="d-flex align-center justify-space-between mb-8 flex-wrap gap-4">
            <div>
                <h2 class="text-h4 font-weight-black mb-1">Subscriptions</h2>
                <p class="text-subtitle-2 text-medium-emphasis">Track and manage your recurring bills and payments</p>
            </div>
            <v-btn color="primary" @click="showAddModal = true" rounded="xl" height="52"
                class="text-none font-weight-black px-8 premium-btn" elevation="8">
                <template v-slot:prepend>
                    <Plus :size="20" stroke-width="3" />
                </template>
                Add New Subscription
            </v-btn>
        </div>

        <!-- Smart Suggestions Section (Redesigned) -->
        <div v-if="suggestions.length > 0 || loadingSuggestions" class="suggestions-container mb-12">
            <div class="d-flex align-center mb-6">
                <div class="icon-orb mr-4">
                    <Sparkles :size="20" class="text-primary" />
                </div>
                <div>
                    <h3 class="text-h6 font-weight-black">Smart Discoveries</h3>
                    <p class="text-caption font-weight-bold opacity-60">We found potential subscriptions in your history
                    </p>
                </div>
                <v-spacer />
                <v-btn variant="text" size="small" rounded="lg" @click="fetchSuggestions" :loading="loadingSuggestions"
                    class="text-none font-weight-bold">
                    <RefreshCw :size="14" class="mr-2" /> Refresh
                </v-btn>
            </div>

            <div class="suggestions-grid">
                <v-card v-for="(suggestion, idx) in suggestions" :key="idx"
                    class="suggestion-premium-card pa-5 border-premium group" elevation="0">
                    <div class="d-flex justify-space-between align-start mb-4">
                        <v-avatar color="primary" variant="tonal" size="48" rounded="xl" class="suggestion-icon">
                            <component :is="getCategoryLucideIcon(suggestion.category)" :size="24" />
                        </v-avatar>
                    </div>

                    <div class="suggestion-info mb-4">
                        <div class="text-subtitle-1 font-weight-black text-truncate">{{ suggestion.name }}</div>
                        <div class="d-flex align-center mt-1">
                            <span class="text-h5 font-weight-black color-primary">{{ formatAmount(suggestion.amount)
                                }}</span>
                            <v-chip size="x-small" color="primary" variant="tonal"
                                class="ml-auto font-weight-bold px-3">
                                {{ suggestion.frequency }}
                            </v-chip>
                        </div>
                    </div>

                    <div class="suggestion-meta mb-5 pa-3 rounded-lg bg-surface-variant-alpha">
                        <div class="d-flex align-center mb-1">
                            <div class="confidence-bar flex-grow-1 mr-3">
                                <div class="confidence-fill" :style="{ width: `${suggestion.confidence * 100}%` }">
                                </div>
                            </div>
                            <span class="text-caption font-weight-bold">{{ (suggestion.confidence * 100).toFixed(0)
                                }}%</span>
                        </div>
                        <div class="text-caption opacity-70 font-weight-medium line-clamp-2">{{ suggestion.reason }}
                        </div>
                    </div>

                    <div class="d-flex gap-3">
                        <v-btn flex-grow-1 color="primary" variant="elevated" size="large" rounded="xl"
                            class="text-none font-weight-black action-btn px-6" @click="approveSuggestion(suggestion)">
                            Confirm
                        </v-btn>
                        <v-btn variant="tonal" color="error" size="large" rounded="xl"
                            class="text-none font-weight-black px-6" @click="ignoreSuggestion(suggestion)">
                            Reject
                        </v-btn>
                    </div>
                </v-card>
            </div>
        </div>

        <!-- Active Subscriptions List -->
        <div v-if="store.recurringTransactions.length > 0">
            <h3 class="text-h6 font-weight-black mb-6 d-flex align-center">
                Active Tracking
                <v-chip class="ml-3 font-weight-black" color="primary" size="small">{{
                    store.recurringTransactions.length
                    }}</v-chip>
            </h3>
            <v-row>
                <v-col v-for="rec in store.recurringTransactions" :key="rec.id" cols="12" md="6" lg="4">
                    <v-card rounded="2xl" class="active-subscription-card hover-elevate group" elevation="0">
                        <div class="pa-5">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="d-flex align-center">
                                    <v-avatar :color="rec.amount < 0 ? 'success' : 'primary'" variant="tonal" size="52"
                                        rounded="xl" class="mr-4">
                                        <component :is="getCategoryLucideIcon(rec.category)" :size="24" />
                                    </v-avatar>
                                    <div>
                                        <h3 class="text-subtitle-1 font-weight-black mb-0">{{ rec.name }}</h3>
                                        <div class="d-flex align-center mt-1">
                                            <v-chip size="x-small" variant="flat" color="surface-variant"
                                                class="font-weight-bold px-2 mr-2">
                                                {{ rec.frequency }}
                                            </v-chip>
                                            <span class="text-caption opacity-60 font-weight-bold">Next: {{ new
                                                Date(rec.next_run_date).toLocaleDateString(undefined, {
                                                    month: 'short',
                                                    day:
                                                        'numeric'
                                                }) }}</span>
                                        </div>
                                    </div>
                                </div>
                                <div class="text-right">
                                    <div class="text-h6 font-weight-black">{{ formatAmount(rec.amount) }}</div>
                                    <v-chip v-if="rec.exclude_from_reports" color="error" variant="tonal" size="x-small"
                                        label class="mt-1 font-weight-black">HIDDEN</v-chip>
                                </div>
                            </div>

                            <div class="d-flex align-center pt-3 border-top-dashed">
                                <div class="text-caption text-medium-emphasis font-weight-medium">
                                    <Calendar :size="14" class="mr-1 mb-1" /> Started {{ new
                                        Date(rec.start_date).toLocaleDateString() }}
                                </div>
                                <v-spacer />
                                <div class="actions d-flex gap-2">
                                    <v-btn variant="tonal" size="x-small" icon color="primary" class="rounded-lg">
                                        <Edit2 :size="14" />
                                    </v-btn>
                                    <v-btn variant="tonal" size="x-small" icon color="error" class="rounded-lg"
                                        @click="deleteRecurrence(rec.id)">
                                        <Trash2 :size="14" />
                                    </v-btn>
                                </div>
                            </div>
                        </div>
                    </v-card>
                </v-col>
            </v-row>
        </div>

        <!-- Empty State -->
        <div v-else-if="!loadingSuggestions" class="text-center py-16 empty-container rounded-pill-extra mt-8">
            <div class="empty-icon-wrapper mb-6">
                <CalendarClock :size="64" class="text-primary opacity-40" stroke-width="1.5" />
            </div>
            <h3 class="text-h5 font-weight-black mb-2">Clear Your Financial Horizon</h3>
            <p class="text-medium-emphasis mx-auto mb-8" style="max-width: 400px;">
                You don't have any active subscriptions yet. Add your fixed expenses like rent, Netflix, or EMI for
                precise
                forecasting.
            </p>
            <v-btn color="primary" class="px-12 premium-btn" rounded="xl" height="56" elevation="12"
                @click="showAddModal = true">
                <template v-slot:prepend>
                    <Plus :size="20" stroke-width="3" />
                </template>
                Add Your First Subscription
            </v-btn>
        </div>

        <!-- Add Recurrence Modal -->
        <v-dialog v-model="showAddModal" max-width="500" persistent transition="dialog-bottom-transition">
            <v-card rounded="xl" class="glass-modal-card overflow-hidden">
                <div class="modal-gradient-bg"></div>
                <v-toolbar color="transparent" class="px-4">
                    <v-toolbar-title class="font-weight-black">Subscription Details</v-toolbar-title>
                    <v-spacer />
                    <v-btn variant="tonal" size="small" @click="showAddModal = false" icon class="rounded-lg">
                        <X :size="20" />
                    </v-btn>
                </v-toolbar>

                <v-card-text class="pa-8">
                    <v-row dense>
                        <v-col cols="12" class="mb-4">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">Provider
                                / Bill Name</label>
                            <v-text-field v-model="newRecurrence.name" placeholder="Netflix, Rent, Salary..."
                                variant="outlined" density="comfortable" flat rounded="xl" hide-details
                                class="custom-input">
                                <template v-slot:prepend-inner>
                                    <CreditCard :size="18" class="text-primary mr-2" />
                                </template>
                            </v-text-field>
                        </v-col>

                        <v-col cols="6" class="mb-4 pr-2">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">Amount</label>
                            <v-text-field v-model="newRecurrence.amount" type="number" prefix="₹" variant="outlined"
                                density="comfortable" flat rounded="xl" hide-details class="custom-input" />
                        </v-col>

                        <v-col cols="6" class="mb-4 pl-2">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">Billing
                                Cycle</label>
                            <v-select v-model="newRecurrence.frequency" :items="frequencyOptions" variant="outlined"
                                density="comfortable" flat rounded="xl" hide-details menu-icon="" class="custom-input">
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="6" class="mb-4 pr-2">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">First/Next
                                Payment</label>
                            <v-text-field v-model="newRecurrence.start_date" type="date" variant="outlined"
                                density="comfortable" flat rounded="xl" hide-details class="custom-input" />
                        </v-col>

                        <v-col cols="6" class="mb-4 pl-2">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">Source
                                Account</label>
                            <v-select v-model="newRecurrence.account_id"
                                :items="store.accounts.map(a => ({ title: a.name, value: a.id }))" variant="outlined"
                                density="comfortable" hide-details flat rounded="xl" class="custom-input" menu-icon="">
                                <template v-slot:prepend-inner>
                                    <Wallet :size="18" class="text-primary mr-2" />
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12" class="mb-6">
                            <label
                                class="text-caption font-weight-black text-uppercase tracking-wider mb-2 d-block opacity-70">Category</label>
                            <v-select v-model="newRecurrence.category"
                                :items="store.categories.map(c => ({ title: c.name, value: c.name }))"
                                variant="outlined" density="comfortable" hide-details flat rounded="xl"
                                class="custom-input" menu-icon="">
                                <template v-slot:prepend-inner>
                                    <component :is="getCategoryLucideIcon(newRecurrence.category)" :size="18"
                                        class="text-primary mr-2" />
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary" />
                                </template>
                            </v-select>
                        </v-col>

                        <v-col cols="12" class="d-flex align-center bg-surface-variant-alpha pa-4 rounded-xl">
                            <div class="mr-4">
                                <ShieldCheck :size="24" class="text-error" />
                            </div>
                            <div>
                                <div class="text-subtitle-2 font-weight-black">Private Expense</div>
                                <div class="text-caption opacity-70">Hide this from shared family reports and summaries.
                                </div>
                            </div>
                            <v-spacer />
                            <v-switch v-model="newRecurrence.exclude_from_reports" color="error" inset hide-details />
                        </v-col>
                    </v-row>
                </v-card-text>

                <div class="pa-8 d-flex gap-4">
                    <v-btn block variant="tonal" rounded="xl" height="52"
                        class="text-none font-weight-black flex-grow-1" @click="showAddModal = false">Cancel</v-btn>
                    <v-btn block color="primary" variant="elevated" rounded="xl" height="52"
                        class="text-none font-weight-black flex-grow-1 premium-btn" @click="saveRecurrence">Start
                        Tracking</v-btn>
                </div>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { todayLocalString } from '@/utils/time'
import { ref, onMounted } from 'vue'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import { useCurrency } from '@/composables/useCurrency'
import { financeApi } from '@/api/client'
import { useConfirmStore } from '@/stores/confirm'
import {
    Plus, X, ChevronDown, CalendarClock, Trash2, Wallet,
    CreditCard, Sparkles, RefreshCw, Calendar, Edit2, ShieldCheck
} from 'lucide-vue-next'
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

async function ignoreSuggestion(suggestion: any) {
    try {
        await financeApi.ignoreRecurringSuggestion(suggestion.pattern)
        await fetchSuggestions()
    } catch (e) {
        console.error("Failed to ignore suggestion", e)
    }
}

async function approveSuggestion(suggestion: any) {
    // Fill the modal with suggestion data for user review
    newRecurrence.value = {
        name: suggestion.name,
        amount: suggestion.amount,
        category: suggestion.category || '',
        account_id: suggestion.account_id,
        frequency: suggestion.frequency,
        start_date: suggestion.last_date ? suggestion.last_date.split('T')[0] : todayLocalString(),
        type: 'DEBIT',
        exclude_from_reports: false
    }
    showAddModal.value = true
}

const newRecurrence = ref({
    name: '',
    amount: 0,
    category: '',
    account_id: '',
    frequency: 'MONTHLY',
    start_date: todayLocalString(),
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
    try {
        await financeApi.deleteRecurring(id)
        await store.fetchRecurring(authStore.selectedMemberId || undefined)
    } catch (e) {
        console.error("Failed to delete recurring transaction", e)
    }
}

const frequencyOptions = ['DAILY', 'WEEKLY', 'BI-WEEKLY', 'MONTHLY', 'QUARTERLY', 'YEARLY']

// Expose modal control to parent
defineExpose({
    openAddModal: () => {
        newRecurrence.value = {
            name: '',
            amount: 0,
            category: '',
            account_id: '',
            frequency: 'MONTHLY',
            start_date: todayLocalString(),
            type: 'DEBIT',
            exclude_from_reports: false
        }
        showAddModal.value = true
    }
})
</script>

<style scoped>
.suggestions-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 24px;
}

.suggestion-premium-card {
    background: rgba(var(--v-theme-surface), 0.4);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 24px;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
}

.suggestion-premium-card:hover {
    background: rgba(var(--v-theme-surface), 0.7);
    transform: translateY(-8px);
    border-color: rgba(var(--v-theme-primary), 0.3);
}

.suggestion-premium-card::after {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 150px;
    height: 150px;
    background: radial-gradient(circle at top right, rgba(var(--v-theme-primary), 0.05), transparent 70%);
}

.icon-orb {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 0.2));
    border-radius: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.1);
}

.suggestion-icon {
    box-shadow: 0 8px 20px rgba(var(--v-theme-primary), 0.1);
}

.color-primary {
    color: rgb(var(--v-theme-primary));
}

.bg-surface-variant-alpha {
    background: rgba(var(--v-theme-surface-variant), 0.3);
}

.confidence-bar {
    height: 6px;
    background: rgba(var(--v-theme-surface-variant), 0.5);
    border-radius: 3px;
    overflow: hidden;
}

.confidence-fill {
    height: 100%;
    background: linear-gradient(90deg, rgb(var(--v-theme-primary)), #10B981);
    border-radius: 3px;
}

.active-subscription-card {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: all 0.3s ease;
}

.active-subscription-card:hover {
    background: rgba(var(--v-theme-surface), 0.9);
    border-color: rgba(var(--v-theme-primary), 0.2);
    transform: scale(1.02);
}

.border-top-dashed {
    border-top: 1px dashed rgba(var(--v-border-color), 0.2);
}

.premium-btn {
    box-shadow: 0 8px 16px rgba(var(--v-theme-primary), 0.2) !important;
    transition: all 0.3s ease;
}

.premium-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 24px rgba(var(--v-theme-primary), 0.3) !important;
}

.empty-container {
    background: rgba(var(--v-theme-surface-variant), 0.1);
    border: 2px dashed rgba(var(--v-border-color), 0.1);
}

.empty-icon-wrapper {
    width: 120px;
    height: 120px;
    background: rgba(var(--v-theme-primary), 0.05);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto;
}

.glass-modal-card {
    background: rgba(var(--v-theme-surface), 0.9);
    backdrop-filter: blur(24px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.modal-gradient-bg {
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 75% 25%, rgba(var(--v-theme-primary), 0.05), transparent);
    pointer-events: none;
}

.custom-input :deep(.v-field) {
    background: rgba(var(--v-theme-surface-variant), 0.2);
    border-radius: 16px !important;
}

.custom-input :deep(.v-field__outline) {
    display: none;
}

.dismiss-btn {
    z-index: 10;
}

.opacity-0 {
    opacity: 0;
}

.group:hover .opacity-0 {
    opacity: 1;
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.rounded-pill-extra {
    border-radius: 40px;
}

.tracking-wider {
    letter-spacing: 0.05em;
}
</style>
