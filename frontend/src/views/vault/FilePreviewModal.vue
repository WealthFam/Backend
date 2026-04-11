<script setup lang="ts">
import { X, Download, Clock, Upload, FileText, Link2, Unlink2, FileImage, FileVideo, Music, FileCode, FileArchive, Fingerprint, ShieldCheck, Folder, Receipt, Scale, FileSpreadsheet, Presentation, Shield } from 'lucide-vue-next'
import { ref, computed, watch, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

const props = defineProps<{
    modelValue: boolean
    item: any
    initialEditMode?: boolean
}>()

const emit = defineEmits(['update:modelValue', 'refresh'])
const notification = useNotificationStore()
const router = useRouter()

const loading = ref(false)
const versionsLoading = ref(false)
const submitting = ref(false)
const versions = ref<any[]>([])
const selectedVersion = ref<number | null>(null)
const previewUrl = ref<string | null>(null)
const activeBlob = ref<string | null>(null)
const sidebarTab = ref('details') // 'details' or 'history'

function viewTransaction() {
    if (!linkedTransaction.value) return
    router.push({ name: 'Transactions', query: { search: linkedTransaction.value.description } })
    emit('update:modelValue', false)
}

// Edit State
const editMode = ref(false)
const editedItem = ref({
    filename: '',
    file_type: 'OTHER',
    is_shared: true
})
const updateFileInput = ref<HTMLInputElement | null>(null)
const selectedNewFile = ref<File | null>(null)

// Transaction linking
const txSearch = ref('')
const txSearchResults = ref<any[]>([])
const txSearchLoading = ref(false)
const linkedTransaction = ref<any>(null)
let txSearchTimeout: ReturnType<typeof setTimeout> | null = null

async function searchTransactions(q: string) {
    if (!q.trim()) { txSearchResults.value = []; return }
    txSearchLoading.value = true
    try {
        const res = await financeApi.searchTransactions(q, 8)
        txSearchResults.value = res.data?.items || res.data || []
    } catch { txSearchResults.value = [] }
    finally { txSearchLoading.value = false }
}

function onTxSearchInput() {
    if (txSearchTimeout) clearTimeout(txSearchTimeout)
    txSearchTimeout = setTimeout(() => searchTransactions(txSearch.value), 350)
}

async function linkToTransaction(tx: any) {
    if (!props.item) return
    try {
        await financeApi.linkDocToTransaction(props.item.id, tx.id)
        linkedTransaction.value = tx
        txSearch.value = ''
        txSearchResults.value = []
        notification.success(`Linked to "${tx.description}"`)
        emit('refresh')
    } catch { notification.error('Failed to link transaction') }
}

async function unlinkTransaction() {
    if (!props.item) return
    try {
        await financeApi.linkDocToTransaction(props.item.id, null)
        linkedTransaction.value = null
        notification.success('Transaction unlinked')
        emit('refresh')
    } catch { notification.error('Failed to unlink') }
}

async function fetchLinkedTransaction() {
    if (props.item?.transaction) {
        linkedTransaction.value = props.item.transaction
        return
    }
    if (!props.item?.transaction_id) { linkedTransaction.value = null; return }
    try {
        // Fallback for simple object if transaction not joined
        linkedTransaction.value = {
            id: props.item.transaction_id,
            description: props.item.transaction_description || 'Linked Transaction',
            amount: props.item.transaction_amount,
            date: props.item.transaction_date
        }
    } catch { linkedTransaction.value = null }
}

const docTypes = [
    { title: 'Other', value: 'OTHER' },
    { title: 'Invoice / Receipt', value: 'INVOICE' },
    { title: 'Insurance Policy', value: 'POLICY' },
    { title: 'Tax Document', value: 'TAX' },
    { title: 'Identity Proof', value: 'IDENTITY' }
]

const isRenderable = computed(() => {
    if (!props.item || !props.item.mime_type) return false
    const mt = props.item.mime_type
    return (
        mt.startsWith('image/') ||
        mt === 'application/pdf' ||
        mt.startsWith('text/') ||
        mt === 'application/json' ||
        mt === 'text/html'
    )
})

const isImage = computed(() => props.item?.mime_type?.startsWith('image/'))
const isPdf = computed(() => props.item?.mime_type === 'application/pdf')

async function fetchVersions() {
    if (!props.item) return
    versionsLoading.value = true
    try {
        const res = await financeApi.listVersions(props.item.id)
        versions.value = res.data.data
    } catch (e) {
        console.error('Failed to fetch versions', e)
    } finally {
        versionsLoading.value = false
    }
}

async function loadPreview(version?: number) {
    if (!props.item || !isRenderable.value) return
    loading.value = true
    selectedVersion.value = version || null

    if (activeBlob.value) {
        URL.revokeObjectURL(activeBlob.value)
        activeBlob.value = null
    }

    try {
        const res = await financeApi.getDocumentBlob(props.item.id, version)
        const blob = new Blob([res.data], { type: props.item.mime_type })
        activeBlob.value = URL.createObjectURL(blob)
        previewUrl.value = activeBlob.value
    } catch (e: any) {
        console.error('Preview load failed', e)
        notification.error('Failed to load preview')
    } finally {
        loading.value = false
    }
}

function initEdit() {
    if (!props.item) return
    editedItem.value = {
        filename: props.item.filename,
        file_type: props.item.file_type,
        is_shared: props.item.is_shared
    }
    selectedNewFile.value = null
    editMode.value = true
}

function handleNewFileSelect(e: any) {
    const file = e.target.files[0]
    if (file) {
        selectedNewFile.value = file
        editedItem.value.filename = file.name
    }
}

async function saveChanges() {
    if (!props.item) return
    submitting.value = true
    try {
        // 1. If new file selected, upload as version
        if (selectedNewFile.value) {
            const formData = new FormData()
            formData.append('file', selectedNewFile.value)
            await financeApi.uploadVersion(props.item.id, formData)
        }

        // 2. Update metadata
        const metaData = new FormData()
        metaData.append('filename', editedItem.value.filename)
        metaData.append('file_type', editedItem.value.file_type)
        metaData.append('is_shared', String(editedItem.value.is_shared))
        await financeApi.updateDocument(props.item.id, metaData)

        notification.success('Document updated successfully')
        editMode.value = false
        emit('refresh')
        // Reload preview and versions
        loadPreview()
        fetchVersions()
    } catch (e) {
        notification.error('Update failed')
    } finally {
        submitting.value = false
    }
}

watch(() => props.modelValue, (val) => {
    if (val && props.item) {
        editMode.value = props.initialEditMode || false
        loadPreview()
        fetchVersions()
        fetchLinkedTransaction()
        if (props.item) {
            editedItem.value = {
                filename: props.item.filename,
                file_type: props.item.file_type,
                is_shared: props.item.is_shared ?? true
            }
        }
        txSearch.value = ''
        txSearchResults.value = []
    } else {
        editMode.value = false
        txSearch.value = ''
        txSearchResults.value = []
        if (activeBlob.value) {
            URL.revokeObjectURL(activeBlob.value)
            activeBlob.value = null
            previewUrl.value = null
        }
    }
})

watch(() => props.item, (newVal) => {
    if (props.modelValue && newVal) {
        fetchLinkedTransaction()
    }
}, { deep: true })

onUnmounted(() => {
    if (activeBlob.value) URL.revokeObjectURL(activeBlob.value)
})

async function handleDownload() {
    if (!props.item) return
    try {
        const res = await financeApi.getDocumentBlob(props.item.id, selectedVersion.value || undefined)
        const blob = new Blob([res.data], { type: props.item.mime_type })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = props.item.filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    } catch (e) {
        notification.error('Download failed')
    }
}

function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleString()
}

