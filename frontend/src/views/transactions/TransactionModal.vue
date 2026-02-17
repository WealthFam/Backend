```vue
<script setup lang="ts">
import { computed } from 'vue'
import { useCurrency } from '@/composables/useCurrency'
import {
    CheckCircle2, X, Pencil, Plus, Info, Tag,
    Settings, ArrowLeftRight, Search, Link, SearchX, LineChart
} from 'lucide-vue-next'

const props = defineProps<{
    isOpen: boolean
    isEditing: boolean
    form: any
    accounts: any[]
    categories: any[]
    budgets: any[]
    expenseGroups: any[]
    potentialMatches: any[]
    isSearchingMatches: boolean
    matchesSearched: boolean
}>()

const emit = defineEmits(['close', 'submit', 'findMatches', 'selectMatch'])

const { formatAmount } = useCurrency()

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
    return list.map(o => ({ title: o.label, value: o.value }))
})

const accountOptions = computed(() => {
    return props.accounts.map(a => ({ title: a.name, value: a.id }))
})

const expenseGroupOptions = computed(() => {
    return [{ title: 'None', value: '' }, ...props.expenseGroups.map(g => ({ title: g.name, value: g.id }))]
})

const currentCategoryBudget = computed(() => {
    if (!props.form.category || props.form.is_transfer) return null
    return props.budgets.find(b => b.category === props.form.category) || null
})

function handleSubmit() {
    emit('submit')
}

function handleClose() {
    emit('close')
}
</script>

<template>
    <v-dialog :model-value="isOpen" @update:model-value="handleClose" persistent max-width="650" scrollable>
        <v-card class="premium-glass-card rounded-xl overflow-hidden no-hover">
            <v-card-title class="pa-0">
                <div class="modal-header-premium pa-4 px-6 d-flex align-center justify-space-between">
                    <div class="d-flex align-center gap-4">
                        <div class="header-icon-wrapper">
                            <component :is="isEditing ? Pencil : Plus" :size="28" class="text-primary" />
                        </div>
                        <div>
                            <h2 class="text-h5 font-weight-black mb-0">{{ isEditing ? 'Edit Transaction' :
                                'New Transaction' }}</h2>
                            <p class="text-caption opacity-70 font-weight-bold mb-0">
                                {{ isEditing ? 'Update transaction details and category' :
                                    'Record a new spending or income' }}
                            </p>
                        </div>
                    </div>
                    <v-btn :icon="X" variant="tonal" color="medium-emphasis" density="comfortable" @click="handleClose"
                        class="backdrop-blur-sm"></v-btn>
                </div>
            </v-card-title>

            <v-card-text class="pa-0 bg-background">
                <v-form @submit.prevent="handleSubmit">
                    <div class="pa-5">
                        <!-- Primary Info Section -->
                        <div class="section-group mb-5">
                            <div class="d-flex align-center gap-2 mb-4">
                                <Info :size="20" class="text-primary" />
                                <span class="text-overline font-weight-black text-primary letter-spacing-wide">Basic
                                    Details</span>
                            </div>

                            <v-row dense>
                                <v-col cols="12" class="mb-1">
                                    <v-text-field v-model="form.description" label="Description"
                                        placeholder="What was this for?" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        autocomplete="off" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-text-field v-model="form.amount" label="Amount" type="number" placeholder="0.00"
                                        variant="outlined" density="comfortable" rounded="lg"
                                        class="premium-modal-input font-weight-bold" hide-details
                                        prepend-inner-icon="DollarSign" autocomplete="off" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-text-field v-model="form.date" label="Date & Time" type="datetime-local"
                                        variant="outlined" density="comfortable" rounded="lg"
                                        class="premium-modal-input font-weight-bold" hide-details
                                        prepend-inner-icon="Calendar" />
                                </v-col>
                            </v-row>
                        </div>

                        <!-- Categorization Section -->
                        <div class="section-group mb-5">
                            <div class="d-flex align-center gap-2 mb-4">
                                <Tag :size="20" class="text-secondary" />
                                <span
                                    class="text-overline font-weight-black text-secondary letter-spacing-wide">Classification</span>
                            </div>

                            <v-row dense>
                                <v-col cols="12" md="6" class="mb-1">
                                    <v-select v-model="form.account_id" :items="accountOptions" label="Account"
                                        item-title="title" item-value="value" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        prepend-inner-icon="Landmark" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-autocomplete v-model="form.category" :items="categoryOptions" label="Category"
                                        item-title="title" item-value="value" placeholder="Uncategorized"
                                        variant="outlined" density="comfortable" rounded="lg"
                                        class="premium-modal-input font-weight-bold" hide-details
                                        prepend-inner-icon="Tag" />
                                </v-col>

                                <v-col cols="12" class="mb-1">
                                    <v-select v-model="form.expense_group_id" :items="expenseGroupOptions"
                                        label="Life Event / Group" item-title="title" item-value="value"
                                        placeholder="Add to a project or life event (Optional)" variant="outlined"
                                        density="comfortable" rounded="lg" class="premium-modal-input font-weight-bold"
                                        hide-details prepend-inner-icon="Folder" />
                                </v-col>
                            </v-row>
                        </div>

                        <!-- Advanced Options Section -->
                        <div class="section-group">
                            <div class="d-flex align-center gap-2 mb-4">
                                <Settings :size="20" class="text-accent" />
                                <span class="text-overline font-weight-black text-accent letter-spacing-wide">Advanced
                                    Options</span>
                            </div>

                            <v-card variant="flat" border class="pa-3 bg-surface border-opacity-10 mb-3"
                                style="border-radius: 20px !important;">
                                <v-row align="center">
                                    <v-col cols="12" sm="6">
                                        <v-switch v-model="form.is_transfer" label="Is this a Transfer?" color="primary"
                                            hide-details density="compact" class="font-weight-bold" persistent-hint
                                            hint="Moving money between your own accounts">
                                            <template #label>
                                                <div class="d-flex flex-column ml-2">
                                                    <span class="text-body-2 font-weight-bold">Internal Transfer</span>
                                                    <span class="text-tiny opacity-60">Between your accounts</span>
                                                </div>
                                            </template>
                                        </v-switch>
                                    </v-col>
                                    <v-col cols="12" sm="6">
                                        <v-switch v-model="form.exclude_from_reports" label="Hide from Reports"
                                            color="error" hide-details density="compact" class="font-weight-bold">
                                            <template #label>
                                                <div class="d-flex flex-column ml-2">
                                                    <span class="text-body-2 font-weight-bold">Hide from
                                                        Analytics</span>
                                                    <span class="text-tiny opacity-60">Exclude from
                                                        budget/spending</span>
                                                </div>
                                            </template>
                                        </v-switch>
                                    </v-col>
                                </v-row>
                            </v-card>

                            <v-expand-transition>
                                <div v-if="form.is_transfer" class="mt-4">
                                    <v-card variant="flat" class="pa-4 border-opacity-10"
                                        style="background: rgba(var(--v-theme-primary), 0.05); border-radius: 20px !important;">
                                        <div class="d-flex align-center gap-2 mb-4">
                                            <ArrowLeftRight :size="20" class="text-primary" />
                                            <span class="text-subtitle-2 font-weight-black">Match Transfer Pair</span>
                                        </div>

                                        <v-row dense>
                                            <v-col cols="12" md="8">
                                                <v-select v-model="form.to_account_id" :items="accountOptions"
                                                    item-title="title" item-value="value" label="Destination Account"
                                                    placeholder="Select account" variant="outlined"
                                                    density="comfortable" rounded="lg"
                                                    class="premium-modal-input font-weight-bold" hide-details />
                                            </v-col>
                                            <v-col cols="12" md="4">
                                                <v-btn color="primary" block height="40" rounded="lg" variant="flat"
                                                    @click="emit('findMatches')" :loading="isSearchingMatches">
                                                    Scan Matches
                                                </v-btn>
                                            </v-col>
                                        </v-row>

                                        <div v-if="matchesSearched" class="mt-6">
                                            <p
                                                class="text-caption font-weight-black mb-3 opacity-70 d-flex align-center gap-2">
                                                <Search :size="14" />
                                                Found {{ potentialMatches.length }} matches within 3-day window
                                            </p>
                                            <div class="d-flex flex-column gap-3">
                                                <v-card v-for="match in potentialMatches" :key="match.id" padding="0"
                                                    class="match-card rounded-xl border-opacity-5 cursor-pointer overflow-hidden transition-all"
                                                    :class="{ 'match-selected-active': form.linked_transaction_id === match.id }"
                                                    @click="emit('selectMatch', match)" variant="flat"
                                                    :color="form.linked_transaction_id === match.id ? 'primary' : 'surface'">
                                                    <div class="pa-4 d-flex justify-space-between align-center">
                                                        <div class="d-flex align-center gap-3">
                                                            <v-avatar size="32"
                                                                :color="form.linked_transaction_id === match.id ? 'white' : 'primary'"
                                                                class="opacity-80">
                                                                <Link :size="16"
                                                                    :color="form.linked_transaction_id === match.id ? 'primary' : 'white'" />
                                                            </v-avatar>
                                                            <div>
                                                                <div class="text-subtitle-2 font-weight-black">{{
                                                                    match.description }}</div>
                                                                <div class="text-tiny opacity-70 font-weight-bold">{{
                                                                    match.date }}</div>
                                                            </div>
                                                        </div>
                                                        <div class="text-h6 font-weight-black">
                                                            {{ formatAmount(match.amount) }}
                                                        </div>
                                                    </div>
                                                </v-card>
                                                <div v-if="potentialMatches.length === 0"
                                                    class="text-center py-6 opacity-40">
                                                    <SearchX :size="32" class="mb-2" />
                                                    <div class="text-caption font-weight-black">No matching txns found
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </v-card>
                                </div>
                            </v-expand-transition>
                        </div>

                        <v-expand-transition>
                            <div v-if="currentCategoryBudget" class="mt-4">
                                <v-alert color="primary" variant="tonal" border="start"
                                    class="rounded-xl border-opacity-20 py-3 px-4 shadow-sm"
                                    style="border-radius: 20px !important;">
                                    <template v-slot:prepend>
                                        <div class="bg-primary rounded-lg pa-1 mr-2 opacity-80">
                                            <LineChart :size="16" class="text-white" />
                                        </div>
                                    </template>
                                    <div class="d-flex align-center justify-space-between w-100">
                                        <div class="text-caption font-weight-black">
                                            {{ currentCategoryBudget.name }} Budget Info
                                        </div>
                                        <div class="text-caption font-weight-black opacity-80">
                                            Remaining: {{ formatAmount(currentCategoryBudget.remaining) }}
                                        </div>
                                    </div>
                                </v-alert>
                            </div>
                        </v-expand-transition>
                    </div>
                </v-form>
            </v-card-text>

            <v-divider class="opacity-5"></v-divider>

            <v-card-actions class="pa-4 bg-surface px-6">
                <v-btn variant="text" rounded="pill" class="font-weight-black px-8" @click="handleClose"
                    color="medium-emphasis">
                    Cancel
                </v-btn>
                <v-spacer></v-spacer>
                <v-btn color="primary" variant="flat" rounded="pill" class="font-weight-black px-10 elevation-4"
                    height="40" @click="handleSubmit" :prepend-icon="CheckCircle2">
                    {{ isEditing ? 'Update Entry' : 'Create Transaction' }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
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
}

.modal-header-premium {
    background: transparent;
    position: relative;
    overflow: hidden;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.header-icon-wrapper {
    background: rgba(var(--v-theme-primary), 0.1);
    padding: 10px;
    border-radius: 16px;
    border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.section-group {
    position: relative;
}

.premium-modal-input :deep(.v-field) {
    /* background: rgba(var(--v-theme-surface), 0.5) !important; */
    /* border: 1px solid rgba(var(--v-border-color), 0.1) !important; */
    box-shadow: none !important;
    /* border-radius: 12px !important; */
    font-weight: 600;
}

.premium-modal-input :deep(.v-field--focused) {
    border-color: rgb(var(--v-theme-primary)) !important;
}

.match-card {
    border: 1px solid rgba(var(--v-border-color), 0.05);
    transition: all 0.2s ease;
}

.match-card:hover {
    transform: scale(1.01);
    border-color: rgba(var(--v-theme-primary), 0.2);
}

.match-selected-active {
    border: 2px solid rgb(var(--v-theme-primary)) !important;
    transform: scale(1.02);
    box-shadow: 0 8px 20px rgba(var(--v-theme-primary), 0.15) !important;
}

.letter-spacing-wide {
    letter-spacing: 0.1em;
}

.backdrop-blur-sm {
    backdrop-filter: blur(4px);
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

.text-tiny {
    font-size: 10px;
}
</style>
