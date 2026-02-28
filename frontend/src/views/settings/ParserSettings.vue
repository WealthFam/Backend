<template>
    <div class="animate-in">
        <!-- Status Cards -->
        <v-row class="mb-6">
            <v-col cols="12" md="4">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex align-center gap-4">
                        <v-avatar color="emerald-lighten-5" rounded="xl" size="56">
                            <CheckCircle :size="32" class="text-emerald-darken-1" />
                        </v-avatar>
                        <div>
                            <div class="text-subtitle-1 font-weight-bold text-medium-emphasis">Parser Status</div>
                            <div class="text-h6 font-weight-bold"
                                :class="parserStatus.isOnline ? 'text-emerald-darken-1' : 'text-error'">
                                {{ parserStatus.isOnline ? 'Active & Online' : 'Service Down' }}
                            </div>
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" md="4">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex align-center gap-4">
                        <v-avatar color="indigo-lighten-5" rounded="xl" size="56">
                            <Zap :size="32" class="text-indigo-darken-1" />
                        </v-avatar>
                        <div>
                            <div class="text-subtitle-1 font-weight-bold text-medium-emphasis">24h Throughput</div>
                            <div class="text-h6 font-weight-bold">
                                {{ parserStats?.summary?.total_processed || 0 }} <span
                                    class="text-caption text-medium-emphasis">Requests</span>
                            </div>
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" md="4">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex align-center gap-4">
                        <v-avatar color="amber-lighten-5" rounded="xl" size="56">
                            <ShieldCheck :size="32" class="text-amber-darken-3" />
                        </v-avatar>
                        <div>
                            <div class="text-subtitle-1 font-weight-bold text-medium-emphasis">Success Rate</div>
                            <div class="text-h6 font-weight-bold">
                                {{ calculateSuccessRate }}% <span
                                    class="text-caption text-medium-emphasis">accuracy</span>
                            </div>
                        </div>
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <v-row class="mb-12">
            <!-- Parser Configuration -->
            <v-col cols="12" md="8">
                <v-card class="premium-glass-card h-100" elevation="0">
                    <v-card-title class="d-flex align-center gap-3 py-4 px-6 border-b">
                        <v-avatar color="primary" variant="tonal" size="40" rounded>
                            <BrainCircuit :size="24" class="text-primary" />
                        </v-avatar>
                        <span class="text-h6 font-weight-bold">Parser AI Configuration</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <v-alert v-if="appAiMatch" color="success" variant="tonal" class="mb-6" rounded="lg">
                            <template v-slot:prepend>
                                <Sparkles :size="24" class="mr-3" />
                            </template>
                            <div class="d-flex align-center justify-space-between w-100">
                                <span class="font-weight-medium">Synced with App
                                    Intelligence</span>
                                <v-btn variant="text" density="comfortable" color="success"
                                    class="font-weight-bold text-uppercase" @click="handleSync">
                                    Force Resync
                                </v-btn>
                            </div>
                        </v-alert>

                        <v-alert v-else color="amber-lighten-5" theme="light" class="mb-6 border-amber" rounded="lg">
                            <template v-slot:prepend>
                                <span class="text-h5 mr-3">⚠️</span>
                            </template>
                            <div class="d-flex align-center justify-space-between w-100">
                                <span class="text-amber-darken-4 font-weight-medium">Config out of sync with App</span>
                                <v-btn color="amber-darken-3" size="small" variant="flat" class="font-weight-bold"
                                    @click="handleSync">
                                    Fix Now
                                </v-btn>
                            </div>
                        </v-alert>

                        <p class="text-body-2 text-medium-emphasis mb-6">
                            The Parser Engine runs as a separate microservice. Sync your main application's AI settings
                            (Model & API Key) to
                            ensure consistent parsing.
                        </p>

                        <div class="bg-grey-lighten-4 rounded-xl pa-4 mb-6 border">
                            <v-row>
                                <v-col cols="6">
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">
                                        Current Model</div>
                                    <div class="font-mono text-body-2 font-weight-bold">{{ parserAiForm.model_name ||
                                        'Not Configured' }}</div>
                                </v-col>
                                <v-col cols="6">
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">
                                        AI Status</div>
                                    <v-chip :color="parserAiForm.is_enabled ? 'success' : 'grey'" size="small"
                                        variant="flat" class="font-weight-bold">
                                        {{ parserAiForm.is_enabled ? 'ENABLED' : 'DISABLED' }}
                                    </v-chip>
                                </v-col>
                            </v-row>
                        </div>

                        <v-btn block color="primary" size="large" :loading="isSyncing" @click="handleSync"
                            class="font-weight-bold">
                            <template v-slot:prepend>
                                <RefreshCw :size="18" class="mr-1" :class="{ 'spin': isSyncing }" />
                            </template>
                            {{ isSyncing ? 'Syncing...' : 'Sync AI Config to Parser' }}
                        </v-btn>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Performance Breakdown -->
            <v-col cols="12" md="4">
                <v-card class="glass-card h-100" elevation="0">
                    <v-card-title class="d-flex align-center gap-3 py-4 px-6 border-b">
                        <v-avatar color="amber-lighten-5" variant="flat" size="40" rounded>
                            <Activity :size="24" class="text-amber-darken-3" />
                        </v-avatar>
                        <span class="text-h6 font-weight-bold">Performance</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div v-if="parserStats?.parser_performance" class="d-flex flex-column gap-4">
                            <div v-for="(count, parser) in parserStats.parser_performance" :key="parser">
                                <div class="d-flex justify-space-between text-caption font-weight-bold mb-1">
                                    <span>{{ parser }}</span>
                                    <span class="text-medium-emphasis">{{ count }} hits</span>
                                </div>
                                <v-progress-linear :model-value="(count / parserStats.summary.total_processed * 100)"
                                    color="primary" height="6" rounded></v-progress-linear>
                            </div>
                        </div>
                        <div v-else class="text-center text-medium-emphasis py-4">No performance data available</div>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>

        <!-- Parser History -->
        <v-card class="premium-glass-card mb-12" elevation="0">
            <v-card-title class="d-flex align-center justify-space-between py-4 px-6">
                <div class="d-flex align-center gap-3">
                    <v-avatar color="indigo-lighten-5" variant="flat" size="40" rounded>
                        <ClipboardList :size="24" class="text-indigo" />
                    </v-avatar>
                    <div class="text-h6 font-weight-bold">Parser Request History</div>
                </div>
                <div class="d-flex align-center gap-2">
                    <v-chip size="small" variant="flat" color="grey-lighten-3" class="font-mono">
                        Total: {{ parserLogPagination.total }}
                    </v-chip>
                    <v-btn icon variant="text" density="comfortable" @click="fetchParserData(undefined, true)">
                        <RefreshCw :size="18" />
                    </v-btn>
                </div>
            </v-card-title>

            <v-divider></v-divider>

            <v-table class="bg-transparent">
                <thead>
                    <tr>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase"
                            style="width: 140px;">Time
                        </th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase"
                            style="width: 100px;">
                            Source</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase"
                            style="width: 100px;">
                            Status</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Input Preview</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Extracted Details
                        </th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="log in parserLogs" :key="log.id" class="hover-row">
                        <td class="text-caption font-mono text-medium-emphasis">{{ formatDate(log.created_at).meta }}
                        </td>
                        <td>
                            <v-chip size="x-small" variant="flat"
                                class="font-weight-bold text-uppercase bg-grey-lighten-4 border">
                                {{ log.source }}
                            </v-chip>
                        </td>
                        <td>
                            <v-chip size="x-small" :color="log.status === 'success' ? 'emerald-lighten-5' : 'error'"
                                :class="log.status === 'success' ? 'text-emerald-darken-2' : ''" variant="flat"
                                class="font-weight-bold text-uppercase">
                                {{ log.status }}
                            </v-chip>
                            <div v-if="log.error_message" class="text-caption text-error text-truncate mt-1"
                                style="max-width: 100px;" :title="log.error_message">
                                {{ log.error_message }}
                            </div>
                        </td>
                        <td class="text-caption text-medium-emphasis">
                            <div class="text-truncate" style="max-width: 300px;"
                                :title="JSON.stringify(log.input_payload)">
                                {{ log.input_payload?.message || log.input_payload?.body || log.input_payload?.content
                                    || 'Raw Input' }}
                            </div>
                        </td>
                        <td class="text-caption">
                            <div v-if="log.output_payload">
                                <div v-if="log.output_payload.results?.length > 1"
                                    class="font-weight-bold text-primary mb-1">
                                    📦 {{ log.output_payload.results.length }} items
                                </div>
                                <div v-if="log.output_payload.results?.[0]?.transaction">
                                    <div class="font-weight-medium">
                                        {{ log.output_payload.results[0].transaction.merchant?.cleaned ||
                                            log.output_payload.results[0].transaction.description }}
                                    </div>
                                    <div class="text-medium-emphasis">
                                        {{ formatAmount(log.output_payload.results[0].transaction.amount) }}
                                    </div>
                                </div>
                                <div v-else-if="log.output_payload.error" class="text-error font-italic">
                                    {{ log.output_payload.error }}
                                </div>
                                <div v-else class="text-disabled font-italic">No extraction</div>
                            </div>
                            <div v-else class="text-disabled font-italic">No output</div>
                        </td>
                    </tr>
                    <tr v-if="parserLogs.length === 0">
                        <td colspan="5" class="text-center py-8 text-medium-emphasis font-italic">
                            No parser logs found.
                        </td>
                    </tr>
                </tbody>
            </v-table>

            <div v-if="parserLogPagination.total > parserLogPagination.limit"
                class="d-flex align-center justify-space-between pa-4 border-t">
                <span class="text-caption text-medium-emphasis">
                    Showing {{ parserLogPagination.skip + 1 }} - {{ Math.min(parserLogPagination.skip +
                        parserLogPagination.limit, parserLogPagination.total) }}
                </span>
                <div class="d-flex gap-2">
                    <v-btn size="small" variant="outlined" :disabled="parserLogPagination.skip === 0"
                        @click="parserLogPagination.skip -= parserLogPagination.limit; fetchParserData()">
                        Previous
                    </v-btn>
                    <v-btn size="small" variant="outlined"
                        :disabled="parserLogPagination.skip + parserLogPagination.limit >= parserLogPagination.total"
                        @click="parserLogPagination.skip += parserLogPagination.limit; fetchParserData()">
                        Next
                    </v-btn>
                </div>
            </div>
        </v-card>

        <!-- Pattern Management -->
        <div class="mt-8 pt-8 border-t">
            <div class="d-flex align-center justify-space-between mb-6">
                <div>
                    <h2 class="text-h5 font-weight-bold mb-1">Parser Patterns</h2>
                    <p class="text-body-2 text-medium-emphasis">View and manage transaction parser patterns</p>
                </div>
                <v-btn color="primary" @click="openAddModal" prepend-icon="Plus">
                    Add Pattern
                </v-btn>
            </div>

            <v-card class="premium-glass-card" elevation="0">
                <v-card-text v-if="patternsLoading" class="text-center py-8">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                    <div class="mt-2 text-caption">Loading patterns...</div>
                </v-card-text>

                <v-table v-else>
                    <thead>
                        <tr>
                            <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Bank</th>
                            <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Pattern</th>
                            <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Source / ID
                            </th>
                            <th class="text-right text-caption font-weight-bold text-medium-emphasis text-uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="pattern in patterns" :key="pattern.id" class="hover-row">
                            <td>
                                <v-chip color="blue-lighten-4" variant="flat" size="small"
                                    class="font-weight-bold text-blue-darken-3">
                                    {{ pattern.bank_name }}
                                </v-chip>
                            </td>
                            <td class="pattern-cell">
                                <code
                                    class="bg-grey-lighten-4 pa-2 rounded font-mono text-caption text-medium-emphasis d-block pattern-code"
                                    :title="pattern.regex_pattern">
                            {{ pattern.regex_pattern }}
                        </code>
                            </td>
                            <td>
                                <div class="d-flex flex-column gap-1">
                                    <v-chip v-if="pattern.is_ai_generated" size="x-small" color="secondary"
                                        variant="tonal" class="font-weight-bold w-fit">
                                        AI
                                    </v-chip>
                                    <v-chip v-else size="x-small" color="grey" variant="tonal"
                                        class="font-weight-bold w-fit">
                                        Manual
                                    </v-chip>
                                    <span class="text-caption font-mono text-disabled">{{ pattern.id.substring(0, 8)
                                        }}</span>
                                </div>
                            </td>
                            <td class="text-right">
                                <v-btn icon density="comfortable" variant="text" color="medium-emphasis"
                                    @click.stop="openEditModal(pattern)">
                                    <Edit2 :size="16" />
                                </v-btn>
                                <v-btn icon density="comfortable" variant="text" color="error"
                                    @click.stop="confirmDelete(pattern)">
                                    <Trash2 :size="16" />
                                </v-btn>
                            </td>
                        </tr>
                        <tr v-if="patterns.length === 0">
                            <td colspan="4" class="text-center py-8 text-medium-emphasis font-italic">
                                <div class="d-flex flex-column align-center gap-2">
                                    <ClipboardList :size="48" class="opacity-20" />
                                    No patterns found
                                </div>
                            </td>
                        </tr>
                    </tbody>
                </v-table>
            </v-card>
        </div>

        <!-- Add/Edit Pattern Modal -->
        <v-dialog v-model="showPatternModal" max-width="600">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">{{ isEditingPattern ? 'Edit Pattern' : 'New Pattern'
                        }}</span>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showPatternModal = false"></v-btn>
                </v-card-title>
                <v-card-text class="pa-6">
                    <v-form @submit.prevent="savePattern">
                        <v-text-field v-model="patternForm.bank_name" label="Bank / Application Name"
                            placeholder="e.g. HDFC Bank" variant="outlined" required
                            :disabled="isEditingPattern && patternForm.is_ai_generated" class="mb-4"></v-text-field>

                        <v-textarea v-model="patternForm.regex_pattern" label="Regex Pattern"
                            placeholder="Regex to capture transactions..." variant="outlined" rows="3"
                            class="font-mono text-body-2 mb-4" required></v-textarea>

                        <v-text-field v-model="patternForm.date_format" label="Date Format (Optional)"
                            placeholder="e.g. %d-%b-%y for 14-Feb-26" variant="outlined" density="comfortable"
                            class="font-mono text-body-2 mb-4" hint="Python datetime format string"
                            persistent-hint></v-text-field>

                        <v-textarea v-model="patternForm.field_mapping_str" label="Field Mapping (JSON)"
                            placeholder='{"amount": 1, "merchant": 2}' variant="outlined" rows="3"
                            class="font-mono text-body-2 mb-1" hint="Map fields to regex groups (1-based index)"
                            persistent-hint></v-textarea>

                        <v-text-field v-model.number="patternForm.confidence" label="Confidence Score (0.0 - 1.0)"
                            type="number" step="0.1" min="0" max="1" variant="outlined"
                            class="mt-6 mb-4"></v-text-field>

                        <v-alert v-if="patternError" type="error" variant="tonal" class="mb-4">
                            {{ patternError }}
                        </v-alert>

                        <div class="d-flex justify-end gap-3 pt-2">
                            <v-btn variant="text" @click="showPatternModal = false">Cancel</v-btn>
                            <v-btn type="submit" color="primary" :loading="patternSaving">
                                {{ isEditingPattern ? 'Update Pattern' : 'Create Pattern' }}
                            </v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>
        <!-- Alias Management -->
        <div class="mt-8 pt-8 border-t">
            <div class="d-flex align-center justify-space-between mb-6">
                <div>
                    <h2 class="text-h5 font-weight-bold mb-1">Merchant Aliases</h2>
                    <p class="text-body-2 text-medium-emphasis">Normalize merchant names (e.g. "AMZN Mktp" -> "Amazon")
                    </p>
                </div>
                <v-btn color="secondary" @click="openAliasModal" prepend-icon="Plus">
                    Add Alias
                </v-btn>
            </div>

            <v-card class="premium-glass-card" elevation="0">
                <v-card-text v-if="aliasesLoading" class="text-center py-8">
                    <v-progress-circular indeterminate color="primary"></v-progress-circular>
                </v-card-text>

                <v-table v-else>
                    <thead>
                        <tr>
                            <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Pattern</th>
                            <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Clean Alias
                            </th>
                            <th class="text-right text-caption font-weight-bold text-medium-emphasis text-uppercase">
                                Actions
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="alias in aliases" :key="alias.id" class="hover-row">
                            <td class="font-mono text-caption">{{ alias.pattern }}</td>
                            <td class="font-weight-bold text-primary">{{ alias.alias }}</td>
                            <td class="text-right">
                                <v-btn icon density="compact" variant="text" color="medium-emphasis"
                                    @click.stop="openAliasModal(alias)">
                                    <Edit2 :size="16" />
                                </v-btn>
                                <v-btn icon density="compact" variant="text" color="error"
                                    @click.stop="confirmDeleteAlias(alias)">
                                    <Trash2 :size="16" />
                                </v-btn>
                            </td>
                        </tr>
                        <tr v-if="aliases.length === 0">
                            <td colspan="3" class="text-center py-8 text-medium-emphasis font-italic">
                                No aliases found
                            </td>
                        </tr>
                    </tbody>
                </v-table>
            </v-card>
        </div>

        <!-- Add Alias Modal -->
        <v-dialog v-model="showAliasModal" max-width="500">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">New Merchant Alias</span>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showAliasModal = false"></v-btn>
                </v-card-title>
                <v-card-text class="pa-6">
                    <v-form @submit.prevent="saveAlias">
                        <v-text-field v-model="aliasForm.pattern" label="Raw Text Pattern" placeholder="e.g. AMZN MKTP"
                            variant="outlined" class="mb-4" hint="Matches if this text appears in description"
                            persistent-hint required @update:model-value="checkAliasImpact"></v-text-field>

                        <v-text-field v-model="aliasForm.alias" label="Clean Merchant Name" placeholder="e.g. Amazon"
                            variant="outlined" class="mb-6" required></v-text-field>

                        <v-checkbox v-model="aliasForm.update_past" color="primary" hide-details class="mb-2">
                            <template v-slot:label>
                                <div>
                                    <div class="font-weight-bold">Update past transactions?</div>
                                    <div class="text-caption text-medium-emphasis" v-if="aliasImpact !== null">
                                        Will update approx. <strong>{{ aliasImpact }}</strong> transactions
                                    </div>
                                    <div class="text-caption text-medium-emphasis" v-else>
                                        Select to verify impact on history
                                    </div>
                                </div>
                            </template>
                        </v-checkbox>

                        <div class="d-flex justify-end gap-3 pt-4">
                            <v-btn variant="text" @click="showAliasModal = false">Cancel</v-btn>
                            <v-btn type="submit" color="primary" :loading="aliasSaving">
                                Create Rule
                            </v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Alias Delete Confirmation -->
        <v-dialog v-model="showAliasDeleteConfirm" max-width="400">
            <v-card class="rounded-xl">
                <v-card-text class="text-center pa-6">
                    <div class="text-h2 mb-4">🗑️</div>
                    <div class="text-h6 font-weight-bold mb-2">Delete Alias?</div>
                    <p class="text-body-2 text-medium-emphasis mb-6">
                        Are you sure you want to delete the alias for <span class="font-weight-bold text-primary">{{
                            aliasToDelete?.alias }}</span>? This will not affect past transactions.
                    </p>
                    <div class="d-flex justify-center gap-3">
                        <v-btn variant="text" @click="showAliasDeleteConfirm = false">Cancel</v-btn>
                        <v-btn color="error" @click="executeDeleteAlias" prepend-icon="Trash2">
                            Delete
                        </v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>

    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import {
    CheckCircle, Zap, ShieldCheck, BrainCircuit, Activity, RefreshCw, ClipboardList, Edit2, Trash2, Sparkles
} from 'lucide-vue-next'
import { parserApi, financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useConfirmStore } from '@/stores/confirm'
import { useAiStore } from '@/stores/ai'
import { useCurrency } from '@/composables/useCurrency'