function formatSize(bytes: number) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getIcon(item: any) {
    if (!item) return FileText
    if (item.is_folder) return Folder

    const filename = (item.filename || '').toLowerCase()
    const mt = (item.mime_type || '').toLowerCase()

    if (item.file_type === 'BILL') return Receipt
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

    if (item.file_type === 'BILL') return 'text-teal-darken-2'
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
    <v-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" fullscreen
        transition="dialog-bottom-transition">
        <v-card class="preview-modal-bg">
            <!-- Header -->
            <v-toolbar flat class="px-6 glass-toolbar" height="70" border="b">
                <div class="d-flex align-center ga-3">
                    <div class="header-icon-box pa-0 overflow-hidden d-flex align-center justify-center bg-surface-variant"
                        :class="getIconColor(item)" style="width: 36px; height: 36px; border-radius: 10px;">
                        <v-img v-if="item?.thumbnail_path" :src="financeApi.getDocumentThumbnailUrl(item.id)" cover
                            class="absolute-full">
                            <template v-slot:placeholder>
                                <v-progress-circular indeterminate size="12" color="primary"></v-progress-circular>
                            </template>
                        </v-img>
                        <component v-else :is="getIcon(item)" :size="20" />
                    </div>
                    <div>
                        <div class="text-subtitle-1 font-weight-black">{{ item?.filename }}</div>
                        <div class="text-caption opacity-60">
                            {{ selectedVersion ? `Version ${selectedVersion}` : 'Current Version' }} • {{
                                item?.mime_type }}
                        </div>
                    </div>
                </div>

                <v-spacer></v-spacer>

                <div class="d-flex align-center ga-3">
                    <v-btn variant="tonal" color="grey-darken-3" rounded="lg" class="font-weight-black"
                        @click="initEdit" v-if="!editMode">
                        EDIT DETAILS
                    </v-btn>
                    <v-btn variant="tonal" color="primary" rounded="lg" class="font-weight-black"
                        @click="handleDownload">
                        <Download :size="18" class="mr-2" /> DOWNLOAD
                    </v-btn>
                    <v-divider vertical class="mx-2 my-4 opacity-10"></v-divider>
                    <v-btn icon variant="text" size="small" @click="emit('update:modelValue', false)">
                        <X :size="24" />
                    </v-btn>
                </div>
            </v-toolbar>

            <v-card-text class="pa-0 d-flex overflow-hidden" style="height: calc(100vh - 70px);">
                <!-- Left: Preview Area -->
                <div class="flex-grow-1 h-100 d-flex flex-column align-center justify-center preview-area relative-pos">
                    <v-fade-transition mode="out-in">
                        <v-progress-circular v-if="loading" indeterminate color="primary" size="64"
                            width="6"></v-progress-circular>

                        <div v-else-if="!isRenderable" class="text-center pa-12">
                            <v-avatar color="surface-variant" variant="tonal" size="120" class="mb-6">
                                <FileQuestion :size="60" class="opacity-50" />
                            </v-avatar>
                            <h2 class="text-h4 font-weight-black mb-4">Preview Not Available</h2>
                            <p class="text-h6 opacity-60 mb-8 mx-auto" style="max-width: 500px;">
                                This file type cannot be displayed in the browser.
                            </p>
                            <v-btn color="primary" rounded="pill" size="large" class="px-10 font-weight-black"
                                @click="handleDownload">
                                DOWNLOAD {{ formatSize(item?.file_size) }}
                            </v-btn>
                        </div>

                        <div v-else-if="previewUrl" class="h-100 w-100 d-flex align-center justify-center pa-4">
                            <v-img v-if="isImage" :src="previewUrl" class="max-h-100 max-w-100" contain></v-img>
                            <iframe v-else-if="isPdf" :src="previewUrl"
                                class="h-100 w-100 border-0 rounded-lg"></iframe>
                            <iframe v-else :src="previewUrl"
                                class="h-100 w-100 border-0 bg-white rounded-lg shadow-lg"></iframe>
                        </div>
                    </v-fade-transition>
                </div>

                <!-- Right: Content Sidebar (Switchable between Version History and Edits) -->
                <div class="content-sidebar border-l d-none d-md-flex flex-column">

                    <!-- EDIT MODE -->
                    <template v-if="editMode">
                        <div class="pa-6 border-b d-flex align-center justify-space-between bg-primary-light">
                            <div class="d-flex align-center ga-3">
                                <Shield :size="20" class="text-primary" />
                                <span class="font-weight-black">Update Document</span>
                            </div>
                            <v-btn icon variant="text" size="small" @click="editMode = false">
                                <X :size="18" />
                            </v-btn>
                        </div>

                        <div class="flex-grow-1 overflow-y-auto pa-6">
                            <v-text-field v-model="editedItem.filename" label="Filename" variant="outlined" rounded="lg"
                                density="comfortable" class="mb-4"></v-text-field>

                            <v-select v-model="editedItem.file_type" :items="docTypes" label="Category"
                                variant="outlined" rounded="lg" density="comfortable" class="mb-4"></v-select>

                            <v-switch v-model="editedItem.is_shared" label="Shared with Family" color="primary" inset
                                hide-details class="mb-6"></v-switch>

                            <!-- Transaction Link Section -->
                            <div class="mb-6">
                                <div class="d-flex align-center ga-2 mb-3">
                                    <Link2 :size="14" class="text-primary" />
                                    <span
                                        class="text-overline font-weight-black text-primary letter-spacing-wide">Linked
                                        Transaction</span>
                                </div>

                                <!-- Currently linked -->
                                <div v-if="linkedTransaction" class="pa-3 rounded-xl border mb-3"
                                    style="border-color: rgba(var(--v-theme-primary), 0.3); background: rgba(var(--v-theme-primary), 0.04);">
                                    <div class="d-flex align-center justify-space-between">
                                        <div class="flex-grow-1 min-w-0">
                                            <div class="text-caption font-weight-black text-truncate">{{
                                                linkedTransaction.description }}</div>
                                            <div class="text-tiny opacity-60 mt-1" v-if="linkedTransaction.date">{{
                                                linkedTransaction.date }}</div>
                                        </div>
                                        <v-btn icon variant="text" size="x-small" color="error"
                                            class="ml-2 flex-shrink-0" @click="unlinkTransaction" title="Remove link">
                                            <Unlink2 :size="14" />
                                        </v-btn>
                                    </div>
                                </div>
                                <div v-else class="text-caption opacity-40 mb-3 py-2 text-center border rounded-xl"
                                    style="border-style: dashed;">
                                    No transaction linked
                                </div>

                                <!-- Search to link -->
                                <v-text-field v-model="txSearch" @input="onTxSearchInput"
                                    :label="linkedTransaction ? 'Change linked transaction' : 'Search & link a transaction'"
                                    variant="outlined" rounded="lg" density="compact" prepend-inner-icon="mdi-magnify"
                                    :loading="txSearchLoading" hide-details clearable
                                    @click:clear="txSearchResults = []"></v-text-field>

                                <div v-if="txSearchResults.length" class="mt-1 rounded-xl border overflow-hidden"
                                    style="border-color: rgba(var(--v-border-color), 0.12);">
                                    <div v-for="tx in txSearchResults" :key="tx.id"
                                        class="tx-result-item pa-3 cursor-pointer d-flex align-center ga-3"
                                        @click="linkToTransaction(tx)">
                                        <div class="flex-grow-1 min-w-0">
                                            <div class="text-caption font-weight-black text-truncate">{{ tx.description
                                            }}</div>
                                            <div class="text-tiny opacity-50">{{ tx.date }} • {{ tx.category }}</div>
                                        </div>
                                        <div class="text-caption font-weight-black text-no-wrap"
                                            :class="tx.amount < 0 ? 'text-error' : 'text-success'">
                                            {{ tx.amount < 0 ? '-' : '+' }}{{ Math.abs(tx.amount).toFixed(2) }} </div>
                                        </div>
                                    </div>
                                </div>

                                <div class="pa-4 rounded-xl border border-dashed text-center cursor-pointer mb-6"
                                    :class="selectedNewFile ? 'bg-primary-light border-primary' : ''"
                                    @click="updateFileInput?.click()">
                                    <Upload :size="32" class="text-primary mx-auto mb-2" />
                                    <div class="text-caption font-weight-black">
                                        {{ selectedNewFile ? selectedNewFile.name : 'REPLACE WITH NEW FILE' }}
                                    </div>
                                    <div class="text-tiny opacity-50 mt-1" v-if="!selectedNewFile">Will create a new
                                        version
                                    </div>
                                    <input type="file" ref="updateFileInput" class="d-none"
                                        @change="handleNewFileSelect" />
                                </div>

                                <v-btn block color="primary" height="52" rounded="xl" class="font-weight-black"
                                    :loading="submitting" @click="saveChanges">
                                    SAVE ALL CHANGES
                                </v-btn>
                                <v-btn block variant="text" height="52" rounded="xl" class="mt-2 font-weight-black"
                                    @click="editMode = false">
                                    CANCEL
                                </v-btn>
                            </div>
                    </template>

                    <!-- NON-EDIT MODE (TABS) -->
                    <template v-else>
                        <div class="pa-2 border-b d-flex ga-1 bg-slate-50">
                            <v-btn variant="text" density="compact"
                                :class="sidebarTab === 'details' ? 'bg-white shadow-sm border text-primary font-weight-black' : 'opacity-60'"
                                class="flex-grow-1 rounded-lg py-1 px-4" height="36" @click="sidebarTab = 'details'">
                                <Info :size="14" class="mr-1" /> Details
                            </v-btn>
                            <v-btn variant="text" density="compact"
                                :class="sidebarTab === 'history' ? 'bg-white shadow-sm border text-primary font-weight-black' : 'opacity-60'"
                                class="flex-grow-1 rounded-lg py-1 px-4" height="36" @click="sidebarTab = 'history'">
                                <History :size="14" class="mr-1" /> History
                            </v-btn>
                        </div>

                        <div class="flex-grow-1 overflow-y-auto">
                            <!-- DETAILS TAB -->
                            <div v-if="sidebarTab === 'details'" class="pa-6">
                                <div class="mb-8">
                                    <div class="d-flex align-center ga-2 mb-4">
                                        <div class="header-icon-box pa-2" :class="getIconColor(item)"
                                            style="background: rgba(var(--v-theme-on-surface), 0.05);">
                                            <component :is="getIcon(item)" :size="18" />
                                        </div>
                                        <div class="text-overline font-weight-black text-primary letter-spacing-wide">
                                            Document Information</div>
                                    </div>

                                    <div class="d-flex flex-column ga-4">
                                        <div class="d-flex justify-space-between align-center px-1">
                                            <span class="text-caption font-weight-bold opacity-60">Category</span>
                                            <v-chip size="x-small" color="primary" class="font-weight-black">{{
                                                item?.file_type }}</v-chip>
                                        </div>
                                        <div class="d-flex justify-space-between align-center px-1">
                                            <span class="text-caption font-weight-bold opacity-60">File Size</span>
                                            <span class="text-caption font-weight-black">{{ formatSize(item?.file_size)
                                            }}</span>
                                        </div>
                                        <div class="d-flex justify-space-between align-center px-1">
                                            <span class="text-caption font-weight-bold opacity-60">Last Updated</span>
                                            <span class="text-caption font-weight-black">{{ formatDate(item?.updated_at
                                                || item?.created_at) }}</span>
                                        </div>
                                        <div v-if="item?.description" class="mt-2">
                                            <div class="text-tiny font-weight-black opacity-40 uppercase mb-1">
                                                Description</div>
                                            <div class="text-caption bg-slate-50 pa-3 rounded-lg border">{{
                                                item.description }}</div>
                                        </div>
                                    </div>
                                </div>

                                <v-divider class="mb-6 opacity-10"></v-divider>

                                <div class="mb-6">
                                    <div class="d-flex align-center ga-2 mb-4">
                                        <div class="header-icon-box pa-2"
                                            style="background: rgba(var(--v-theme-secondary), 0.1);">
                                            <Link2 :size="18" class="text-secondary" />
                                        </div>
                                        <div class="text-overline font-weight-black text-secondary letter-spacing-wide">
                                            Linked Transaction</div>
                                    </div>

                                    <div v-if="linkedTransaction"
                                        class="pa-4 rounded-xl border border-secondary-thin bg-secondary-soft-bg relative-pos overflow-hidden">
                                        <v-btn icon variant="text" size="x-small"
                                            class="position-absolute top-2 right-2 opacity-40 hover-opacity-100"
                                            @click="viewTransaction" title="Jump to transaction">
                                            <ExternalLink :size="14" />
                                        </v-btn>
                                        <div class="d-flex justify-space-between align-start mb-2 ga-2">
                                            <div class="text-subtitle-2 font-weight-black leading-tight flex-grow-1">{{
                                                linkedTransaction.description }}</div>
                                            <div :class="linkedTransaction.amount < 0 ? 'text-error' : 'text-success'"
                                                class="text-subtitle-2 font-weight-black no-wrap">
                                                {{ linkedTransaction.amount < 0 ? '-' : '+' }}₹{{
                                                    Math.abs(linkedTransaction.amount).toLocaleString() }} </div>
                                            </div>
                                            <div class="d-flex align-center justify-space-between">
                                                <span class="text-tiny font-weight-bold opacity-60">{{
                                                    formatDate(linkedTransaction.date) }}</span>
                                                <v-chip v-if="linkedTransaction.category" variant="tonal" size="x-small"
                                                    class="text-tiny font-weight-black">{{ linkedTransaction.category
                                                    }}</v-chip>
                                            </div>
                                        </div>
                                        <div v-else class="pa-6 rounded-xl border border-dashed text-center">
                                            <div class="text-caption opacity-50 mb-3">No transaction linked to this
                                                document.</div>
                                            <v-btn variant="tonal" size="small" rounded="pill" color="primary"
                                                class="font-weight-black text-none" @click="initEdit">
                                                Link Now
                                            </v-btn>
                                        </div>
                                    </div>
                                </div>

                                <!-- VERSION HISTORY TAB -->
                                <div v-if="sidebarTab === 'history'" class="pa-4">
                                    <div v-if="versionsLoading" class="d-flex justify-center py-8">
                                        <v-progress-circular indeterminate color="primary"></v-progress-circular>
                                    </div>
                                    <template v-else>
                                        <div v-for="v in versions" :key="v.id"
                                            :class="['version-item pa-4 rounded-xl mb-3 border cursor-pointer transition-all',
                                                (selectedVersion === v.version_number || (!selectedVersion && v.version_number === item?.current_version)) ? 'active' : '']"
                                            @click="loadPreview(v.version_number)">
                                            <div class="d-flex justify-space-between align-start mb-2">
                                                <div class="version-label">Version {{ v.version_number }}</div>
                                                <v-chip v-if="v.version_number === item?.current_version" size="x-small"
                                                    color="primary" class="font-weight-black">LATEST</v-chip>
                                            </div>
                                            <div class="text-caption font-weight-bold mb-2 opacity-80 text-truncate">{{
                                                v.filename }}</div>
                                            <div class="d-flex align-center justify-space-between opacity-50 text-tiny">
                                                <span class="d-flex align-center">
                                                    <Clock :size="12" class="mr-1" /> {{ formatDate(v.created_at) }}
                                                </span>
                                                <span>{{ formatSize(v.file_size) }}</span>
                                            </div>
                                        </div>
                                    </template>
                                </div>
                            </div>
                    </template>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.preview-modal-bg {
    background: #f8fafc !important;
}

