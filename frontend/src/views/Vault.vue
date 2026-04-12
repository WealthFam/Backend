<template>
    <MainLayout>
        <v-container fluid class="page-container vault-page dashboard-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"></div>
            <div class="mesh-blob blob-2"></div>

            <div class="relative-pos z-10">
                <!-- Header Actions -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="6">
                        <div class="d-flex align-center ga-3">
                            <div class="icon-box primary-glow">
                                <ShieldCheck :size="24" class="text-primary" />
                            </div>
                            <div>
                                <h1 class="text-h6 font-weight-black mb-0">Document Vault</h1>
                                <p class="text-caption text-medium-emphasis font-weight-bold">Secure family storage with
                                    versioning</p>
                            </div>
                        </div>
                    </v-col>
                    <v-col cols="12" md="6" class="d-flex justify-md-end ga-2">
                        <!-- Cloud Sync hidden for now 
                        <v-tooltip text="Sync History" location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" color="slate-600" rounded="lg" height="44"
                                    width="44" class="icon-btn-square" @click="openHistory">
                                    <History :size="20" />
                                </v-btn>
                            </template>
</v-tooltip>

<v-tooltip text="Cloud Sync" location="top">
    <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" color="slate-600" rounded="lg" height="44"
                                    width="44" class="icon-btn-square" :loading="syncLoading" @click="triggerSync">
                                    <RefreshCw :size="20" :class="{ 'spin-sync': syncLoading }" />
                                </v-btn>
                            </template>
</v-tooltip>

<v-tooltip text="Vault Settings" location="top">
    <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" color="slate-600" rounded="lg" height="44"
                                    width="44" class="icon-btn-square" @click="showSettingsModal = true">
                                    <Settings :size="20" />
                                </v-btn>
                            </template>
