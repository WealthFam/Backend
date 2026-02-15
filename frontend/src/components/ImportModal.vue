<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useCurrency } from '@/composables/useCurrency'
import {
    FileDown, X, UploadCloud, Lightbulb, FileText,
    Coins, CheckCircle2, Trash2, CheckCircle
} from 'lucide-vue-next'

const { formatAmount } = useCurrency()

const props = defineProps<{
    isOpen: boolean
}>()

const emit = defineEmits(['close', 'import-success'])

const notify = useNotificationStore()

// State
const step = ref(1)
const loading = ref(false)
const accounts = ref<any[]>([])
const selectedAccount = ref('')
const file = ref<File | null>(null)

// Step Labels
const stepLabels = ['Account & File', 'Analysis', 'Mapping', 'Verification']

// Detail Fields
const detailFields = [
    { key: 'date', label: 'Date', icon: '📅', desc: 'Transaction date', optional: false },
    { key: 'description', label: 'Description', icon: '📝', desc: 'Payee or narration', optional: false },
    { key: 'reference', label: 'Reference', icon: '🆔', desc: 'Reference / UTR / Txn #', optional: true },
    { key: 'balance', label: 'Balance', icon: '💰', desc: 'Available balance after txn', optional: true },
    { key: 'credit_limit', label: 'Credit Limit', icon: '💳', desc: 'New credit limit if updated', optional: true },
] as const

// Step 2: Mapping
const mapping = ref({
    date: 'Date',
    description: 'Description',
    reference: '', // Optional
    balance: '', // Optional
    credit_limit: '', // Optional
    amount: 'Amount',
    mode: 'single' as 'single' | 'split'
})
const splitMapping = ref({
    debit: 'Debit',
    credit: 'Credit'
})
const csvHeaders = ref<string[]>([])
const detectedHeaderRow = ref(0)
const previewRows = ref<any[]>([])
const analyzing = ref(false)

// Step 3: Verification
const parsedTxns = ref<any[]>([])
const selectedTxns = ref<Set<number>>(new Set())

// Step 4: Results
const importResult = ref<any>(null)

async function fetchAccounts() {
    try {
        const res = await financeApi.getAccounts()
        accounts.value = res.data
    } catch (e) {
        notify.error("Failed to load accounts")
    }
}

const accountOptionsFlat = computed(() => accounts.value.map(a => ({
    label: `${a.icon || '🏦'} ${a.name} (${a.currency})`,
    value: a.id
})))

// Watch open to load accounts
watch(() => props.isOpen, (val) => {
    if (val) {
        reset()
        fetchAccounts()
    }
})

// Watch account selection to load mapping
watch(selectedAccount, (newVal) => {
    if (newVal) {
        const acc = accounts.value.find(a => a.id === newVal)
        if (acc && acc.import_config) {
            try {
                const config = JSON.parse(acc.import_config)
                mapping.value = { ...mapping.value, ...config.mapping }
                splitMapping.value = { ...splitMapping.value, ...config.splitMapping }
                // Restore mode if saved
                if (config.mode) mapping.value.mode = config.mode

                notify.info("Loaded saved mapping")
            } catch (e) {
                console.error("Failed to parse import config", e)
            }
        }
    }
})

async function handleFileUpload(event: any) {
    const target = event.target || event
    const uploadFile = target.files ? target.files[0] : (target[0] || target)

    if (uploadFile) {
        file.value = uploadFile
        analyzing.value = true

        try {
            const formData = new FormData()
            formData.append('file', file.value as File)

            const res = await financeApi.analyzeCsv(formData)
            const analysis = res.data

            csvHeaders.value = analysis.headers
            detectedHeaderRow.value = analysis.header_row_index
            previewRows.value = analysis.preview

            notify.success(`Detected headers on row ${analysis.header_row_index + 1}`)
            step.value = 2 // Auto-advance to preview

        } catch (e) {
            notify.error("Failed to analyze file. Please check format.")
            console.error(e)
        } finally {
            analyzing.value = false
        }
    }
}