const aiStore = useAiStore()
const { formatAmount } = useCurrency()
const notify = useNotificationStore()
const confirmDialog = useConfirmStore()

// --- Internal State ---
const parserStatus = ref({ isOnline: false })
const isSyncing = ref(false)
const parserStats = ref<any>(null)
const parserLogs = ref<any[]>([])
const parserAiForm = ref({
    is_enabled: false,
    model_name: 'models/gemini-1.5-flash',
    api_key: ''
})
const parserLogPagination = ref({ limit: 10, skip: 0, total: 0 })

// --- Pattern Management State ---
const patterns = ref<any[]>([])
const patternsLoading = ref(false)
const patternSaving = ref(false)
const patternError = ref<string | null>(null)
const showPatternModal = ref(false)
const isEditingPattern = ref(false)
const patternForm = reactive({
    id: null as string | null,
    bank_name: '',
    regex_pattern: '',
    field_mapping_str: '{}',
    date_format: '',
    confidence: 1.0,
    is_ai_generated: false
})

// --- Computed ---
const calculateSuccessRate = computed(() => {
    if (!parserStats.value?.summary?.total_processed) return 0
    const success = parserStats.value.summary.status_breakdown?.success || 0
    return Math.round((success / parserStats.value.summary.total_processed) * 100)
})

