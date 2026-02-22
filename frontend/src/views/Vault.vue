<template>
    <MainLayout>
        <v-container fluid class="page-container vault-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Header Actions -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="6">
                        <div class="d-flex align-center gap-3">
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
                    <v-col cols="12" md="6" class="d-flex justify-md-end gap-3">
                        <v-btn variant="tonal" color="slate-600" rounded="pill" height="44"
                            class="px-6 font-weight-black" :loading="syncLoading" @click="triggerSync">
                            <template v-slot:prepend>
                                <RefreshCw :size="18" :class="{ 'spin-sync': syncLoading }" />
                            </template>
                            CLOUD SYNC
                        </v-btn>
                        <v-btn variant="tonal" color="primary" rounded="pill" height="44" class="px-6 font-weight-black"
                            prepend-icon="folder_plus" @click="showFolderModal = true">
                            NEW FOLDER
                        </v-btn>
                        <v-btn color="primary" rounded="pill" height="44" class="px-6 font-weight-black shadow-primary"
                            prepend-icon="upload" @click="showUploadModal = true">
                            UPLOAD FILE
                        </v-btn>
                    </v-col>
                </v-row>

                <!-- Breadcrumbs -->
                <v-row class="mb-4">
                    <v-col cols="12">
                        <div class="d-flex align-center gap-2 breadcrumb-container">
                            <v-btn variant="text" density="compact" class="text-none px-2 font-weight-bold"
                                @click="navigateTo('ROOT')">
                                <Home :size="16" class="mr-1" /> Vault
                            </v-btn>
                            <template v-for="(crumb, idx) in breadcrumbs" :key="crumb.id">
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
                        <div class="glass-card pa-3 d-flex align-center flex-wrap gap-4">
                            <v-btn-toggle v-model="filterType" mandatory color="primary" rounded="pill"
                                density="compact" class="vault-toggle">
                                <v-btn value="ALL" class="px-4">All Items</v-btn>
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
                            @click="item.is_folder ? navigateTo(item.id, item.filename) : null">
                            <div class="card-preview d-flex align-center justify-center">
                                <div :class="['icon-wrap', getIconColor(item)]">
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
                                            <v-btn icon="more_vert" variant="text" density="compact" v-bind="props"
                                                size="small" @click.stop></v-btn>
                                        </template>
                                        <v-list class="glass-card py-1" density="compact">
                                            <v-list-item v-if="!item.is_folder" @click="downloadItem(item)">
                                                <template v-slot:prepend>
                                                    <Download :size="14" class="mr-2" />
                                                </template>
                                                <v-list-item-title
                                                    class="text-caption font-weight-bold">Download</v-list-item-title>
                                            </v-list-item>
                                            <v-list-item v-if="!item.is_folder" @click="openVersionModal(item)">
                                                <template v-slot:prepend>
                                                    <History :size="14" class="mr-2" />
                                                </template>
                                                <v-list-item-title class="text-caption font-weight-bold">Update
                                                    Version</v-list-item-title>
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

                                <div class="d-flex align-center text-caption text-medium-emphasis gap-2">
                                    <span v-if="item.is_folder">Folder</span>
                                    <span v-else>{{ formatSize(item.file_size) }} • v{{ item.current_version }}</span>
                                    <span class="opacity-30">•</span>
                                    <span>{{ formatDate(item.created_at) }}</span>
                                </div>
                                <div v-if="item.transaction_id"
                                    class="d-flex align-center text-caption text-primary font-weight-bold mt-2 gap-1">
                                    <Link :size="12" />
                                    <span>Linked to transaction</span>
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
                        <v-btn icon="close" variant="text" @click="showUploadModal = false"></v-btn>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div v-if="!selectedFile" class="dropzone" @click="$refs.fileInput.click()" @dragover.prevent
                            @drop.prevent="handleDrop">
                            <UploadCloud :size="48" class="text-primary mb-3" />
                            <div class="text-subtitle-1 font-weight-bold">Click or Drag File</div>
                            <input type="file" ref="fileInput" class="d-none" @change="handleFileSelect" />
                        </div>
                        <div v-else class="file-preview pa-4 mb-4 d-flex align-center gap-4">
                            <FileText :size="32" class="text-primary" />
                            <div class="flex-grow-1 overflow-hidden">
                                <div class="font-weight-bold text-truncate">{{ selectedFile.name }}</div>
                                <div class="text-caption opacity-70">{{ formatSize(selectedFile.size) }}</div>
                            </div>
                            <v-btn icon="close" variant="text" size="small" @click="selectedFile = null"></v-btn>
                        </div>

                        <v-select v-model="uploadForm.file_type" label="Category" :items="docTypes" variant="outlined"
                            rounded="lg"></v-select>
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

            <!-- Version History Modal -->
            <v-dialog v-model="showVersionModal" max-width="600">
                <v-card class="glass-card" rounded="xl">
                    <v-card-title class="pa-6 pb-2 d-flex justify-space-between align-center">
                        <div>
                            <span class="font-weight-black">Version History</span>
                            <div class="text-caption opacity-70">{{ selectedDoc?.filename }}</div>
                        </div>
                        <v-btn icon="close" variant="text" @click="showVersionModal = false"></v-btn>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <!-- Upload New Version -->
                        <div class="mb-8 pa-4 bg-primary bg-opacity-5 rounded-lg border border-dashed border-primary">
                            <div class="text-subtitle-2 font-weight-black mb-2">Upload New Version</div>
                            <div v-if="!selectedFile" class="d-flex align-center gap-3">
                                <v-btn color="primary" variant="tonal" rounded="pill" prepend-icon="upload"
                                    @click="$refs.versionFileInput.click()">
                                    SELECT FILE
                                </v-btn>
                                <input type="file" ref="versionFileInput" class="d-none" @change="handleFileSelect" />
                                <span class="text-caption opacity-60">Replaces current version</span>
                            </div>
                            <div v-else class="d-flex align-center justify-space-between">
                                <div class="d-flex align-center gap-2">
                                    <FileText :size="20" class="text-primary" />
                                    <span class="text-body-2 font-weight-bold truncate" style="max-width: 250px;">{{
                                        selectedFile.name }}</span>
                                </div>
                                <div class="d-flex gap-2">
                                    <v-btn variant="text" size="small" @click="selectedFile = null">Cancel</v-btn>
                                    <v-btn color="primary" size="small" rounded="pill" :loading="submitting"
                                        @click="handleVersionUpload">CONFIRM</v-btn>
                                </div>
                            </div>
                        </div>

                        <!-- History List -->
                        <div class="version-list">
                            <div class="text-overline font-weight-black text-medium-emphasis mb-3">Previous Versions
                            </div>
                            <v-row v-if="versionLoading">
                                <v-col v-for="i in 3" :key="i" cols="12">
                                    <v-skeleton-loader type="list-item" class="bg-transparent"></v-skeleton-loader>
                                </v-col>
                            </v-row>
                            <div v-else-if="versions.length > 0">
                                <div v-for="(v, idx) in versions" :key="v.id"
                                    class="pa-4 mb-2 rounded-lg d-flex align-center justify-space-between border"
                                    :class="idx === 0 ? 'bg-primary bg-opacity-5 border-primary-light' : 'bg-surface'">
                                    <div class="d-flex align-center gap-4">
                                        <div class="version-badge" :class="{ 'current': idx === 0 }">
                                            v{{ v.version_number }}
                                        </div>
                                        <div>
                                            <div class="text-body-2 font-weight-black">{{ v.filename }}</div>
                                            <div class="text-tiny opacity-60">
                                                {{ formatDate(v.created_at) }} • {{ formatSize(v.file_size) }}
                                            </div>
                                        </div>
                                    </div>
                                    <v-btn icon="download" variant="text" size="small" color="primary"
                                        @click="downloadVersion(v.version_number)"></v-btn>
                                </div>
                            </div>
                            <div v-else class="text-center py-8 opacity-40">
                                No history found
                            </div>
                        </div>
                    </v-card-text>
                </v-card>
            </v-dialog>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import {
    ShieldCheck, Download, Trash2, Search, UploadCloud, Home,
    FileText, Folder, ChevronRight, History, Receipt, Scale, RefreshCw, Link
} from 'lucide-vue-next'

