<template>
    <v-container fluid class="pa-0 animate-in relative-pos z-10">
        <!-- Control Bar (Glass Box) -->
        <v-card class="premium-glass-card pa-4 mb-8 no-hover" rounded="xl">
            <v-row align="center">
                <v-col cols="12" sm="4">
                    <v-text-field v-model="rulesStore.searchQuery" placeholder="Search rules..." hide-details
                        density="comfortable" variant="outlined" class="font-weight-black" bg-color="surface">
                        <template v-slot:prepend-inner>
                            <Search :size="20" class="text-primary mr-2" />
                        </template>
                    </v-text-field>
                </v-col>

                <v-spacer />

                <v-col cols="12" sm="auto" class="d-flex align-center gap-3">
                    <!-- Export/Import Capsule (Matches CategoriesTab) -->
                    <div class="glass-card border rounded-pill d-flex align-center pa-1 shadow-sm"
                        style="background: rgba(var(--v-theme-surface), 0.5)">
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="rulesStore.exportRules">
                            <template v-slot:prepend>
                                <Download :size="16" />
                            </template>
                            Export
                            <v-tooltip activator="parent" location="top">Download rules as JSON</v-tooltip>
                        </v-btn>
                        <v-divider vertical class="mx-1 my-1 opacity-20" />
                        <v-btn variant="text" size="small" rounded="pill" color="primary"
                            class="text-none font-weight-black px-4" @click="ruleFileInput?.click()">
                            <template v-slot:prepend>
                                <Upload :size="16" />
                            </template>
                            Import
                            <input type="file" ref="ruleFileInput" class="d-none" accept=".json"
                                @change="handleRuleImport" />
                            <v-tooltip activator="parent" location="top">Upload rules from JSON</v-tooltip>
                        </v-btn>
                    </div>
                </v-col>
            </v-row>
        </v-card>

        <!-- Suggestions Section (Stacked Top) -->
        <v-expand-transition>
            <div v-if="rulesStore.suggestions.length > 0" class="mb-10">
                <div class="d-flex align-center gap-3 mb-6">
                    <v-avatar color="secondary" variant="tonal" size="44">
                        <Sparkles :size="24" class="text-secondary" />
                    </v-avatar>
                    <div>
                        <div class="d-flex align-center gap-2 mb-1">
                            <h2 class="text-h6 font-weight-black line-height-1">Suggestions</h2>
                            <v-chip size="x-small" color="secondary" variant="flat" border
                                class="font-weight-black letter-spacing-1">
                                {{ rulesStore.suggestions.length }}
                            </v-chip>
                        </div>
                        <p class="text-caption font-weight-bold opacity-60">Smart suggestions based on your
                            spending activity</p>
                    </div>
                </div>

                <v-row>
                    <v-col v-for="s in rulesStore.suggestions" :key="s.name" cols="12" md="4">
                        <v-card class="premium-glass-card pa-6 overflow-hidden" rounded="xl" elevation="2">
                            <div class="d-flex justify-space-between align-start relative-pos z-10">
                                <div class="flex-grow-1 min-w-0">
                                    <div class="d-flex align-center gap-2 mb-1">
                                        <div class="text-h6 font-weight-black truncate">{{ s.name }}</div>
                                        <v-chip v-if="s.count" size="x-small" color="secondary" variant="flat" border
                                            class="px-2 font-weight-black">
                                            {{ s.count }}x
                                        </v-chip>
                                    </div>
                                    <div v-if="s.reason" class="text-caption font-weight-black opacity-40 mb-2 truncate"
                                        :title="s.reason">
                                        {{ s.reason }}
                                    </div>
                                    <div class="text-body-2 font-weight-medium opacity-60 mb-4 italic truncate">
                                        matches "{{ s.keywords.join(', ') }}"
                                    </div>
                                    <div class="d-flex align-center gap-2">
                                        <v-chip color="primary" variant="tonal" size="small"
                                            class="font-weight-black letter-spacing-1" label border>
                                            {{ categoriesStore.getCategoryDisplay(s.category) }}
                                        </v-chip>
                                        <v-tooltip v-if="s.confidence_level" location="bottom">
                                            <template v-slot:activator="{ props }">
                                                <v-chip v-bind="props"
                                                    :color="['High', 'Very High'].includes(s.confidence_level) ? 'success' : 'warning'"
                                                    variant="text" size="small" class="font-weight-black">
                                                    <Zap :size="12" class="mr-1" />
                                                    {{ s.confidence_level }}
                                                </v-chip>
                                            </template>
                                            System is {{ Math.round(s.confidence * 100) }}% confident
                                        </v-tooltip>
                                    </div>
                                </div>
                                <div class="d-flex gap-2 ml-2">
                                    <v-btn variant="outlined" size="small" color="slate-400"
                                        class="rounded-lg border-thin"
                                        style="min-width: 36px; width: 36px; height: 36px; padding: 0"
                                        @click="rulesStore.ignoreSuggestion(s)">
                                        <X :size="18" />
                                        <v-tooltip activator="parent" location="top">Ignore</v-tooltip>
                                    </v-btn>
                                    <v-btn color="primary" variant="tonal" size="small" class="rounded-lg border-thin"
                                        style="min-width: 36px; width: 36px; height: 36px; padding: 0"
                                        @click="openSuggestionModal(s)">
                                        <Check :size="18" />
                                        <v-tooltip activator="parent" location="top">Accept Suggestion</v-tooltip>
                                    </v-btn>
                                </div>
                            </div>
                            <Sparkles class="card-bg-icon-standard" color="secondary" />
                        </v-card>
                    </v-col>
                </v-row>
            </div>
        </v-expand-transition>

        <!-- Active Rules Grid (Stacked Bottom) -->
        <v-divider class="mb-10 opacity-10" />

        <div class="d-flex align-center gap-3 mb-6">
            <v-avatar color="primary" variant="tonal" size="44">
                <FileText :size="24" class="text-primary" />
            </v-avatar>
            <div>
                <div class="d-flex align-center gap-2 mb-1">
                    <h2 class="text-h6 font-weight-black line-height-1">Active Rules</h2>
                    <v-chip size="x-small" color="primary" variant="flat" border
                        class="font-weight-black letter-spacing-1">
                        {{ rulesStore.rules.length }}
                    </v-chip>
                </div>
                <p class="text-caption font-weight-bold opacity-60">Manage your classification and categorization logic
                </p>
            </div>
        </div>

        <v-row v-if="rulesStore.filteredRules.length === 0" class="justify-center py-16">
            <v-col cols="12" sm="8" md="6" class="text-center">
                <v-avatar size="100" color="surface-variant" variant="tonal" class="mb-6 elevation-2">
                    <FileText :size="48" class="opacity-30" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">No Rules Found</h3>
                <p class="text-subtitle-1 opacity-60 mb-8 font-weight-medium mx-auto" style="max-width: 400px">
                    {{ rulesStore.emptyRulesMsg }}
                </p>
                <v-btn v-if="!rulesStore.searchQuery" color="primary" rounded="pill" size="large" variant="elevated"
                    class="text-none px-10 elevation-4 btn-primary-glow font-weight-black" @click="openAddRuleModal">
                    Create First Rule
                    <v-tooltip activator="parent" location="top">Define your first rule</v-tooltip>
                </v-btn>
            </v-col>
        </v-row>

        <!-- Rules Grid -->
        <v-row v-else class="pb-16">
            <!-- Add New Rule Card -->
            <v-col cols="12" sm="6" lg="4">
                <v-card
                    class="premium-glass-card group h-100 d-flex flex-column align-center justify-center border-dashed border-primary border-opacity-25"
                    rounded="xl" style="min-height: 240px; cursor: pointer" @click="openAddRuleModal">
                    <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                        style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                        <Plus :size="36" color="white" stroke-width="3" />
                    </v-avatar>
                    <div class="text-h6 font-weight-black mb-1">Add New Rule</div>
                    <div class="text-caption font-weight-bold opacity-40">Create custom classification</div>

                    <!-- Subtle background icon -->
                    <div class="card-bg-icon-standard">
                        <FileText :size="120" />
                    </div>
                </v-card>
            </v-col>
            <v-col v-for="rule in rulesStore.filteredRules" :key="rule.id" cols="12" sm="6" lg="4">
                <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden" rounded="xl">
                    <div class="pa-6 flex-grow-1 relative-pos z-10">
                        <div class="d-flex justify-space-between align-start mb-6">
                            <div class="d-flex align-center gap-4 min-w-0">
                                <v-avatar color="primary" variant="tonal" rounded="lg" size="52" border
                                    class="elevation-2">
                                    <FileText :size="28" />
                                </v-avatar>
                                <div class="min-w-0">
                                    <div class="text-h6 font-weight-black truncate mb-1">{{ rule.name }}</div>
                                    <v-chip v-if="rule.exclude_from_reports" density="comfortable" size="x-small"
                                        color="error" variant="flat" label
                                        class="text-uppercase font-weight-black letter-spacing-1">
                                        Hidden
                                    </v-chip>
                                    <span v-else class="text-caption font-weight-bold opacity-60">
                                        {{ rule.keywords.length }} Active Keyword{{ rule.keywords.length !== 1 ?
                                            's' :
                                            '' }}
                                    </span>
                                </div>
                            </div>

                            <div class="text-right shrink-0 ml-4">
                                <span
                                    class="text-overline font-weight-black opacity-60 line-height-1 mb-1 d-block">Store
                                    As</span>
                                <v-chip density="comfortable" size="small" variant="flat" color="surface"
                                    class="font-weight-black border" label>
                                    {{ categoriesStore.getCategoryDisplay(rule.category) }}
                                </v-chip>
                            </div>
                        </div>

                        <!-- Keywords Box -->
                        <div class="inset-glass-metric pa-4 border-thin mb-4">
                            <div class="d-flex flex-wrap gap-2">
                                <v-chip v-for="(k, idx) in rule.keywords.slice(0, 6)" :key="idx" size="x-small"
                                    variant="flat" border class="font-mono font-weight-black bg-surface opacity-80">
                                    {{ k }}
                                </v-chip>
                                <v-chip v-if="rule.keywords.length > 6" size="x-small" variant="text"
                                    class="text-primary font-weight-black">
                                    +{{ rule.keywords.length - 6 }} more
                                </v-chip>
                                <div v-if="rule.keywords.length === 0" class="text-caption italic opacity-40">No
                                    keywords defined</div>
                            </div>
                        </div>
                    </div>

                    <v-divider class="opacity-10" />

                    <!-- Bottom Actions (Refined) -->
                    <div class="pa-4 d-flex align-center justify-space-between bg-transparent">
                        <v-btn variant="outlined" color="primary"
                            class="rounded-lg border-thin font-weight-black text-none"
                            style="height: 36px; min-width: 36px; padding: 0"
                            @click="handleApplyRuleRetrospectively(rule.id)">
                            <Zap :size="16" class="mr-1" />
                            <v-tooltip activator="parent" location="top">Apply Retrospectively</v-tooltip>
                        </v-btn>
                        <div class="d-flex gap-2">
                            <v-btn variant="outlined" color="primary" class="rounded-lg border-thin"
                                style="height: 36px; min-width: 36px; padding: 0" @click="openEditRuleModal(rule)">
                                <Pencil :size="18" />
                                <v-tooltip activator="parent" location="top">Edit</v-tooltip>
                            </v-btn>
                            <v-btn variant="outlined" color="error" class="rounded-lg border-thin"
                                style="height: 36px; min-width: 36px; padding: 0" @click="deleteRule(rule.id)">
                                <Trash2 :size="18" />
                                <v-tooltip activator="parent" location="top">Delete</v-tooltip>
                            </v-btn>
                        </div>
                    </div>

                    <!-- Subtle background icon -->
                    <div class="card-bg-icon-standard">
                        <Filter :size="120" />
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Add/Edit Rule Modal -->
        <v-dialog v-model="showRuleModal" max-width="550px" persistent>
            <v-card class="premium-glass-card no-hover" rounded="xl">
                <v-card-title class="pa-6 border-b d-flex align-center">
                    <div class="d-flex align-center gap-3 flex-grow-1">
                        <v-avatar color="primary" rounded="lg" size="44" class="elevation-4">
                            <FileText :size="24" class="text-white" />
                        </v-avatar>
                        <div>
                            <div class="text-overline font-weight-black opacity-60 line-height-1 mb-1">
                                {{ isEditingRule ? 'Logic Update' : 'New Intelligence Rule' }}
                            </div>
                            <div class="text-h6 font-weight-black line-height-1 truncate" style="max-width: 300px;">
                                {{ newRule.name || 'Set Classification Logic' }}
                            </div>
                        </div>
                    </div>
                    <v-btn icon variant="text" size="small" @click="showRuleModal = false" color="slate-400">
                        <X :size="20" />
                        <v-tooltip activator="parent" location="top">Close</v-tooltip>
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-6">
                    <v-form @submit.prevent="saveRule">
                        <v-row>
                            <v-col cols="12">
                                <v-text-field v-model="newRule.name" label="Rule Identifier" variant="outlined"
                                    rounded="lg" placeholder="e.g. Swiggy Orders" required hide-details
                                    class="font-weight-black text-h6" density="comfortable" />
                            </v-col>

                            <v-col cols="12">
                                <v-select v-model="newRule.category" label="Target Category" variant="outlined"
                                    rounded="lg"
                                    :items="categoriesStore.categories.map(c => ({ title: `${c.icon || '🏷️'} ${c.name}`, value: c.name }))"
                                    placeholder="Select Category" required hide-details class="font-weight-black"
                                    density="comfortable" />
                            </v-col>

                            <v-col cols="12">
                                <v-textarea v-model="newRule.keywords" label="Trigger Keywords (Comma separated)"
                                    variant="outlined" rounded="lg" placeholder="swiggy, zomato, food delivery" rows="3"
                                    hide-details class="font-weight-bold" density="comfortable" />
                                <div class="text-caption font-weight-medium opacity-50 mt-2 ml-1">
                                    Matches any transaction description containing these terms.
                                </div>
                            </v-col>

                            <v-col cols="12">
                                <v-card variant="tonal" color="error" rounded="lg" class="pa-1">
                                    <v-switch v-model="newRule.exclude_from_reports" color="error" inset hide-details
                                        class="px-4">
                                        <template v-slot:label>
                                            <div class="ml-2 py-2">
                                                <div class="text-subtitle-2 font-weight-black line-height-1 mb-1">Hide
                                                    from reports</div>
                                                <div class="text-caption font-weight-bold opacity-70">Exclude from
                                                    dashboard analytics and monthly totals.</div>
                                            </div>
                                        </template>
                                    </v-switch>
                                </v-card>
                            </v-col>
                        </v-row>
                    </v-form>
                </v-card-text>

                <v-card-actions class="pa-6 pt-0">
                    <v-spacer />
                    <v-btn variant="text" @click="showRuleModal = false" class="text-none px-8 font-weight-black"
                        rounded="pill">
                        Cancel
                        <v-tooltip activator="parent" location="top">Discard changes</v-tooltip>
                    </v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none px-10 btn-primary-glow font-weight-black"
                        @click="saveRule" size="large">
                        Save Intelligence
                        <v-tooltip activator="parent" location="top">Save rule changes</v-tooltip>
                    </v-btn>
                </v-card-actions>
            </v-card>
        </v-dialog>

        <!-- Confirmation Dialogs -->
        <!-- Delete Rule -->
        <v-dialog v-model="showRuleDeleteConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl">
                <v-avatar color="error" variant="tonal" size="80" class="mb-6 mx-auto">
                    <Trash2 :size="48" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Delete Classification Rule?</h3>
                <p class="text-subtitle-1 font-weight-medium opacity-60 mb-8">
                    Future transactions matched by this rule will become uncategorized.
                </p>
                <v-row>
                    <v-col cols="6">
                        <v-btn block variant="text" rounded="pill" class="text-none font-weight-black" height="48"
                            @click="showRuleDeleteConfirm = false">
                            Cancel
                            <v-tooltip activator="parent" location="top">Keep this rule</v-tooltip>
                        </v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn block color="error" rounded="pill" class="text-none font-weight-black" height="48"
                            @click="confirmDeleteRule">
                            Yes, Delete
                            <v-tooltip activator="parent" location="top">Permanently delete rule</v-tooltip>
                        </v-btn>
                    </v-col>
                </v-row>
            </v-card>
        </v-dialog>

        <!-- Exclude confirmation -->
        <v-dialog v-model="showExcludeConfirm" max-width="450px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl">
                <v-avatar color="amber" variant="tonal" size="80" class="mb-6 mx-auto">
                    <EyeOff :size="48" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Invisible in Reports?</h3>
                <p class="text-subtitle-1 font-weight-medium opacity-60 mb-8">
                    Transactions matching this rule will be hidden from monthly totals and charts.
                </p>
                <div class="d-flex gap-3">
                    <v-btn variant="text" rounded="pill" class="text-none font-weight-black flex-grow-1" height="48"
                        @click="showExcludeConfirm = false">
                        Back
                        <v-tooltip activator="parent" location="top">Return to editing</v-tooltip>
                    </v-btn>
                    <v-btn color="primary" rounded="pill" class="text-none font-weight-black flex-grow-1 elevation-4"
                        height="48" @click="confirmSaveRule">
                        Confirm & Save
                        <v-tooltip activator="parent" location="top">Confirm and save rule</v-tooltip>
                    </v-btn>
                </div>
            </v-card>
        </v-dialog>

        <!-- Apply Retro -->
        <v-dialog v-model="showApplyRuleConfirm" max-width="500px" persistent>
            <v-card class="premium-glass-card no-hover text-center pa-8" rounded="xl">
                <v-avatar color="primary" variant="tonal" size="80" class="mb-6 mx-auto">
                    <Zap :size="48" />
                </v-avatar>
                <h3 class="text-h5 font-weight-black mb-2">Retroactive Application</h3>
                <p class="text-subtitle-1 font-weight-medium opacity-60 mb-4">
                    Scan your history and apply this logic to matching records?
                </p>

                <!-- Override Switch -->
                <div class="d-flex justify-center mb-6">
                    <v-card variant="tonal" color="primary" rounded="pill" class="pa-1 pr-4 border-thin">
                        <v-switch v-model="rulesStore.overrideExisting" color="primary" inset hide-details
                            density="compact" @update:model-value="refetchPreview">
                            <template v-slot:label>
                                <span class="text-caption font-weight-black ml-2">Override existing categories</span>
                            </template>
                        </v-switch>
                        <v-tooltip activator="parent" location="top">If on, updates all matches. If off, only
                            uncategorized.</v-tooltip>
                    </v-card>
                </div>

                <v-expand-transition>
                    <div v-if="rulesStore.previewLoading" class="py-8">
                        <v-progress-circular indeterminate color="primary" size="32" />
                        <div class="mt-2 text-caption font-weight-bold opacity-60">Scanning history...</div>
                    </div>
                    <div v-else-if="rulesStore.matchingCount > 0" class="mb-8">
                        <div class="inset-glass-metric pa-4 border-thin text-left">
                            <div
                                class="d-flex align-center justify-space-between mb-3 text-caption font-weight-black opacity-60">
                                <span>Preview (Latest 5 of {{ rulesStore.matchingCount }})</span>
                                <v-chip size="x-small" color="primary" variant="flat" border>
                                    {{ rulesStore.matchingCount }} matches
                                </v-chip>
                            </div>
                            <div class="d-flex flex-column gap-2">
                                <div v-for="txn in rulesStore.matchingPreview" :key="txn.id"
                                    class="d-flex justify-space-between align-center border-b pb-2 last-no-border opacity-90">
                                    <div class="min-w-0 pr-2">
                                        <div class="text-caption font-weight-black truncate">{{ txn.description ||
                                            txn.recipient
                                            }}</div>
                                        <div class="text-extra-small opacity-50">
                                            {{ new Date(txn.date).toLocaleDateString() }}
                                            <v-chip v-if="txn.category && txn.category !== 'Uncategorized'"
                                                size="x-small" variant="text" color="primary"
                                                class="px-1 font-weight-bold">
                                                · {{ txn.category }}
                                            </v-chip>
                                        </div>
                                    </div>
                                    <div class="text-caption font-weight-black shrink-0"
                                        :class="txn.amount < 0 ? 'text-error' : 'text-success'">
                                        {{ txn.amount < 0 ? '-' : '' }}₹{{ Math.abs(txn.amount).toLocaleString() }}
                                            </div>
                                    </div>
                                </div>

                                <!-- Pagination -->
                                <div v-if="rulesStore.matchingCount > rulesStore.previewLimit"
                                    class="mt-4 d-flex justify-center">
                                    <v-pagination v-model="rulesStore.previewPage"
                                        :length="Math.ceil(rulesStore.matchingCount / rulesStore.previewLimit)"
                                        :total-visible="3" density="compact" variant="flat" color="primary"
                                        active-color="primary" size="small" @update:model-value="handlePageChange" />
                                </div>
                            </div>
                        </div>
                        <div v-else-if="!rulesStore.previewLoading"
                            class="mb-8 text-center text-caption font-weight-black text-amber">
                            <AlertCircle :size="16" class="mr-1 inline-block vertical-align-middle" />
                            No matching transactions found.
                        </div>
                </v-expand-transition>

                <v-row>
                    <v-col cols="6">
                        <v-btn block variant="text" rounded="pill" class="text-none font-weight-black" height="48"
                            @click="showApplyRuleConfirm = false">
                            Cancel
                            <v-tooltip activator="parent" location="top">Don't run logic</v-tooltip>
                        </v-btn>
                    </v-col>
                    <v-col cols="6">
                        <v-btn block color="primary" rounded="pill" class="text-none font-weight-black elevation-4"
                            height="48" @click="confirmApplyRule"
                            :disabled="rulesStore.matchingCount === 0 || rulesStore.previewLoading">
                            Run Logic
                            <v-tooltip activator="parent" location="top">Scan history now</v-tooltip>
                        </v-btn>
                    </v-col>
                </v-row>
            </v-card>
        </v-dialog>
    </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRulesStore } from '@/stores/finance/rules'