const appAiMatch = computed(() => {
    // Check if app Gemini config matches parser Gemini config
    return aiStore.aiForm.model_name === parserAiForm.value.model_name &&
        aiStore.aiForm.is_enabled === parserAiForm.value.is_enabled
})

// --- Methods ---
const fetchParserData = async (sourceFilter?: string, resetSkip = false) => {
    if (resetSkip) parserLogPagination.value.skip = 0

    try {
        const [health, stats, logs, config] = await Promise.all([
            parserApi.getHealth(),
            parserApi.getStats(),
            parserApi.getLogs({
                limit: parserLogPagination.value.limit,
                offset: parserLogPagination.value.skip,
                source: sourceFilter
            }),
            parserApi.getAiConfig()
        ])
        parserStatus.value.isOnline = health.data?.status === 'ok'
        parserStats.value = stats.data || null
        parserLogs.value = logs.data?.logs || []
        parserLogPagination.value.total = logs.data?.total || 0

        parserAiForm.value = {
            is_enabled: config.data.is_enabled || false,
            model_name: config.data.model_name || 'models/gemini-1.5-flash',
            api_key: ''
        }
    } catch (e) {
        parserStatus.value.isOnline = false
        console.error("Failed to fetch parser data", e)
    }
}

async function handleSync() {
    if (!aiStore.aiForm.has_api_key && !aiStore.aiForm.api_key) {
        notify.warning("App AI is not configured.")
        return
    }

    try {
        isSyncing.value = true
        await financeApi.syncAiToParser()
        notify.success("Synced App AI Settings to Parser")
        fetchParserData()
    } catch (e) {
        notify.error("Sync failed: Check if parser microservice is online")
    } finally {
        isSyncing.value = false
    }
}