</v-tooltip>
-->

                        <v-tooltip text="New Folder" location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" variant="tonal" color="primary" rounded="lg" height="44"
                                    width="44" class="icon-btn-square" @click="showFolderModal = true">
                                    <FolderPlus :size="20" />
                                </v-btn>
                            </template>
                        </v-tooltip>

                        <v-tooltip text="Upload File" location="top">
                            <template v-slot:activator="{ props }">
                                <v-btn v-bind="props" color="primary" rounded="lg" height="44" width="44"
                                    class="icon-btn-square shadow-primary" @click="showUploadModal = true">
                                    <Upload :size="20" />
                                </v-btn>
                            </template>
                        </v-tooltip>
                    </v-col>
                </v-row>

                <!-- Breadcrumbs -->
                <v-row class="mb-4">
                    <v-col cols="12">
                        <div class="d-flex align-center ga-2 breadcrumb-container">
                            <v-btn variant="text" density="compact" class="text-none px-2 font-weight-bold"
                                @click="navigateTo('ROOT')">
                                <Home :size="16" class="mr-1" /> Vault
                            </v-btn>
                            <template v-for="crumb in breadcrumbs" :key="crumb.id">
                                <ChevronRight :size="14" class="opacity-30" />
                                <v-btn variant="text" density="compact" class="text-none px-2 font-weight-bold"
                                    @click="navigateTo(crumb.id)">
                                    {{ crumb.name }}
                                </v-btn>
                            </template>
                        </div>
                    </v-col>
                </v-row>

                <!-- Filters & Search -->
                <v-row class="mb-6">
                    <v-col cols="12">
                        <div class="glass-card pa-3 d-flex align-center flex-wrap ga-4">
                            <v-btn-toggle v-model="filterType" mandatory color="primary" rounded="pill"
                                density="compact" class="vault-toggle">
                                <v-btn value="ALL" class="px-4">All Items</v-btn>
                                <v-btn value="BILL" class="px-4 text-teal">Bills</v-btn>
                                <v-btn value="INVOICE" class="px-4">Invoices</v-btn>
                                <v-btn value="POLICY" class="px-4">Policies</v-btn>
                                <v-btn value="TAX" class="px-4">Tax Docs</v-btn>
                                <v-btn value="IDENTITY" class="px-4">Identity</v-btn>
                            </v-btn-toggle>

                            <v-spacer></v-spacer>

                            <v-text-field v-model="search" placeholder="Search..." density="compact" variant="outlined"
                                hide-details rounded="pill" class="search-premium" style="max-width: 300px;">
                                <template v-slot:prepend-inner>
                                    <Search :size="16" class="text-primary" />
                                </template>
                            </v-text-field>
                        </div>
                    </v-col>
                </v-row>

                <!-- Content Grid -->
                <v-row v-if="loading">
                    <v-col v-for="i in 8" :key="i" cols="12" sm="6" md="4" lg="3">
                        <v-skeleton-loader type="card" class="glass-card" height="180"></v-skeleton-loader>
                    </v-col>
                </v-row>

                <v-row v-else-if="items.length > 0">
                    <v-col v-for="item in filteredItems" :key="item.id" cols="12" sm="6" md="4" lg="3">
                        <v-card class="vault-card glass-card h-100" elevation="0"
                            @click="item.is_folder ? navigateTo(item.id, item.filename) : openPreview(item)">
                            <div class="card-preview d-flex align-center justify-center relative-pos overflow-hidden">
                                <v-img v-if="item.thumbnail_path" :src="financeApi.getDocumentThumbnailUrl(item.id)"
                                    cover class="absolute-full thumbnail-zoom" alt="thumbnail">
                                    <template v-slot:placeholder>
                                        <div class="d-flex align-center justify-center fill-height bg-primary-soft">
                                            <v-progress-circular indeterminate size="20"
                                                color="primary"></v-progress-circular>
                                        </div>
                                    </template>
                                </v-img>
                                <div v-else :class="['icon-wrap', getIconColor(item)]">
                                    <component :is="getIcon(item)" :size="32" />
                                </div>
                            </div>

                            <v-card-text class="pa-4">
                                <div class="d-flex justify-space-between align-start mb-1">
                                    <span class="text-subtitle-2 font-weight-black text-truncate"
                                        style="max-width: 80%">
                                        {{ item.filename }}
                                    </span>
                                    <v-menu location="bottom end">
                                        <template v-slot:activator="{ props }">
                                            <v-btn variant="text" density="compact" v-bind="props" icon size="small"
                                                class="opacity-60 hover-opacity-100" @click.stop>
                                                <MoreVertical :size="18" />
                                            </v-btn>
                                        </template>
                                        <v-list class="glass-card py-1" density="compact">
                                            <v-list-item v-if="!item.is_folder" @click="downloadItem(item)">
                                                <template v-slot:prepend>
                                                    <Download :size="14" class="mr-2" />
                                                </template>
                                                <v-list-item-title class="font-weight-bold">Download</v-list-item-title>
                                            </v-list-item>
                                            <v-list-item v-if="!item.is_folder" @click="openPreview(item, true)">
                                                <template v-slot:prepend>
                                                    <Link2 :size="14" class="mr-2" />
                                                </template>
                                                <v-list-item-title class="font-weight-bold">Link
                                                    Transaction</v-list-item-title>
                                            </v-list-item>
                                            <v-list-item @click="deleteItem(item)" class="text-error">
                                                <template v-slot:prepend>
                                                    <Trash2 :size="14" class="mr-2" />
                                                </template>
                                                <v-list-item-title
                                                    class="text-caption font-weight-bold">Delete</v-list-item-title>
                                            </v-list-item>
                                        </v-list>
                                    </v-menu>
                                </div>

                                <div class="d-flex align-center justify-space-between mt-2">
                                    <span class="text-tiny opacity-50 d-flex align-center">
                                        <Clock :size="10" class="mr-1" /> {{ formatDate(item.updated_at ||
                                            item.created_at) }}
                                    </span>
                                    <div class="d-flex align-center ga-2">
                                        <span v-if="!item.is_folder" class="version-badge">v{{ item.current_version
                                        }}</span>
                                        <span v-else
                                            class="text-tiny opacity-30 font-weight-bold uppercase">Folder</span>
                                    </div>
                                </div>
                                <!-- Linked Transaction Info -->
                                <div v-if="item.transaction" @click.stop="openPreview(item, false)"
                                    class="mt-3 pa-2 rounded-lg border-primary-thin bg-primary-soft-bg d-flex align-center justify-space-between ga-2 cursor-pointer hover-bg-primary-soft min-w-0">
                                    <div
                                        class="text-tiny font-weight-bold text-truncate opacity-80 flex-grow-1 min-w-0">
                                        {{ item.transaction.description }}
                                    </div>
                                    <span class="text-tiny font-weight-black flex-shrink-0"
                                        :class="item.transaction.amount < 0 ? 'text-error' : 'text-success'">
                                        {{ item.transaction.amount < 0 ? '-' : '+' }}₹{{
                                            Math.abs(item.transaction.amount).toLocaleString() }} </span>
                                </div>
                                <div v-else-if="item.transaction_id"
                                    class="mt-2 text-tiny text-primary font-weight-bold">
                                    Linked
                                </div>
                            </v-card-text>
                        </v-card>
                    </v-col>
                </v-row>

                <div v-else class="text-center py-16">
                    <div class="empty-icon mb-4">📂</div>
                    <h3 class="text-h6 font-weight-bold">This folder is empty</h3>
                    <p class="text-medium-emphasis mb-6">Start organizing your documents here.</p>
                </div>
            </div>

            <!-- Upload Modal -->
            <v-dialog v-model="showUploadModal" max-width="500">
                <v-card class="glass-card" rounded="xl">
                    <v-card-title class="pa-6 pb-2 d-flex justify-space-between align-center">
                        <span class="font-weight-black">Upload Document</span>
                        <v-btn icon variant="text" @click="showUploadModal = false">
                            <X :size="20" />
                        </v-btn>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div v-if="!selectedFile" class="dropzone" @click="fileInput?.click()" @dragover.prevent
                            @drop.prevent="handleDrop">
                            <UploadCloud :size="48" class="text-primary mb-3" />
                            <div class="text-subtitle-1 font-weight-bold">Click or Drag File</div>
                            <input type="file" ref="fileInput" class="d-none" @change="handleFileSelect" />
                        </div>
                        <div v-else class="file-preview pa-4 mb-4 d-flex align-center ga-4">
                            <FileText :size="32" class="text-primary" />
                            <div class="flex-grow-1 overflow-hidden">
                                <div class="font-weight-bold text-truncate">{{ selectedFile.name }}</div>
                                <div class="text-caption opacity-70">{{ formatSize(selectedFile.size) }}</div>
                            </div>
                            <v-btn icon variant="text" size="small" @click="selectedFile = null">
                                <X :size="16" />
                            </v-btn>
                        </div>

                        <v-autocomplete v-model="uploadForm.file_type" label="Category" :items="docTypes" variant="outlined"
                            rounded="lg"></v-autocomplete>
                        <v-checkbox v-model="uploadForm.is_shared" label="Shared with Family"
                            color="primary"></v-checkbox>

                        <v-btn block color="primary" height="48" rounded="pill" class="mt-4 font-weight-black"
                            :loading="submitting" :disabled="!selectedFile" @click="uploadFile">
                            UPLOAD TO {{ currentPathName }}
                        </v-btn>
                    </v-card-text>
                </v-card>
            </v-dialog>

            <!-- Folder Modal -->
            <v-dialog v-model="showFolderModal" max-width="400">
                <v-card class="glass-card" rounded="xl">
                    <v-card-title class="pa-6 pb-2 font-weight-black">New Folder</v-card-title>
                    <v-card-text class="pa-6">
                        <v-text-field v-model="folderName" label="Folder Name" variant="outlined" rounded="lg"
                            hide-details class="mb-4"></v-text-field>
                        <v-btn block color="primary" height="48" rounded="pill" class="font-weight-black"
                            :loading="submitting" :disabled="!folderName" @click="createFolder">
                            CREATE FOLDER
                        </v-btn>
                    </v-card-text>
                </v-card>
            </v-dialog>

        </v-container>

        <FilePreviewModal v-model="showPreviewModal" :item="selectedDoc" :initialEditMode="isPreviewEdit"
            @refresh="fetchItems" />
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { 
    X, Download, Clock, Upload, FileText, Link2, FileImage, FileVideo, 
    Music, FileCode, FileArchive, Fingerprint, ShieldCheck, Folder, 
    Receipt, Scale, FileSpreadsheet, Presentation, FolderPlus, 
    MoreVertical, UploadCloud, Home, ChevronRight, Search, Trash2 
} from 'lucide-vue-next'