import { useCategoriesStore } from '@/stores/finance/categories'
import { useNotificationStore } from '@/stores/notification'
import {
    Search,
    Plus,
    Pencil,
    Trash2,
    Zap,
    Filter,
    X,
    Check,
    AlertCircle,
    EyeOff,
    Sparkles,
    FileText,
    Download,
    Upload
} from 'lucide-vue-next'

const rulesStore = useRulesStore()
const categoriesStore = useCategoriesStore()
const notify = useNotificationStore()

// Local UI State (Modals)
const showRuleModal = ref(false)
const showExcludeConfirm = ref(false)
const showRuleDeleteConfirm = ref(false)
const showApplyRuleConfirm = ref(false)
const ruleToDelete = ref<string | null>(null)
const ruleToApply = ref<string | null>(null)
const isEditingRule = ref(false)
const editingRuleId = ref<string | null>(null)

const newRule = ref({
    name: '',
    category: '',
    keywords: '',
    exclude_from_reports: false
})

onMounted(() => {
    rulesStore.fetchRules()
    rulesStore.fetchSuggestions()
    if (categoriesStore.categories.length === 0) {
        categoriesStore.fetchCategories()
    }
})

function openAddRuleModal() {
    isEditingRule.value = false
    editingRuleId.value = null
    newRule.value = { name: '', category: '', keywords: '', exclude_from_reports: false }
    showRuleModal.value = true
}