function formatDate(dateStr: string) {
    if (!dateStr) return { day: 'N/A', meta: '' }
    const d = new Date(dateStr)
    return {
        day: d.toLocaleDateString(),
        meta: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        full: d.toLocaleString()
    }
}

// --- Pattern Management Methods ---
async function loadPatterns() {
    patternsLoading.value = true
    try {
        const res = await parserApi.getPatterns({ limit: 100 })
        patterns.value = res.data.patterns
    } catch (err) {
        console.error('Failed to load patterns:', err)
        notify.error("Failed to load patterns")
    } finally {
        patternsLoading.value = false
    }
}

function openAddModal() {
    isEditingPattern.value = false
    patternForm.id = null
    patternForm.bank_name = ''
    patternForm.regex_pattern = ''
    patternForm.date_format = ''
    patternForm.field_mapping_str = '{\n  "amount": 1,\n  "merchant": 2,\n  "date": 3\n}'
    patternForm.confidence = 1.0
    patternForm.is_ai_generated = false
    patternError.value = null
    showPatternModal.value = true
}

function openEditModal(pattern: any) {
    try {
        isEditingPattern.value = true
        patternForm.id = pattern.id
        patternForm.bank_name = pattern.bank_name
        patternForm.regex_pattern = pattern.regex_pattern
        patternForm.date_format = pattern.date_format || ''

        const mapping = pattern.field_mapping || {}
        patternForm.field_mapping_str = JSON.stringify(mapping, null, 2)

        patternForm.confidence = pattern.confidence !== undefined ? pattern.confidence : 1.0
        patternForm.is_ai_generated = !!pattern.is_ai_generated
        patternError.value = null
        showPatternModal.value = true
    } catch (e) {
        console.error("Error opening edit modal:", e)
        notify.error("Failed to open edit modal")
    }
}