async function parseFile() {
    if (!file.value) return notify.error("Please select a file")

    loading.value = true
    try {
        const formData = new FormData()
        formData.append('file', file.value)

        const mapPayload: any = {
            date: mapping.value.date,
            description: mapping.value.description,
            reference: mapping.value.reference,
            balance: mapping.value.balance,
            credit_limit: mapping.value.credit_limit
        }

        if (mapping.value.mode === 'single') {
            mapPayload.amount = mapping.value.amount
        } else {
            mapPayload.debit = splitMapping.value.debit
            mapPayload.credit = splitMapping.value.credit
        }

        formData.append('mapping', JSON.stringify(mapPayload))
        formData.append('header_row_index', String(detectedHeaderRow.value))

        const res = await financeApi.parseCsv(formData)
        parsedTxns.value = res.data
        selectedTxns.value = new Set(parsedTxns.value.map((_, i) => i))

        step.value = 4
    } catch (e: any) {
        notify.error(e.response?.data?.detail || "Failed to parse file")
    } finally {
        loading.value = false
    }
}

function removeTxn(index: number) {
    selectedTxns.value.delete(index)
}

function toggleSelection(index: number) {
    if (selectedTxns.value.has(index)) {
        selectedTxns.value.delete(index)
    } else {
        selectedTxns.value.add(index)
    }
}

function toggleAllVerify() {
    if (selectedTxns.value.size < parsedTxns.value.length) {
        selectedTxns.value = new Set(parsedTxns.value.map((_, i) => i))
    } else {
        selectedTxns.value.clear()
    }
}

async function importSelected() {
    loading.value = true
    try {
        const finalTxns = parsedTxns.value.filter((_, i) => selectedTxns.value.has(i))
        const source = file.value?.name.endsWith('.csv') ? 'CSV' : 'EXCEL'

        const res = await financeApi.importCsv({
            account_id: selectedAccount.value,
            transactions: finalTxns,
            source: source
        })

        // Save Mapping to Account
        const currentMapping = {
            mapping: {
                date: mapping.value.date,
                description: mapping.value.description,
                reference: mapping.value.reference,
                balance: mapping.value.balance,
                credit_limit: mapping.value.credit_limit,
                amount: mapping.value.amount,
                mode: mapping.value.mode
            },
            splitMapping: {
                debit: splitMapping.value.debit,
                credit: splitMapping.value.credit
            },
            mode: mapping.value.mode
        }

        try {
            await financeApi.updateAccount(selectedAccount.value, {
                import_config: JSON.stringify(currentMapping)
            })
        } catch (e) {
            console.error("Failed to save mapping preference", e)
        }

        importResult.value = res.data
        step.value = 5
        notify.success(`Imported ${res.data.imported} transactions`)
        emit('import-success')
    } catch (e: any) {
        notify.error("Import failed")
    } finally {
        loading.value = false
    }
}

function reset() {
    step.value = 1
    file.value = null
    parsedTxns.value = []
    importResult.value = null
    selectedAccount.value = ''
}

function close() {
    emit('close')
}
</script>