function openEditRuleModal(rule: any) {
    isEditingRule.value = true
    editingRuleId.value = rule.id
    newRule.value = {
        name: rule.name,
        category: rule.category,
        keywords: rule.keywords.join(', '),
        exclude_from_reports: rule.exclude_from_reports || false
    }
    showRuleModal.value = true
}

function openSuggestionModal(s: any) {
    isEditingRule.value = false
    editingRuleId.value = null
    newRule.value = {
        name: s.name,
        category: s.category,
        keywords: s.keywords.join(', '),
        exclude_from_reports: false
    }
    showRuleModal.value = true
}

async function saveRule() {
    if (!newRule.value.name || !newRule.value.category || !newRule.value.keywords) return

    if (newRule.value.exclude_from_reports) {
        showExcludeConfirm.value = true
        return
    }

    await confirmSaveRule()
}

async function confirmSaveRule() {
    const keywordList = newRule.value.keywords.split(',').map(k => k.trim())
    const payload = {
        ...newRule.value,
        keywords: keywordList,
        priority: 10
    }

    let success = false
    if (isEditingRule.value && editingRuleId.value) {
        success = await rulesStore.updateRule(editingRuleId.value, payload)
        if (success && newRule.value.exclude_from_reports) {
            notify.success(`Rule updated! Matching transactions will be hidden from reports.`)
        }
    } else {
        success = await rulesStore.createRule(payload)
        if (success && newRule.value.exclude_from_reports) {
            notify.success(`Rule saved! Future transactions will be hidden from reports.`)
        }
    }

    if (success) {
        showRuleModal.value = false
        showExcludeConfirm.value = false
        newRule.value = { name: '', category: '', keywords: '', exclude_from_reports: false }
    }
}