import { financeApi } from '@/api/client'
import MainLayout from '@/layouts/MainLayout.vue'
import { useConfirmStore } from '@/stores/confirm'
import { useNotificationStore } from '@/stores/notification'

const notification = useNotificationStore()
const confirmDialog = useConfirmStore()

// Components
import FilePreviewModal from './vault/FilePreviewModal.vue'

// Navigation & State
const currentFolderId = ref<string | null>(null)
const currentPathName = ref('Vault')
const breadcrumbs = ref<{ id: string, name: string }[]>([])
const items = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const filterType = ref('ALL')

// Modals
const showUploadModal = ref(false)
const showFolderModal = ref(false)
const submitting = ref(false)
const selectedFile = ref<File | null>(null)
const folderName = ref('')
const uploadForm = ref({ file_type: 'OTHER', is_shared: true })
const fileInput = ref<HTMLInputElement | null>(null)

const showPreviewModal = ref(false)
const selectedDoc = ref<any>(null)
const isPreviewEdit = ref(false)

const docTypes = [
    { title: 'Other', value: 'OTHER' },
    { title: 'Utility Bill / Receipt', value: 'BILL' },
    { title: 'Invoice', value: 'INVOICE' },
    { title: 'Insurance Policy', value: 'POLICY' },
    { title: 'Tax Document', value: 'TAX' },
    { title: 'Identity Proof', value: 'IDENTITY' }
]