<template>
    <v-dialog :model-value="isOpen" @update:model-value="close" persistent max-width="1100" scrollable>
        <v-card class="premium-import-card rounded-xl overflow-hidden">
            <v-card-title class="pa-0">
                <div class="modal-header-premium pa-4 d-flex align-center justify-space-between text-white">
                    <div class="d-flex align-center ga-3">
                        <FileDown class="text-white" :size="24" />
                        <h2 class="text-h6 font-weight-black">Import Transactions</h2>
                    </div>
                    <v-btn icon variant="text" color="white" density="compact" @click="close">
                        <X :size="24" class="text-white" />
                    </v-btn>
                </div>

                <!-- Stepper Progress Indicator -->
                <div class="stepper-nav pa-4 border-b border-opacity-5 d-flex align-center justify-center gap-4">
                    <div v-for="s in 4" :key="s" class="d-flex align-center gap-2">
                        <div class="step-circle" :class="{ active: step >= s }">{{ s }}</div>
                        <span class="step-label text-caption font-weight-black" :class="{ active: step >= s }">
                            {{ stepLabels[s - 1] }}
                        </span>
                        <div v-if="s < 4" class="step-divider" :class="{ active: step > s }"></div>
                    </div>
                </div>
            </v-card-title>

            <v-card-text class="pa-0 pa-md-6 bg-surface-lighten-5">
                <v-divider v-if="loading" class="mb-4"></v-divider>
                <div v-if="loading" class="d-flex flex-column align-center justify-center py-10">
                    <v-progress-circular indeterminate color="primary" size="64" width="6"></v-progress-circular>
                    <p class="mt-4 text-h6 font-weight-bold opacity-70">Processing transactions...</p>
                </div>

                <div v-else class="import-content-wrapper pa-4 pa-md-0">
                    <!-- Step 1: Account & File Selection -->
                    <v-window v-model="step" class="overflow-visible">
                        <v-window-item :value="1">
                            <v-row>
                                <v-col cols="12" md="6">
                                    <v-label class="text-subtitle-2 font-weight-black mb-2 d-block">Select Target
                                        Account</v-label>
                                    <v-autocomplete v-model="selectedAccount" :items="accountOptionsFlat"
                                        item-title="label" item-value="value"
                                        placeholder="Which bank account is this for?" variant="outlined"
                                        density="comfortable" flat class="premium-select-field" hide-details>

                                    </v-autocomplete>
                                </v-col>
                                <v-col cols="12" md="6">
                                    <v-label class="text-subtitle-2 font-weight-black mb-2 d-block">Upload CSV or
                                        Excel</v-label>
                                    <v-file-input @change="handleFileUpload" accept=".csv, .xlsx, .xls"
                                        variant="outlined" density="comfortable" flat class="premium-file-field"
                                        prepend-icon="" placeholder="Drag and drop or click to browse" hide-details>
                                        <template v-slot:prepend-inner>
                                            <UploadCloud :size="20" class="text-primary mr-2" />
                                        </template>
                                    </v-file-input>
                                </v-col>
                            </v-row>

                            <v-alert border="start" border-color="primary" color="surface" elevation="1"
                                class="mt-10 rounded-xl pa-6">
                                <template v-slot:prepend>
                                    <Lightbulb :size="32" class="text-primary" />
                                </template>
                                <div class="ml-4">
                                    <h4 class="text-h6 font-weight-black mb-1">Pro Tip</h4>
                                    <p class="text-body-2 opacity-70">Once you map your statement columns for an
                                        account, we'll remember them for
                                        your next import! Saving you time and clicks.</p>
                                </div>
                            </v-alert>
                        </v-window-item>

                        <!-- Step 2: File Analysis Preview -->
                        <v-window-item :value="2">
                            <div v-if="analyzing"
                                class="d-flex flex-column align-center justify-center py-10 text-center">
                                <v-progress-circular indeterminate color="primary" size="48"></v-progress-circular>
                                <p class="mt-4 font-weight-bold opacity-70">Analyzing file structure...</p>
                            </div>

                            <div v-else>
                                <v-card
                                    class="bg-surface border-0 rounded-xl pa-4 mb-6 d-flex align-center gap-4 elevation-1">
                                    <div class="text-h4">👀</div>
                                    <div>
                                        <h3 class="text-h6 font-weight-black">Review File Structure</h3>
                                        <p class="text-body-2 opacity-70">
                                            We found <strong>{{ csvHeaders.length }} columns</strong> starting at row
                                            <v-chip size="x-small" color="primary" variant="flat"
                                                class="font-weight-black mx-1">{{
                                                    detectedHeaderRow + 1 }}</v-chip>.
                                        </p>
                                    </div>
                                </v-card>

                                <v-table v-if="previewRows.length > 0"
                                    class="premium-table border rounded-xl overflow-hidden">
                                    <thead>
                                        <tr>
                                            <th v-for="h in csvHeaders" :key="h"
                                                class="text-uppercase text-tiny font-weight-black opacity-60">
                                                {{ h }}
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="(row, idx) in previewRows.slice(0, 3)" :key="idx">
                                            <td v-for="h in csvHeaders" :key="h" class="text-caption opacity-80">{{
                                                row[h] }}</td>
                                        </tr>
                                    </tbody>
                                </v-table>
                            </div>
                        </v-window-item>

                        <!-- Step 3: Column Mapping -->
                        <v-window-item :value="3">
                            <v-row>
                                <!-- Transaction Details Mapping -->
                                <v-col cols="12" md="7">
                                    <v-card variant="outlined"
                                        class="rounded-xl border-opacity-5 pa-4 h-100 bg-surface shadow-sm">
                                        <h4 class="text-subtitle-1 font-weight-black mb-6 d-flex align-center gap-2">
                                            <FileText :size="20" class="text-primary" />
                                            Transaction Details
                                        </h4>

                                        <div class="mapping-grid-premium">
                                            <div v-for="field in detailFields" :key="field.key"
                                                class="mapping-item-row mb-4 d-flex align-center">
                                                <div class="field-info-panel d-flex align-center ga-3 flex-grow-1">
                                                    <div class="field-icon-box">{{ field.icon }}</div>
                                                    <div class="flex-grow-1">
                                                        <div class="text-caption font-weight-black">{{ field.label }}
                                                        </div>
                                                        <div class="text-tiny opacity-60 line-clamp-1">{{ field.desc
                                                        }}</div>
                                                    </div>
                                                </div>
                                                <div class="mapping-arrow mx-4 opacity-30">
                                                    <v-icon size="small">ArrowRight</v-icon>
                                                </div>
                                                <div class="field-select-panel" style="width: 200px;">
                                                    <v-select v-model="mapping[field.key]" :items="csvHeaders"
                                                        placeholder="Choose column..." variant="outlined"
                                                        density="comfortable" flat class="premium-select-field-small"
                                                        hide-details>
                                                        <template v-if="field.optional" v-slot:prepend-item>
                                                            <v-list-item value="" title="-- No Column --"></v-list-item>
                                                        </template>
                                                    </v-select>
                                                </div>
                                            </div>
                                        </div>
                                    </v-card>
                                </v-col>

                                <!-- Financials Mapping -->
                                <v-col cols="12" md="5">
                                    <v-card variant="outlined"
                                        class="rounded-xl border-opacity-5 pa-4 h-100 bg-surface shadow-sm text-surface">
                                        <h4 class="text-subtitle-1 font-weight-black mb-4 d-flex align-center gap-2">
                                            <Coins :size="20" class="text-success" />
                                            Financials
                                        </h4>

                                        <v-btn-toggle v-model="mapping.mode" mandatory color="primary" variant="tonal"
                                            class="rounded-xl mb-6 w-100 d-flex" density="compact">
                                            <v-btn value="single"
                                                class="flex-grow-1 font-weight-bold text-caption">Single Column</v-btn>
                                            <v-btn value="split"
                                                class="flex-grow-1 font-weight-bold text-caption">Debit/Credit
                                                Split</v-btn>
                                        </v-btn-toggle>

                                        <div v-if="mapping.mode === 'single'" class="mapping-item-row">
                                            <div class="field-info-panel d-flex align-center ga-3 flex-grow-1">
                                                <div class="field-icon-box">💵</div>
                                                <div class="flex-grow-1">
                                                    <div class="text-caption font-weight-black">Amount</div>
                                                    <v-select v-model="mapping.amount" :items="csvHeaders"
                                                        placeholder="Amount column" variant="outlined"
                                                        density="comfortable" flat
                                                        class="premium-select-field-small mt-2" hide-details></v-select>
                                                </div>
                                            </div>
                                        </div>

                                        <div v-else class="d-flex flex-column gap-4">
                                            <div class="field-info-panel d-flex align-center ga-3">
                                                <div class="field-icon-box">➖</div>
                                                <div class="flex-grow-1">
                                                    <div class="text-caption font-weight-black">Debit (Out)</div>
                                                    <v-select v-model="splitMapping.debit" :items="csvHeaders"
                                                        variant="outlined" density="comfortable" flat
                                                        class="premium-select-field-small mt-2" hide-details></v-select>
                                                </div>
                                            </div>
                                            <div class="field-info-panel d-flex align-center ga-3">
                                                <div class="field-icon-box">➕</div>
                                                <div class="flex-grow-1">
                                                    <div class="text-caption font-weight-black">Credit (In)</div>
                                                    <v-select v-model="splitMapping.credit" :items="csvHeaders"
                                                        variant="outlined" density="comfortable" flat
                                                        class="premium-select-field-small mt-2" hide-details></v-select>
                                                </div>
                                            </div>
                                        </div>
                                    </v-card>
                                </v-col>
                            </v-row>
                        </v-window-item>

                        <!-- Step 4: Final Verification -->
                        <v-window-item :value="4">
                            <div
                                class="verify-header pa-3 d-flex align-center justify-space-between bg-primary-lighten-5 rounded-lg mb-4">
                                <span class="text-subtitle-2 font-weight-black d-flex align-center">
                                    <CheckCircle2 :size="20" class="mr-2" />
                                    {{ selectedTxns.size }} of {{ parsedTxns.length }} transactions selected
                                </span>
                                <v-btn size="x-small" variant="tonal" color="primary"
                                    class="font-weight-black rounded-pill" @click="toggleAllVerify">
                                    {{ selectedTxns.size < parsedTxns.length ? 'Select All' : 'Deselect All' }} </v-btn>
                            </div>

                            <div class="table-scroll-container border rounded-xl overflow-hidden bg-surface">
                                <v-table class="premium-table verify-table" height="400px" fixed-header>
                                    <thead>
                                        <tr>
                                            <th class="text-center px-4" style="width: 50px;">
                                                <v-checkbox-btn :model-value="selectedTxns.size === parsedTxns.length"
                                                    color="primary" hide-details
                                                    @update:model-value="toggleAllVerify"></v-checkbox-btn>
                                            </th>
                                            <th class="font-weight-black text-tiny opacity-60">DATE</th>
                                            <th class="font-weight-black text-tiny opacity-60">REF #</th>
                                            <th class="font-weight-black text-tiny opacity-60">RECIPIENT / SOURCE</th>
                                            <th class="font-weight-black text-tiny opacity-60 text-right">AMOUNT</th>
                                            <th class="text-center" style="width: 50px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="(txn, idx) in parsedTxns" :key="idx"
                                            :class="{ 'disabled-row': !selectedTxns.has(idx) }">
                                            <td class="text-center px-4">
                                                <v-checkbox-btn :model-value="selectedTxns.has(idx)"
                                                    @update:model-value="toggleSelection(idx)" color="primary"
                                                    hide-details></v-checkbox-btn>
                                            </td>
                                            <td class="text-caption">{{ txn.date }}</td>
                                            <td class="text-caption opacity-50">{{ txn.external_id || txn.ref_id || '-'
                                            }}</td>
                                            <td>
                                                <div class="font-weight-bold text-caption text-surface">{{ txn.recipient
                                                    || '-' }}</div>
                                                <div class="text-tiny opacity-60 line-clamp-1">{{ txn.description }}
                                                </div>
                                            </td>
                                            <td class="text-right font-weight-black"
                                                :class="txn.type === 'DEBIT' ? 'text-error' : 'text-success'">
                                                {{ formatAmount(txn.amount) }}
                                            </td>
                                            <td class="text-center">
                                                <v-btn icon size="x-small" variant="text" color="error"
                                                    @click="removeTxn(idx)">
                                                    <Trash2 :size="16" />
                                                </v-btn>
                                            </td>
                                        </tr>
                                    </tbody>
                                </v-table>
                            </div>
                        </v-window-item>

                        <!-- Step 5: Success Results -->
                        <v-window-item :value="5">
                            <div class="d-flex flex-column align-center justify-center py-10 text-center">
                                <div class="success-icon-wrapper mb-6">
                                    <CheckCircle :size="100" class="text-success" />
                                </div>
                                <h2 class="text-h4 font-weight-black mb-2">Import Successful!</h2>
                                <p class="text-h6 opacity-70 mb-8">Successfully imported {{ importResult?.imported }}
                                    transactions to your
                                    account.</p>

                                <v-alert v-if="importResult?.errors?.length > 0" type="warning" variant="tonal"
                                    class="rounded-xl w-100 max-w-600 text-left">
                                    <h4 class="font-weight-black text-subtitle-2 mb-2">Errors Enountered ({{
                                        importResult.errors.length }})</h4>
                                    <ul class="text-caption opacity-80 pl-4">
                                        <li v-for="err in importResult.errors" :key="err">{{ err }}</li>
                                    </ul>
                                </v-alert>

                                <v-btn color="primary" variant="flat" size="large" rounded="pill"
                                    class="mt-8 font-weight-black px-12" @click="close">
                                    Done & Close
                                </v-btn>
                            </div>
                        </v-window-item>
                    </v-window>
                </div>
            </v-card-text>

            <v-divider class="opacity-5"></v-divider>

            <v-card-actions v-if="step < 5" class="pa-4 bg-surface px-6">
                <v-btn v-if="step > 1" variant="tonal" rounded="pill" class="font-weight-black" @click="step--">
                    Back
                </v-btn>
                <v-btn v-else variant="text" rounded="pill" class="font-weight-black" @click="close">
                    Close
                </v-btn>
                <v-spacer></v-spacer>

                <v-btn v-if="step === 1" color="primary" variant="flat" rounded="pill" class="font-weight-black px-8"
                    :disabled="!selectedAccount || !file" @click="step = 2">
                    Next: Preview File
                </v-btn>

                <v-btn v-if="step === 2" color="primary" variant="flat" rounded="pill" class="font-weight-black px-8"
                    @click="step = 3">
                    Yes, Looks Good
                </v-btn>

                <v-btn v-if="step === 3" color="primary" variant="flat" rounded="pill" class="font-weight-black px-8"
                    @click="parseFile">
                    Next: Verify List
                </v-btn>

                <v-btn v-if="step === 4" color="primary" variant="flat" rounded="pill" class="font-weight-black px-8"
                    @click="importSelected" :disabled="selectedTxns.size === 0">
                    Import {{ selectedTxns.size }} Transactions
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.premium-import-card {
    background: rgb(var(--v-theme-surface));
}

