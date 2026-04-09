<script setup lang="ts">
import { ref, computed, reactive, watch } from 'vue'
import { useTheme } from 'vuetify'
import { useCurrency } from '@/composables/useCurrency'
import {
    CheckCircle2, X, Pencil, Plus, Minus, Info, Tag,
    Settings, ArrowLeftRight, Search, Link, SearchX, LineChart, IndianRupee, Calendar,
    FileText, Paperclip, ExternalLink, Trash2, Link2,
    FileImage, FileVideo, Music, FileCode, FileArchive, Fingerprint, ShieldCheck, Receipt, Scale, Folder,
    FileSpreadsheet, Presentation
} from 'lucide-vue-next'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'

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
const theme = useTheme()
const isDark = computed(() => theme.global.current.value.dark)

// Local state to avoid prop mutation

const localForm = reactive({ ...props.form })

watch(() => props.isOpen, (next) => {
    if (next) {
        Object.assign(localForm, props.form)
    }
})

// Deep watch on props.form to keep local state in sync if parent changes it
watch(() => props.form, (newForm) => {
    Object.assign(localForm, newForm)
}, { deep: true })

// Document Management
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

const notification = useNotificationStore()
const attachedDocs = ref<any[]>([])
const loadingDocs = ref(false)

// Vault picker for linking existing docs
const vaultPickerOpen = ref(false)
const vaultPickerSearch = ref('')
const vaultPickerResults = ref<any[]>([])
const vaultPickerLoading = ref(false)
let vaultPickerTimeout: ReturnType<typeof setTimeout> | null = null

async function searchVaultDocs(q: string) {
    vaultPickerLoading.value = true
    try {
        // When q is empty, list all root-level files; when typing, use backend search (spans all folders)
        const params = q.trim()
            ? { search: q.trim(), limit: 20 }
            : { limit: 20 }
        const res = await financeApi.getDocuments(params)
        const all: any[] = Array.isArray(res.data) ? res.data : (res.data?.items || [])
        vaultPickerResults.value = all.filter(d => !d.is_folder)
    } catch { vaultPickerResults.value = [] }
    finally { vaultPickerLoading.value = false }
}

function onVaultPickerInput() {
    if (vaultPickerTimeout) clearTimeout(vaultPickerTimeout)
    vaultPickerTimeout = setTimeout(() => searchVaultDocs(vaultPickerSearch.value), 300)
}

async function linkVaultDoc(doc: any) {
    if (!localForm.id) return
    try {
        await financeApi.linkDocToTransaction(doc.id, localForm.id)
        notification.success(`"${doc.filename}" linked to this transaction`)
        vaultPickerOpen.value = false
        vaultPickerSearch.value = ''
        fetchAttachedDocs()
    } catch { notification.error('Failed to link document') }
}

function openVaultPicker() {
    vaultPickerOpen.value = true
    vaultPickerSearch.value = ''
    searchVaultDocs('')
}

async function fetchAttachedDocs() {
    if (!props.isEditing || !localForm.id) {
        attachedDocs.value = []
        return
    }
    loadingDocs.value = true
    try {
        const res = await financeApi.getDocuments({ transaction_id: localForm.id })
        attachedDocs.value = res.data
    } catch (e) {
        console.error('Failed to fetch docs', e)
    } finally {
        loadingDocs.value = false
    }
}

watch(() => props.isOpen, (next) => {
    if (next && props.isEditing) fetchAttachedDocs()
})

async function handleFileUpload(e: any) {
    const file = e.target.files[0]
    if (!file || !localForm.id) return

    const formData = new FormData()
    formData.append('file', file)
    formData.append('transaction_id', localForm.id)
    formData.append('is_shared', 'true')

    try {
        await financeApi.uploadDocument(formData)
        notification.success('Document attached')
        fetchAttachedDocs()
    } catch (e) {
        notification.error('Failed to upload document')
    }
}

