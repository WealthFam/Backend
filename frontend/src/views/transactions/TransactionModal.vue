<script setup lang="ts">
import { computed } from 'vue'
import { useCurrency } from '@/composables/useCurrency'

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
        <v-card class="premium-modal-card rounded-xl overflow-hidden shadow-2xl">
            <v-card-title class="pa-0">
                <div class="modal-header-premium pa-4 px-6 d-flex align-center justify-space-between text-white">
                    <div class="d-flex align-center gap-4">
                        <div class="header-icon-wrapper">
                            <v-icon size="28" color="white">{{ isEditing ? 'Pencil' : 'Plus' }}</v-icon>
                        </div>
                        <div>
                            <h2 class="text-h5 font-weight-black mb-0">{{ isEditing ? 'Edit Transaction' :
                                'New Transaction' }}</h2>
                            <p class="text-caption text-white opacity-70 font-weight-bold mb-0">
                                {{ isEditing ? 'Update transaction details and category' :
                                    'Record a new spending or income' }}
                            </p>
                        </div>
                    </div>
                    <v-btn icon="X" variant="tonal" color="white" density="comfortable" @click="handleClose"
                        class="backdrop-blur-sm"></v-btn>
                </div>
            </v-card-title>

            <v-card-text class="pa-0 bg-background">
                <v-form @submit.prevent="handleSubmit">
                    <div class="pa-5">
                        <!-- Primary Info Section -->
                        <div class="section-group mb-5">
                            <div class="d-flex align-center gap-2 mb-4">
                                <v-icon color="primary" size="20" icon="Info"></v-icon>
                                <span class="text-overline font-weight-black text-primary letter-spacing-wide">Basic
                                    Details</span>
                            </div>

                            <v-row dense>
                                <v-col cols="12" class="mb-1">
                                    <v-text-field v-model="form.description" label="Description"
                                        placeholder="What was this for?" variant="solo-filled" density="compact" flat
                                        rounded="lg" class="premium-input-v2" hide-details autocomplete="off" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-text-field v-model="form.amount" label="Amount" type="number" placeholder="0.00"
                                        variant="solo-filled" density="compact" flat rounded="lg"
                                        class="premium-input-v2" hide-details prepend-inner-icon="DollarSign"
                                        autocomplete="off" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-text-field v-model="form.date" label="Date & Time" type="datetime-local"
                                        variant="solo-filled" density="compact" flat rounded="lg"
                                        class="premium-input-v2" hide-details prepend-inner-icon="Calendar" />
                                </v-col>
                            </v-row>
                        </div>

                        <!-- Categorization Section -->
                        <div class="section-group mb-5">
                            <div class="d-flex align-center gap-2 mb-4">
                                <v-icon color="secondary" size="20">mdi-tag-outline</v-icon>
                                <span
                                    class="text-overline font-weight-black text-secondary letter-spacing-wide">Classification</span>
                            </div>

                            <v-row dense>
                                <v-col cols="12" md="6" class="mb-1">
                                    <v-select v-model="form.account_id" :items="accountOptions" label="Account"
                                        variant="solo-filled" density="compact" flat rounded="lg"
                                        class="premium-input-v2" hide-details prepend-inner-icon="Landmark" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-select v-model="form.category" :items="categoryOptions" label="Category"
                                        placeholder="Uncategorized" variant="solo-filled" density="compact" flat
                                        rounded="lg" class="premium-input-v2" hide-details
                                        prepend-inner-icon="Shapes" />
                                </v-col>

                                <v-col cols="12" class="mb-1">
                                    <v-select v-model="form.expense_group_id" :items="expenseGroupOptions"
                                        label="Life Event / Group"
                                        placeholder="Add to a project or life event (Optional)" variant="solo-filled"
                                        density="compact" flat rounded="lg" class="premium-input-v2" hide-details
                                        prepend-inner-icon="Folder" />
                                </v-col>
                            </v-row>
                        </div>

                        <!-- Advanced Options Section -->
                        <div class="section-group">
                            <div class="d-flex align-center gap-2 mb-4">
                                <v-icon color="accent" size="20" icon="Settings2"></v-icon>
                                <span class="text-overline font-weight-black text-accent letter-spacing-wide">Advanced
                                    Options</span>
                            </div>

                            <v-card variant="flat" border class="rounded-xl pa-3 bg-surface border-opacity-10 mb-3">
                                <v-row align="center">
                                    <v-col cols="12" sm="6">
                                        <v-switch v-model="form.is_transfer" label="Is this a Transfer?" color="primary"
                                            hide-details density="compact" class="font-weight-bold" persistent-hint
                                            hint="Moving money between your own accounts">
                                            <template #label>
                                                <div class="d-flex flex-column ml-2">
                                                    <span class="text-body-2 font-weight-bold">Internal Transfer</span>
                                                    <span class="text-[10px] opacity-60">Between your accounts</span>
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
                                                    <span class="text-[10px] opacity-60">Exclude from
                                                        budget/spending</span>
                                                </div>
                                            </template>
                                        </v-switch>
                                    </v-col>
                                </v-row>
                            </v-card>

                            <v-expand-transition>
                                <div v-if="form.is_transfer" class="mt-4">
                                    <v-card variant="tonal" color="primary" class="rounded-xl pa-4 border-opacity-10">
                                        <div class="d-flex align-center gap-2 mb-4">
                                            <v-icon size="20" icon="ArrowLeftRight"></v-icon>
                                            <span class="text-subtitle-2 font-weight-black">Match Transfer Pair</span>
                                        </div>

                                        <v-row dense>
                                            <v-col cols="12" md="8">
                                                <v-select v-model="form.to_account_id" :items="accountOptions"
                                                    label="Destination Account" placeholder="Select account"
                                                    variant="solo" density="compact" flat rounded="lg"
                                                    class="premium-field" hide-details />
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
                                                <v-icon size="14" icon="Search"></v-icon>
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
                                                                <v-icon size="16"
                                                                    :color="form.linked_transaction_id === match.id ? 'primary' : 'white'"
                                                                    icon="Link"></v-icon>
                                                            </v-avatar>
                                                            <div>
                                                                <div class="text-subtitle-2 font-weight-black">{{
                                                                    match.description }}</div>
                                                                <div class="text-[10px] opacity-70 font-weight-bold">{{
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
                                                    <v-icon size="32" class="mb-2" icon="SearchX"></v-icon>
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
                                    class="rounded-xl border-opacity-20 py-3 px-4 shadow-sm">
                                    <template v-slot:prepend>
                                        <div class="bg-primary rounded-lg pa-1 mr-2 opacity-80">
                                            <v-icon size="16" color="white" icon="LineChart"></v-icon>
                                        </div>
                                    </template>
                                    <div class="d-flex align-center justify-space-between w-100">
                                        <div class="text-caption font-weight-black">
                                            {{ currentCategoryBudget.name }} Budget Info
                                        </div>
                                        <div class="text-caption font-weight-black opacity-80">
                                            Remaining: {{ formatAmount(currentCategoryBudget.balance) }}
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
                    height="40" @click="handleSubmit" prepend-icon="CheckCircle2">
                    {{ isEditing ? 'Update Entry' : 'Create Transaction' }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.premium-modal-card {
    background: rgb(var(--v-theme-surface));
}

.modal-header-premium {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, #4338ca 100%);
    position: relative;
    overflow: hidden;
}

.modal-header-premium::before {
    content: '';
    position: absolute;
    top: -50%;
    right: -10%;
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0) 70%);
    transform: rotate(-15deg);
}

.header-icon-wrapper {
    background: rgba(255, 255, 255, 0.15);
    padding: 10px;
    border-radius: 16px;
    backdrop-filter: blur(4px);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.section-group {
    position: relative;
}

.premium-input-v2 :deep(.v-field) {
    border-radius: 12px !important;
    background-color: rgb(var(--v-theme-surface)) !important;
    border: 1px solid rgba(var(--v-border-color), 0.08);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-input-v2 :deep(.v-field:hover) {
    border-color: rgba(var(--v-theme-primary), 0.2);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
}

.premium-input-v2 :deep(.v-field--focused) {
    border-color: rgb(var(--v-theme-primary));
    box-shadow: 0 0 0 4px rgba(var(--v-theme-primary), 0.08) !important;
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

.bg-slate-50 {
    background-color: rgb(var(--v-theme-background));
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

.text-[10px] {
    font-size: 10px;
}
</style>