const notification = useNotificationStore()

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

const showVersionModal = ref(false)
const selectedDoc = ref<any>(null)
const versions = ref<any[]>([])
const versionLoading = ref(false)

const syncLoading = ref(false)

async function triggerSync() {
    syncLoading.value = true
    try {
        const res = await financeApi.syncVault()
        if (res.data.status === 'success') {
            notification.success('Vault synced with Google Drive')
            fetchItems()
        } else {
            notification.warning(res.data.message)
        }
    } catch (e) {
        notification.error('Sync failed. Check credentials.')
    } finally {
        syncLoading.value = false
    }
}

const docTypes = [
    { title: 'Other', value: 'OTHER' },
    { title: 'Invoice / Receipt', value: 'INVOICE' },
    { title: 'Insurance Policy', value: 'POLICY' },
    { title: 'Tax Document', value: 'TAX' },
    { title: 'Identity Proof', value: 'IDENTITY' }
]

// Fetching
async function fetchItems() {
    loading.value = true
    try {
        const res = await financeApi.getDocuments({ parent_id: currentFolderId.value || 'ROOT' })
        items.value = res.data
    } catch (error) {
        notification.error('Failed to load vault items')
    } finally {
        loading.value = false
    }
}

function navigateTo(id: string | null, name?: string) {
    if (id === 'ROOT') {
        currentFolderId.value = null
        currentPathName.value = 'Vault'
        breadcrumbs.value = []
    } else {
        // If not already in breadcrumbs, add it
        const exists = breadcrumbs.value.find(b => b.id === id)
        if (!exists && name) {
            breadcrumbs.value.push({ id, name })
        } else if (exists) {
            // Trim breadcrumbs up to this folder
            const idx = breadcrumbs.value.findIndex(b => b.id === id)
            breadcrumbs.value = breadcrumbs.value.slice(0, idx + 1)
        }
        currentFolderId.value = id
        currentPathName.value = name || 'Folder'
    }
    fetchItems()
}