async function detachDoc(docId: string) {
    try {
        await financeApi.deleteDocument(docId)
        notification.success('Document detached')
        fetchAttachedDocs()
    } catch (e) {
        notification.error('Failed to detach document')
    }
}

async function openDoc(docId: string) {
    try {
        const doc = attachedDocs.value.find(d => d.id === docId)
        const res = await financeApi.getDocumentBlob(docId)
        const blob = new Blob([res.data], { type: res.headers['content-type'] || doc?.mime_type || 'application/octet-stream' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = doc?.filename || 'document'
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    } catch (e) {
        notification.error('Failed to open document')
    }
}

const categoryOptions = computed(() => {
    const list: any[] = []

    // Helper to build hierarchy manually if not provided as tree
    const buildTree = (flatList: any[]) => {
        const lookup = new Map();
        const roots: any[] = [];

        // First pass: put everything in a map
        flatList.forEach(c => {
            lookup.set(c.id || c.name, { ...c, subcategories: [] });
        });

        // Second pass: link children to parents
        flatList.forEach(c => {
            const parentKey = c.parent_id;
            if (parentKey && lookup.has(parentKey)) {
                lookup.get(parentKey).subcategories.push(lookup.get(c.id || c.name));
            } else if (!parentKey) {
                roots.push(lookup.get(c.id || c.name));
            } else {
                // If parent_id exists but parent not found, treat as root to avoid losing it
                roots.push(lookup.get(c.id || c.name));
            }
        });
        return roots;
    }

    const flatten = (cats: any[], depth = 0) => {
        // Sort alphabetically to maintain order
        const sorted = [...cats].sort((a, b) => a.name.localeCompare(b.name))

        sorted.forEach(c => {
            const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
            list.push({
                title: `${prefix}${c.icon || '🏷️'} ${c.name}`,
                value: c.name
            })
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories, depth + 1)
            }
        })
    }

    // Check if we already have a tree structure (some roots have subcategories)
    const hasTreeStructure = props.categories.some(c => c.subcategories && c.subcategories.length > 0)
    const tree = hasTreeStructure ? props.categories.filter(c => !c.parent_id) : buildTree(props.categories)

    flatten(tree)

    if (!list.find(o => o.value === 'Uncategorized')) {
        list.push({ title: '🏷️ Uncategorized', value: 'Uncategorized' })
    }
    return list
})

const accountOptions = computed(() => {
    return props.accounts.map(a => ({ title: a.name, value: a.id }))
})

const expenseGroupOptions = computed(() => {
    return [{ title: 'None', value: '' }, ...props.expenseGroups.map(g => ({ title: g.name, value: g.id }))]
})

const currentCategoryBudget = computed(() => {
    if (!localForm.category || localForm.is_transfer) return null
    return props.budgets.find(b => b.category === localForm.category) || null
})

// Auto-detect Credit Card Payment
watch(() => localForm.category, (newVal) => {
    if (!newVal) return;

    // Check if category implies credit card payment
    const lower = newVal.toLowerCase();
    if (lower.includes('credit card') || lower.includes('cc payment') || lower.includes('card payment')) {
        // Find if we have credit card accounts
        const ccAccounts = props.accounts.filter(a => a.type === 'CREDIT_CARD');

        if (ccAccounts.length > 0) {
            // Suggest Transfer mode (Safe to mutate localForm now)
            if (!localForm.is_transfer) {
                localForm.is_transfer = true;

                // If only one card, auto-select it
                if (ccAccounts.length === 1) {
                    localForm.to_account_id = ccAccounts[0].id;
                }
            }
        }
    }
})

const isFormValid = computed(() => {
    const basicValid = localForm.amount > 0 && localForm.date && localForm.account_id && localForm.category
    if (localForm.is_transfer) {
        return basicValid && localForm.to_account_id
    }
    return basicValid
})

function handleSubmit() {
    if (!isFormValid.value) return
    emit('submit', { ...localForm }) // Emit a clone of the local result
}

function handleClose() {
    emit('close')
}