// Fetching
async function fetchItems() {
    loading.value = true
    const params: any = { 
        parent_id: currentFolderId.value || 'ROOT',
        limit: 100 // Fetch a larger chunk for now since we don't have infinite scroll yet
    }
    if (search.value) params.search = search.value
    if (filterType.value !== 'ALL') params.file_type = filterType.value

    try {
        const res = await financeApi.getDocuments(params)
        items.value = res.data.data

        // Sync selectedDoc if modal is open to ensure details tab stays fresh
        if (showPreviewModal.value && selectedDoc.value) {
            const fresh = items.value.find(i => i.id === selectedDoc.value.id)
            if (fresh) selectedDoc.value = fresh
        }
    } catch (error) {
        notification.error('Failed to load vault items')
    } finally {
        loading.value = false
    }
}

function navigateTo(id: string | null, name?: string) {
    if (id === 'ROOT' || !id) {
        currentFolderId.value = null
        currentPathName.value = 'Vault'
        breadcrumbs.value = []
    } else {
        // If not already in breadcrumbs, add it
        const exists = breadcrumbs.value.find(b => b.id === id)
        if (!exists && name) {
            breadcrumbs.value.push({ id: id as string, name })
        } else if (exists) {
            // Trim breadcrumbs up to this folder
            const crumbIdx = breadcrumbs.value.findIndex(b => b.id === id)
            breadcrumbs.value = breadcrumbs.value.slice(0, crumbIdx + 1)
        }
        currentFolderId.value = id
        currentPathName.value = name || 'Folder'
    }
}

function openPreview(item: any, isEdit = false) {
    selectedDoc.value = item
    isPreviewEdit.value = isEdit
    showPreviewModal.value = true
}


// Upload & Folder creation
function handleFileSelect(e: any) {
    const file = e.target.files[0]
    if (file) selectedFile.value = file
}

function handleDrop(e: DragEvent) {
    const file = e.dataTransfer?.files[0]
    if (file) selectedFile.value = file
}

async function uploadFile() {
    if (!selectedFile.value) return
    submitting.value = true
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('file_type', uploadForm.value.file_type)
    formData.append('is_shared', String(uploadForm.value.is_shared))
    if (currentFolderId.value) formData.append('parent_id', currentFolderId.value)

    try {
        await financeApi.uploadDocument(formData)
        notification.success('File uploaded')
        showUploadModal.value = false
        selectedFile.value = null
        fetchItems()
    } catch (e) {
        notification.error('Upload failed')
    } finally {
        submitting.value = false
    }
}