async function openVersionModal(item: any) {
    selectedDoc.value = item
    showVersionModal.value = true
    versionLoading.value = true
    try {
        const res = await financeApi.listVersions(item.id)
        versions.value = res.data
    } catch (e) {
        notification.error('Failed to load version history')
    } finally {
        versionLoading.value = false
    }
}

async function handleVersionUpload() {
    if (!selectedFile.value || !selectedDoc.value) return
    submitting.value = true
    const formData = new FormData()
    formData.append('file', selectedFile.value)

    try {
        await financeApi.uploadVersion(selectedDoc.value.id, formData)
        notification.success('New version uploaded')
        selectedFile.value = null
        openVersionModal(selectedDoc.value)
        fetchItems()
    } catch (e) {
        notification.error('Version upload failed')
    } finally {
        submitting.value = false
    }
}

function downloadVersion(versionNum: number) {
    if (!selectedDoc.value) return
    const url = financeApi.getDocumentDownloadUrl(selectedDoc.value.id, versionNum)
    window.open(url, '_blank')
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
function downloadItem(item: any) {
    const url = financeApi.getDocumentDownloadUrl(item.id)
    window.open(url, '_blank')
}

async function deleteItem(item: any) {
    if (!confirm(`Delete ${item.is_folder ? 'folder and its contents' : 'file'}?`)) return
    try {
        await financeApi.deleteDocument(item.id)
        notification.success('Deleted')
        fetchItems()
    } catch (e) {
        notification.error('Delete failed')
    }
}

// Helpers
const filteredItems = computed(() => {
    let list = items.value
    if (filterType.value !== 'ALL') {
        list = list.filter(i => i.is_folder || i.file_type === filterType.value)
    }
    if (search.value) {
        const s = search.value.toLowerCase()
        list = list.filter(i => i.filename.toLowerCase().includes(s))
    }
    return list
})

function getIcon(item: any) {
    if (item.is_folder) return Folder
    switch (item.file_type) {
        case 'INVOICE': return Receipt
        case 'POLICY': return ShieldCheck
        case 'TAX': return Scale
        case 'IDENTITY': return ShieldCheck
        default: return FileText
    }
}

function getIconColor(item: any) {
    if (item.is_folder) return 'text-primary'
    switch (item.file_type) {
        case 'INVOICE': return 'text-orange-500'
        case 'POLICY': return 'text-blue-500'
        case 'TAX': return 'text-red-500'
        case 'IDENTITY': return 'text-green-500'
        default: return 'text-slate-500'
    }
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

onMounted(fetchItems)
</script>

<style scoped>
.vault-page {
    position: relative;
    min-height: calc(100vh - 100px);
}

.mesh-blob {
    position: absolute;
    filter: blur(100px);
    opacity: 0.15;
    z-index: 0;
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

.glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 20px;
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

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
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

.truncate {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