async function savePattern() {
    patternSaving.value = true
    patternError.value = null

    try {
        let mapping = {}
        try {
            mapping = JSON.parse(patternForm.field_mapping_str)
        } catch (e) {
            patternError.value = "Invalid JSON in Field Mapping"
            patternSaving.value = false
            return
        }

        const payload = {
            bank_name: patternForm.bank_name,
            regex_pattern: patternForm.regex_pattern,
            field_mapping: mapping,
            date_format: patternForm.date_format || null,
            confidence: patternForm.confidence
        }

        if (isEditingPattern.value && patternForm.id) {
            await parserApi.updatePattern(patternForm.id, payload)
            notify.success("Pattern updated")
        } else {
            await parserApi.createPattern(payload)
            notify.success("Pattern created")
        }

        showPatternModal.value = false
        loadPatterns()
    } catch (err: any) {
        console.error("Save failed", err)
        patternError.value = err.response?.data?.detail || "Failed to save pattern"
    } finally {
        patternSaving.value = false
    }
}

async function confirmDelete(pattern: any) {
    const isConfirmed = await confirmDialog.prompt(`Are you sure you want to delete the pattern for ${pattern.bank_name}?`, 'Delete Pattern', 'Delete', 'Cancel')
    if (!isConfirmed) return

    try {
        await parserApi.deletePattern(pattern.id)
        notify.success("Pattern deleted")
        loadPatterns()
    } catch (err) {
        notify.error("Failed to delete pattern")
    }
}