function getIcon(item: any) {
    if (!item) return FileText
    if (item.is_folder) return Folder

    const filename = (item.filename || '').toLowerCase()
    const mt = (item.mime_type || '').toLowerCase()

    if (item.file_type === 'INVOICE') return Receipt
    if (item.file_type === 'POLICY') return ShieldCheck
    if (item.file_type === 'TAX') return Scale
    if (item.file_type === 'IDENTITY') return Fingerprint

    if (filename.endsWith('.pdf') || mt === 'application/pdf') return FileText
    if (filename.endsWith('.xls') || filename.endsWith('.xlsx') || filename.endsWith('.csv') ||
        mt.includes('spreadsheet') || mt.includes('excel') || mt.includes('csv') || mt.includes('sheet')) return FileSpreadsheet
    if (filename.endsWith('.ppt') || filename.endsWith('.pptx') ||
        mt.includes('presentation') || mt.includes('powerpoint')) return Presentation
    if (filename.endsWith('.doc') || filename.endsWith('.docx') || mt.includes('word') || mt.includes('msword')) return FileText

    if (mt.startsWith('image/')) return FileImage
    if (mt.startsWith('video/')) return FileVideo
    if (mt.startsWith('audio/')) return Music
    if (mt.includes('javascript') || mt.includes('json') || mt.includes('html') || mt.includes('css')) return FileCode
    if (mt.includes('zip') || mt.includes('rar') || mt.includes('tar') || mt.includes('7z') || mt.includes('archive')) return FileArchive
    return FileText
}