function deleteRule(id: string) {
    ruleToDelete.value = id
    showRuleDeleteConfirm.value = true
}

async function confirmDeleteRule() {
    if (!ruleToDelete.value) return
    const success = await rulesStore.deleteRule(ruleToDelete.value)
    if (success) {
        showRuleDeleteConfirm.value = false
        ruleToDelete.value = null
    }
}

async function handleApplyRuleRetrospectively(ruleId: string) {
    ruleToApply.value = ruleId
    const rule = rulesStore.rules.find(r => r.id === ruleId)
    if (rule) {
        showApplyRuleConfirm.value = true
        await rulesStore.fetchMatchPreview(rule.keywords)
    }
}

async function confirmApplyRule() {
    if (!ruleToApply.value) return
    const count = await rulesStore.applyRuleRetrospectively(ruleToApply.value)
    if (count !== false) {
        showApplyRuleConfirm.value = false
        ruleToApply.value = null
    }
}

async function refetchPreview() {
    if (!ruleToApply.value) return
    const rule = rulesStore.rules.find(r => r.id === ruleToApply.value)
    if (rule) {
        await rulesStore.fetchMatchPreview(rule.keywords, 1)
    }
}

async function handlePageChange(page: number) {
    if (!ruleToApply.value) return
    const rule = rulesStore.rules.find(r => r.id === ruleToApply.value)
    if (rule) {
        await rulesStore.fetchMatchPreview(rule.keywords, page)
    }
}