async function createFolder() {
    if (!folderName.value) return
    submitting.value = true
    const formData = new FormData()
    formData.append('name', folderName.value)
    if (currentFolderId.value) formData.append('parent_id', currentFolderId.value)

    try {
        await financeApi.createFolder(formData)
        notification.success('Folder created')
        showFolderModal.value = false
        folderName.value = ''
        fetchItems()
    } catch (e) {
        notification.error('Failed to create folder')
    } finally {
        submitting.value = false
    }
}

// Actions
async function downloadItem(item: any) {
    try {
        const res = await financeApi.getDocumentBlob(item.id)
        const blob = new Blob([res.data], { type: item.mime_type })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = item.filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    } catch (e) {
        notification.error('Download failed')
    }
}

async function deleteItem(item: any) {
    const isConfirmed = await confirmDialog.prompt(`Delete ${item.is_folder ? 'folder and its contents' : 'file'}?`, 'Confirm Delete', 'Delete', 'Cancel')
    if (!isConfirmed) return
    try {
        await financeApi.deleteDocument(item.id)
        notification.success('Deleted')
        fetchItems()
    } catch (e) {
        notification.error('Delete failed')
    }
}

// Helpers
const filteredItems = computed(() => items.value)

function getIcon(item: any) {
    if (!item) return FileText
    if (item.is_folder) return Folder
    const filename = (item.filename || '').toLowerCase()
    const mt = (item.mime_type || '').toLowerCase()

    // 1. By Category (Highest Priority)
    if (item.file_type === 'BILL') return Receipt
    if (item.file_type === 'INVOICE') return Receipt
    if (item.file_type === 'POLICY') return ShieldCheck
    if (item.file_type === 'TAX') return Scale
    if (item.file_type === 'IDENTITY') return Fingerprint

    // 2. By Extension / Specific Type
    if (filename.endsWith('.pdf') || mt === 'application/pdf') return FileText
    if (filename.endsWith('.xls') || filename.endsWith('.xlsx') || filename.endsWith('.csv') ||
        mt.includes('spreadsheet') || mt.includes('excel') || mt.includes('csv') || mt.includes('sheet')) return FileSpreadsheet
    if (filename.endsWith('.ppt') || filename.endsWith('.pptx') ||
        mt.includes('presentation') || mt.includes('powerpoint')) return Presentation
    if (filename.endsWith('.doc') || filename.endsWith('.docx') || mt.includes('word') || mt.includes('msword')) return FileText

    // 3. By General Mime Type
    if (mt.startsWith('image/')) return FileImage
    if (mt.startsWith('video/')) return FileVideo
    if (mt.startsWith('audio/')) return Music
    if (mt.includes('javascript') || mt.includes('json') || mt.includes('html') || mt.includes('css')) return FileCode
    if (mt.includes('zip') || mt.includes('rar') || mt.includes('tar') || mt.includes('gz') || mt.includes('7z') || mt.includes('archive')) return FileArchive

    return FileText
}

function getIconColor(item: any) {
    if (!item) return 'text-grey'
    if (item.is_folder) return 'text-primary'
    const filename = (item.filename || '').toLowerCase()
    const mt = (item.mime_type || '').toLowerCase()

    // 1. By Category
    if (item.file_type === 'BILL') return 'text-teal-darken-2'
    if (item.file_type === 'INVOICE') return 'text-orange-darken-2'
    if (item.file_type === 'POLICY') return 'text-blue-darken-2'
    if (item.file_type === 'TAX') return 'text-red-darken-2'
    if (item.file_type === 'IDENTITY') return 'text-green-darken-2'

    // 2. By Specific File Type
    if (filename.endsWith('.pdf') || mt === 'application/pdf') return 'text-red-darken-1'
    if (filename.endsWith('.xls') || filename.endsWith('.xlsx') || filename.endsWith('.csv') || mt.includes('sheet')) return 'text-green-darken-3'
    if (mt.includes('presentation') || mt.includes('powerpoint')) return 'text-deep-orange-darken-2'

    // 3. By General Mime Type
    if (mt.startsWith('image/')) return 'text-purple-darken-1'
    if (mt.startsWith('video/')) return 'text-deep-purple'
    if (mt.startsWith('audio/')) return 'text-pink'
    if (mt.includes('zip') || mt.includes('rar') || mt.includes('archive')) return 'text-amber-darken-3'

    return 'text-grey-darken-1'
}