function getIconColor(item: any) {
    if (!item) return 'text-grey'
    if (item.is_folder) return 'text-primary'

    const filename = (item.filename || '').toLowerCase()
    const mt = (item.mime_type || '').toLowerCase()

    if (item.file_type === 'INVOICE') return 'text-orange-darken-2'
    if (item.file_type === 'POLICY') return 'text-blue-darken-2'
    if (item.file_type === 'TAX') return 'text-red-darken-2'
    if (item.file_type === 'IDENTITY') return 'text-green-darken-2'

    if (filename.endsWith('.pdf') || mt === 'application/pdf') return 'text-red-darken-1'
    if (filename.endsWith('.xls') || filename.endsWith('.xlsx') || filename.endsWith('.csv') || mt.includes('sheet')) return 'text-green-darken-3'
    if (mt.includes('presentation') || mt.includes('powerpoint')) return 'text-deep-orange-darken-2'

    if (mt.startsWith('image/')) return 'text-purple-darken-1'
    if (mt.startsWith('video/')) return 'text-deep-purple'
    if (mt.startsWith('audio/')) return 'text-pink'
    if (mt.includes('zip') || mt.includes('rar') || mt.includes('archive')) return 'text-amber-darken-3'
    return 'text-grey-darken-1'
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
                                    <v-text-field v-model="localForm.description" label="Description"
                                        placeholder="What was this for?" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        autocomplete="off" />
                                </v-col>

                                <v-col cols="12" class="mb-1">
                                    <v-text-field v-model="localForm.recipient" label="Merchant / Payee"
                                        placeholder="Who did you pay?" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        autocomplete="off" />
                                </v-col>

                                <v-col cols="4" md="3" class="mb-1">
                                    <v-autocomplete v-model="localForm.type" :items="['DEBIT', 'CREDIT']" label="Type"
                                        variant="outlined" density="comfortable" rounded="lg"
                                        class="premium-modal-input font-weight-bold" hide-details>
                                        <template v-slot:selection="{ item }">
                                            <span :class="item.value === 'DEBIT' ? 'text-error' : 'text-success'">{{
                                                item.value === 'DEBIT' ? 'Debit' : 'Credit' }}</span>
                                        </template>
                                        <template v-slot:item="{ props, item }">
                                            <v-list-item v-bind="props"
                                                :title="item.value === 'DEBIT' ? 'Debit' : 'Credit'"
                                                :class="item.value === 'DEBIT' ? 'text-error' : 'text-success'">
                                                <template v-slot:prepend>
                                                    <component :is="item.value === 'DEBIT' ? Minus : Plus" :size="16"
                                                        class="mr-2" />
                                                </template>
                                            </v-list-item>
                                        </template>
                                    </v-autocomplete>
                                </v-col>

                                <v-col cols="8" md="5" class="mb-1">
                                    <v-text-field v-model="localForm.amount" label="Amount" type="number"
                                        placeholder="0.00" variant="outlined" density="comfortable" rounded="lg"
                                        class="premium-modal-input font-weight-bold" hide-details
                                        :prepend-inner-icon="IndianRupee" autocomplete="off" />
                                </v-col>

                                <v-col cols="12" md="4" class="mb-1">
                                    <div class="date-picker-wrapper">
                                        <VueDatePicker v-model="localForm.date" :dark="isDark" auto-apply
                                            :enable-time-picker="true" model-type="yyyy-MM-dd'T'HH:mm"
                                            format="dd MMM yyyy HH:mm" placeholder="Date & Time" :teleport="true"
                                            input-class-name="premium-date-input">
                                            <template #trigger>
                                                <v-text-field
                                                    :model-value="localForm.date ? new Date(localForm.date).toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''"
                                                    label="Date & Time" variant="outlined" density="comfortable"
                                                    rounded="lg" class="premium-modal-input font-weight-bold"
                                                    hide-details :prepend-inner-icon="Calendar" readonly />
                                            </template>
                                        </VueDatePicker>
                                    </div>
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
                                    <v-autocomplete v-model="localForm.account_id" :items="accountOptions" label="Account"
                                        item-title="title" item-value="value" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        prepend-inner-icon="Landmark" />
                                </v-col>

                                <v-col cols="12" md="6" class="mb-1">
                                    <v-autocomplete v-model="localForm.category" :items="categoryOptions"
                                        label="Category" item-title="title" item-value="value"
                                        placeholder="Select Category" variant="outlined" density="comfortable"
                                        rounded="lg" class="premium-modal-input font-weight-bold" hide-details
                                        :prepend-inner-icon="!localForm.category ? 'Tag' : undefined" />
                                </v-col>

                                <v-col cols="12" class="mb-1">
                                    <v-autocomplete v-model="localForm.expense_group_id" :items="expenseGroupOptions"
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
                                        <v-switch v-model="localForm.is_transfer" label="Is this a Transfer?"
                                            color="primary" hide-details density="compact" class="font-weight-bold"
                                            persistent-hint hint="Moving money between your own accounts">
                                            <template #label>
                                                <div class="d-flex flex-column ml-2">
                                                    <span class="text-body-2 font-weight-bold">Internal Transfer</span>
                                                    <span class="text-tiny opacity-60">Between your accounts</span>
                                                </div>
                                            </template>
                                        </v-switch>
                                    </v-col>
                                    <v-col cols="12" sm="6">
                                        <v-switch v-model="localForm.exclude_from_reports" label="Hide from Reports"
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
                                <div v-if="localForm.is_transfer" class="mt-4">
                                    <v-card variant="flat" class="pa-4 border-opacity-10"
                                        style="background: rgba(var(--v-theme-primary), 0.05); border-radius: 20px !important;">
                                        <div class="d-flex align-center gap-2 mb-4">
                                            <ArrowLeftRight :size="20" class="text-primary" />
                                            <span class="text-subtitle-2 font-weight-black">Match Transfer Pair</span>
                                        </div>

                                        <v-row dense>
                                            <v-col cols="12" md="8">
                                                <v-autocomplete v-model="localForm.to_account_id" :items="accountOptions"
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
                                                    :class="{ 'match-selected-active': localForm.linked_transaction_id === match.id }"
                                                    @click="emit('selectMatch', match)" variant="flat"
                                                    :color="localForm.linked_transaction_id === match.id ? 'primary' : 'surface'">
                                                    <div class="pa-4 d-flex justify-space-between align-center">
                                                        <div class="d-flex align-center gap-3">
                                                            <v-avatar size="32"
                                                                :color="localForm.linked_transaction_id === match.id ? 'white' : 'primary'"
                                                                class="opacity-80">
                                                                <Link :size="16"
                                                                    :color="localForm.linked_transaction_id === match.id ? 'primary' : 'white'" />
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

                        <!-- Document Vault Integration -->
                        <div class="section-group mt-6">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="d-flex align-center gap-2">
                                    <Paperclip :size="20" class="text-primary" />
                                    <span
                                        class="text-overline font-weight-black text-primary letter-spacing-wide">Documents</span>
                                </div>
                                <div v-if="isEditing" class="d-flex align-center gap-1">
                                    <v-btn variant="text" color="primary" density="compact"
                                        class="text-none font-weight-bold"
                                        @click="($refs.txFileInput as HTMLInputElement).click()">
                                        <Plus :size="14" class="mr-1" /> Upload New
                                    </v-btn>
                                    <v-btn variant="text" color="secondary" density="compact"
                                        class="text-none font-weight-bold" @click="openVaultPicker">
                                        <Link2 :size="14" class="mr-1" /> Link from Vault
                                    </v-btn>
                                </div>
                                <input type="file" ref="txFileInput" class="d-none" @change="handleFileUpload" />
                            </div>

                            <!-- Vault Picker panel -->
                            <v-expand-transition>
                                <div v-if="vaultPickerOpen && isEditing" class="mb-4 pa-3 rounded-xl border"
                                    style="border-color: rgba(var(--v-theme-secondary), 0.3); background: rgba(var(--v-theme-secondary), 0.03);">
                                    <div class="d-flex align-center justify-space-between mb-3">
                                        <span class="text-caption font-weight-black opacity-70">PICK FROM VAULT</span>
                                        <v-btn icon variant="text" size="x-small" @click="vaultPickerOpen = false">
                                            <X :size="14" />
                                        </v-btn>
                                    </div>
                                    <v-text-field v-model="vaultPickerSearch" @input="onVaultPickerInput"
                                        label="Search vault documents…" variant="outlined" rounded="lg"
                                        density="compact" prepend-inner-icon="mdi-magnify" :loading="vaultPickerLoading"
                                        hide-details class="mb-2" clearable
                                        @click:clear="searchVaultDocs('')"></v-text-field>
                                    <div class="rounded-lg border overflow-hidden"
                                        style="max-height: 200px; overflow-y: auto;" v-if="vaultPickerResults.length">
                                        <div v-for="doc in vaultPickerResults" :key="doc.id"
                                            class="vault-pick-item pa-3 cursor-pointer d-flex align-center ga-3"
                                            @click="linkVaultDoc(doc)">
                                            <div class="header-icon-box bg-surface-variant rounded pa-0 overflow-hidden d-flex align-center justify-center"
                                                style="width: 32px; height: 32px; flex-shrink: 0;">
                                                <v-img v-if="doc.thumbnail_path"
                                                    :src="financeApi.getDocumentThumbnailUrl(doc.id)" cover
                                                    class="absolute-full">
                                                    <template v-slot:placeholder>
                                                        <v-progress-circular indeterminate size="12"
                                                            color="primary"></v-progress-circular>
                                                    </template>
                                                </v-img>
                                                <component v-else :is="getIcon(doc)" :size="16"
                                                    :class="getIconColor(doc)" />
                                            </div>
                                            <div class="flex-grow-1 min-w-0">
                                                <div class="text-caption font-weight-bold text-truncate">{{ doc.filename
                                                }}</div>
                                                <div class="text-tiny opacity-50">{{ doc.file_type }} - {{
                                                    doc.transaction_id ? '(linked)' :
                                                        'Free' }}</div>

                                            </div>
                                            <v-chip size="x-small" color="primary" variant="tonal">LINK</v-chip>
                                        </div>
                                    </div>
                                    <div v-else-if="!vaultPickerLoading"
                                        class="text-caption opacity-40 text-center py-3">
                                        No documents found
                                    </div>
                                </div>
                            </v-expand-transition>

                            <v-card variant="flat" border class="pa-1 bg-surface border-opacity-10"
                                style="border-radius: 20px !important;">
                                <v-list v-if="attachedDocs.length > 0" density="compact" class="bg-transparent">
                                    <v-list-item v-for="doc in attachedDocs" :key="doc.id" rounded="lg" class="mb-1">
                                        <template v-slot:prepend>
                                            <div class="bg-surface-variant rounded mr-3 pa-0 overflow-hidden d-flex align-center justify-center"
                                                style="width: 24px; height: 24px;">
                                                <v-img v-if="doc.thumbnail_path"
                                                    :src="financeApi.getDocumentThumbnailUrl(doc.id)" cover
                                                    class="absolute-full" />
                                                <component v-else :is="getIcon(doc)" :size="14"
                                                    :class="getIconColor(doc)" />
                                            </div>
                                        </template>
                                        <v-list-item-title class="text-caption font-weight-bold">{{ doc.filename
                                        }}</v-list-item-title>
                                        <template v-slot:append>
                                            <div class="d-flex gap-1">
                                                <v-btn icon variant="text" density="compact" @click="openDoc(doc.id)">
                                                    <ExternalLink :size="14" class="text-primary" />
                                                </v-btn>
                                                <v-btn icon variant="text" density="compact" @click="detachDoc(doc.id)"
                                                    color="error">
                                                    <Trash2 :size="14" />
                                                </v-btn>
                                            </div>
                                        </template>
                                    </v-list-item>
                                </v-list>
                                <div v-else class="pa-6 text-center opacity-40">
                                    <p class="text-caption font-weight-bold mb-0">No documents attached</p>
                                    <p v-if="!isEditing" class="text-tiny">Save transaction first to attach docs</p>
                                </div>
                            </v-card>
                        </div>
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
                    height="40" @click="handleSubmit" :prepend-icon="CheckCircle2" :disabled="!isFormValid">
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

/* DatePicker Customization */
.dp__theme_dark {
    --dp-background-color: rgb(var(--v-theme-surface));
    --dp-text-color: rgba(var(--v-theme-on-surface), 0.87);
    --dp-hover-color: rgba(var(--v-theme-primary), 0.1);
    --dp-hover-text-color: rgb(var(--v-theme-on-surface));
    --dp-hover-icon-color: rgb(var(--v-theme-on-surface));
    --dp-primary-color: rgb(var(--v-theme-primary));
    --dp-primary-text-color: #ffffff;
    --dp-secondary-color: #a0a0a0;
    --dp-border-color: rgba(var(--v-border-color), 0.15);
    --dp-menu-border-color: rgba(var(--v-border-color), 0.15);
    --dp-border-color-hover: rgba(var(--v-border-color), 0.3);
    --dp-disabled-color: #f6f6f6;
    --dp-scroll-bar-background: #f3f3f3;
    --dp-scroll-bar-color: #959595;
    --dp-success-color: #76d275;
    --dp-success-color-disabled: #a3d9b1;
    --dp-icon-color: rgba(var(--v-theme-on-surface), 0.6);
    --dp-danger-color: #ff6f60;
    --dp-marker-color: #ff6f60;
    --dp-tooltip-color: #fafafa;
    --dp-disabled-color-text: #8e8e8e;
    --dp-highlight-color: rgb(25 118 210 / 10%);
    --dp-range-between-dates-background-color: var(--dp-hover-color, #484848);
    --dp-range-between-dates-text-color: var(--dp-hover-text-color, #fff);
    --dp-range-between-border-color: var(--dp-hover-color, #fff);
    font-family: inherit;
}

.date-picker-wrapper :deep(.dp__input_wrap) {
    display: none;
}
</style>