.glass-toolbar {
    background: rgba(255, 255, 255, 0.8) !important;
    backdrop-filter: blur(10px);
}

.header-icon-box {
    background: rgba(var(--v-theme-primary), 0.1);
    padding: 10px;
    border-radius: 12px;
}

.preview-area {
    background: #e2e8f0;
    overflow: hidden;
}

.content-sidebar {
    width: 340px;
    background: rgb(var(--v-theme-surface));
    z-index: 10;
}

.version-item {
    border: 1px solid rgba(var(--v-border-color), 0.1);
    background: rgba(var(--v-theme-on-surface), 0.03);
}


.version-item.active {
    background: rgba(var(--v-theme-primary), 0.05);
    border-color: rgb(var(--v-theme-primary));
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.1);
}

.version-label {
    font-size: 0.75rem;
    font-weight: 900;
    text-transform: uppercase;
    color: rgb(var(--v-theme-primary));
}

.text-tiny {
    font-size: 10px;
}

.max-h-100 {
    max-height: 100%;
}

.max-w-100 {
    max-width: 100%;
}

.bg-primary-light {
    background: rgba(var(--v-theme-primary), 0.05);
}

.border-primary {
    border-color: rgb(var(--v-theme-primary)) !important;
}

.tx-result-item {
    transition: background 0.15s;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.08);
}

.tx-result-item:last-child {
    border-bottom: none;
}

.tx-result-item:hover {
    background: rgba(var(--v-theme-primary), 0.05);
}
</style>