function formatSize(bytes: number) {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateStr: string) {
    return new Date(dateStr).toLocaleDateString()
}

let searchDebounce: any = null
watch(search, () => {
    if (searchDebounce) clearTimeout(searchDebounce)
    searchDebounce = setTimeout(() => {
        fetchItems()
    }, 400) // 400ms debounce
})

watch([filterType, currentFolderId], () => {
    fetchItems()
})

onMounted(() => {
    fetchItems()
})
</script>

<style scoped>
.vault-page {
    position: relative;
    min-height: calc(100vh - 64px);
    overflow: hidden;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

/* Mesh Background */
.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    z-index: 1;
    border-radius: 50%;
    animation: blob-float 20s infinite alternate;
}

.blob-1 {
    background: rgba(var(--v-theme-primary), 0.1);
    width: 600px;
    height: 600px;
    top: -200px;
    right: -100px;
}

.blob-2 {
    background: rgba(var(--v-theme-secondary), 0.05);
    width: 400px;
    height: 400px;
    bottom: -100px;
    left: -100px;
    animation-delay: -5s;
}

@keyframes blob-float {
    0% {
        transform: translate(0, 0) scale(1);
    }

    100% {
        transform: translate(20px, -20px) scale(1.1);
    }
}

.icon-box {
    width: 48px;
    height: 48px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.primary-glow {
    background: rgba(var(--v-theme-primary), 0.1);
    box-shadow: 0 4px 20px rgba(var(--v-theme-primary), 0.15);
}

.breadcrumb-container {
    background: rgba(var(--v-theme-on-surface), 0.03);
    padding: 8px 16px;
    border-radius: 12px;
    width: fit-content;
}

.vault-card {
    cursor: pointer;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.vault-card:hover {
    transform: translateY(-4px);
    background: rgba(var(--v-theme-surface), 0.9);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1) !important;
}

.card-preview {
    height: 100px;
    background: rgba(var(--v-theme-on-surface), 0.02);
}

.thumbnail-zoom {
    transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.vault-card:hover .thumbnail-zoom {
    transform: scale(1.08);
}

.absolute-full {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
}

.icon-wrap {
    width: 56px;
    height: 56px;
    border-radius: 16px;
    background: rgba(var(--v-theme-surface), 1);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
}

.dropzone {
    border: 2px dashed rgba(var(--v-theme-primary), 0.3);
    border-radius: 16px;
    padding: 32px;
    text-align: center;
    cursor: pointer;
    background: rgba(var(--v-theme-primary), 0.02);
}

.dropzone:hover {
    border-color: rgb(var(--v-theme-primary));
}

.shadow-primary {
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

.vault-toggle :deep(.v-btn) {
    font-weight: 700 !important;
    text-transform: none;
    font-size: 0.75rem;
}

.version-badge {
    padding: 2px 8px;
    background: rgba(var(--v-theme-on-surface), 0.1);
    border-radius: 6px;
    font-size: 0.65rem;
    font-weight: 900;
}

.version-badge.current {
    background: rgb(var(--v-theme-primary));
    color: white;
}

.settings-json-area :deep(textarea) {
    font-family: 'Fira Code', monospace !important;
    font-size: 0.8rem;
}

.status-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.status-dot.success {
    background-color: #22c55e;
    box-shadow: 0 0 10px rgba(34, 197, 94, 0.4);
}

.status-dot.error {
    background-color: #ef4444;
    box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
}

.status-dot.running {
    background-color: #3b82f6;
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 1;
    }

    50% {
        transform: scale(1.2);
        opacity: 0.7;
    }

    100% {
        transform: scale(1);
        opacity: 1;
    }
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

.text-tiny {
    font-size: 10px;
}

.icon-btn-square {
    min-width: 44px !important;
    padding: 0 !important;
}

.help-panels :deep(.v-expansion-panel-text__wrapper) {
    padding: 0;
}

.setup-steps {
    padding-left: 15px;
    line-height: 1.6;
}

.setup-steps li {
    margin-bottom: 4px;
}
</style>