onMounted(() => {
    fetchParserData()
    if (!aiStore.aiForm.model_name) {
        aiStore.fetchAiSettings()
    }
    loadPatterns()
    loadAliases()
})

// --- Alias Management ---
const aliases = ref<any[]>([])
const aliasesLoading = ref(false)
const showAliasModal = ref(false)
const aliasSaving = ref(false)
const aliasImpact = ref<number | null>(null)
const isEditingAlias = ref(false)
const showAliasDeleteConfirm = ref(false)
const aliasToDelete = ref<any>(null)

const aliasForm = reactive({
    id: null as string | null,
    pattern: '',
    alias: '',
    update_past: false
})

async function loadAliases() {
    aliasesLoading.value = true
    try {
        const res2 = await financeApi.getAliases()
        aliases.value = res2.data
    } catch (err) {
        console.error('Failed to load aliases:', err)
        aliases.value = []
    } finally {
        aliasesLoading.value = false
    }
}

let impactDebounce: any = null
function checkAliasImpact() {
    if (!aliasForm.pattern) {
        aliasImpact.value = null
        return
    }
    if (impactDebounce) clearTimeout(impactDebounce)
    impactDebounce = setTimeout(async () => {
        try {
            const res = await financeApi.previewAliasImpact(aliasForm.pattern)
            aliasImpact.value = res.data.match_count
        } catch (e) {
            console.error(e)
        }
    }, 500)
}