.modal-header-premium {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, #4338ca 100%);
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.2);
}

.stepper-nav {
    background: white;
}

.step-circle {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(var(--v-theme-on-surface), 0.1);
    color: rgba(var(--v-theme-on-surface), 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.75rem;
    font-weight: 800;
    transition: all 0.3s ease;
}

.step-circle.active {
    background: rgb(var(--v-theme-primary));
    color: white;
    box-shadow: 0 0 0 4px rgba(var(--v-theme-primary), 0.1);
}

.step-label {
    color: rgba(var(--v-theme-on-surface), 0.4);
    transition: all 0.3s ease;
}

.step-label.active {
    color: rgb(var(--v-theme-primary));
}

.step-divider {
    width: 32px;
    height: 2px;
    background: rgba(var(--v-theme-on-surface), 0.1);
    transition: all 0.3s ease;
}

.step-divider.active {
    background: rgb(var(--v-theme-primary));
}

.premium-select-field :deep(.v-field) {
    border-radius: 12px !important;
    background: white !important;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-file-field :deep(.v-field) {
    border-radius: 12px !important;
    background: white !important;
    border: 1px dashed rgb(var(--v-theme-primary));
}

.premium-table {
    background: rgb(var(--v-theme-surface));
}

.premium-table th {
    background: rgba(var(--v-theme-on-surface), 0.02) !important;
    height: 40px !important;
}

.premium-table td {
    height: 48px !important;
}

.field-icon-box {
    width: 36px;
    height: 36px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
}

.premium-select-field-small :deep(.v-field) {
    border-radius: 8px !important;
    background: white !important;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.disabled-row {
    opacity: 0.4;
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.success-icon-wrapper {
    animation: bounce 1s ease infinite alternate;
}

@keyframes bounce {
    from {
        transform: translateY(0);
    }

    to {
        transform: translateY(-10px);
    }
}

.line-clamp-1 {
    display: -webkit-box;
    -webkit-line-clamp: 1;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

.bg-primary-lighten-5 {
    background-color: rgba(var(--v-theme-primary), 0.1);
}

.text-tiny {
    font-size: 10px;
}
</style>