const ruleFileInput = ref<HTMLInputElement | null>(null)

function handleRuleImport(event: Event) {
    const input = event.target as HTMLInputElement
    if (input.files && input.files[0]) {
        rulesStore.importRules(input.files[0])
        input.value = '' // Reset
    }
}

defineExpose({
    openAddRuleModal
})
</script>

<style scoped>
.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.animate-in {
    animation: fadeIn 0.4s ease-out;
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

.line-height-1 {
    line-height: 1;
}

.last-no-border:last-child {
    border-bottom: none !important;
}

.text-extra-small {
    font-size: 0.65rem !important;
}

.card-bg-icon-standard {
    position: absolute;
    bottom: -1.5rem;
    right: -1rem;
    font-size: 8rem;
    opacity: 0.03;
    pointer-events: none;
    line-height: 1;
    transform: rotate(-12deg);
    transition: all 0.5s ease;
    z-index: 0;
}

.premium-glass-card:hover .card-bg-icon-standard {
    transform: rotate(0deg) scale(1.1);
    opacity: 0.05;
}

.rules-tabs :deep(.v-btn) {
    border-radius: 12px !important;
    transition: all 0.3s ease;
}

.rules-tabs :deep(.v-tab--selected) {
    background: rgba(var(--v-theme-primary), 0.1);
    color: rgb(var(--v-theme-primary)) !important;
}

.tab-item {
    font-size: 0.9rem !important;
    letter-spacing: 0.5px;
}
</style>