function openAliasModal(alias?: any) {
    if (alias) {
        isEditingAlias.value = true
        aliasForm.id = alias.id
        aliasForm.pattern = alias.pattern
        aliasForm.alias = alias.alias
        aliasForm.update_past = false
    } else {
        isEditingAlias.value = false
        aliasForm.id = null
        aliasForm.pattern = ''
        aliasForm.alias = ''
        aliasForm.update_past = false
    }
    // Calculate impact immediately for both create and edit
    aliasImpact.value = null
    checkAliasImpact()
    showAliasModal.value = true
}

async function saveAlias() {
    aliasSaving.value = true
    try {
        if (isEditingAlias.value && aliasForm.id) {
            await financeApi.updateAlias(aliasForm.id, {
                pattern: aliasForm.pattern,
                alias: aliasForm.alias,
                update_past_transactions: aliasForm.update_past
            })
            notify.success("Alias updated successfully")
        } else {
            await financeApi.createAlias({
                pattern: aliasForm.pattern,
                alias: aliasForm.alias,
                update_past_transactions: aliasForm.update_past
            })
            notify.success("Alias created successfully")
        }

        if (aliasForm.update_past) {
            notify.info("Background update of transactions started")
        }
        showAliasModal.value = false
        loadAliases()
    } catch (err) {
        notify.error(isEditingAlias.value ? "Failed to update alias" : "Failed to create alias")
    } finally {
        aliasSaving.value = false
    }
}

function confirmDeleteAlias(alias: any) {
    aliasToDelete.value = alias
    showAliasDeleteConfirm.value = true
}

async function executeDeleteAlias() {
    if (!aliasToDelete.value) return

    try {
        await financeApi.deleteAlias(aliasToDelete.value.id)
        notify.success("Alias deleted")
        loadAliases()
    } catch (err) {
        notify.error("Failed to delete alias rule")
    } finally {
        showAliasDeleteConfirm.value = false
        aliasToDelete.value = null
    }
}
</script>

<style scoped>
.glass-card {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.2);
    border-radius: 16px;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.border-emerald {
    border: 1px solid rgb(var(--v-theme-success));
}

.border-amber {
    border: 1px solid rgb(var(--v-theme-warning));
}

.pattern-cell {
    max-width: 0;
    width: 100%;
}

.pattern-code {
    white-space: pre-wrap;
    word-break: break-all;
    font-size: 0.7rem !important;
}

.spin {
    animation: spin 3s linear infinite;
}

@keyframes spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}
</style>
