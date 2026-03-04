<template>
    <div class="animate-in">
        <!-- Search Bar -->
        <div class="d-flex flex-column flex-sm-row align-center justify-space-between gap-4 mb-6">
            <v-text-field v-model="searchQuery" placeholder="Search email accounts..." variant="outlined"
                density="comfortable" hide-details class="flex-grow-1" style="max-width: 400px; width: 100%;"
                bg-color="surface">
                <template v-slot:prepend-inner>
                    <Search :size="18" class="text-medium-emphasis mr-2" />
                </template>
            </v-text-field>

            <div class="d-flex align-center gap-3">
                <h3 class="text-subtitle-1 font-weight-bold">Email Accounts</h3>
                <v-chip color="success" size="small" variant="flat" class="font-weight-bold">
                    {{ emailConfigs.length }} Total
                </v-chip>
            </div>
        </div>

        <v-alert v-if="syncStatus && syncStatus.status !== 'running'"
            :color="syncStatus.status === 'completed' ? 'success' : 'error'" variant="tonal" border="start" closable
            class="mb-6" @click:close="syncStatus = null">
            <template v-slot:prepend>
                <div class="mr-2">
                    <CheckCircle2 v-if="syncStatus.status === 'completed'" :size="24" />
                    <XCircle v-else :size="24" />
                </div>
            </template>
            <div class="text-subtitle-2 font-weight-bold">
                {{ syncStatus.status === 'completed' ? 'Sync Complete' : 'Sync Failed' }}
            </div>
            <div class="text-body-2">
                {{ syncStatus.message || `${syncStatus.stats?.processed} transactions processed.` }}
            </div>
        </v-alert>

        <v-row>
            <v-col v-for="config in emailConfigs" :key="config.id" cols="12" md="6" lg="4">
                <v-card class="premium-glass-card h-100 d-flex flex-column" elevation="0">
                    <div class="status-stripe-compact" :class="{
                        'active': config.is_active,
                        'inactive': !config.is_active,
                        'auto-sync': config.auto_sync_enabled
                    }"></div>

                    <v-card-text class="d-flex flex-column h-100 pl-6">
                        <!-- Header -->
                        <div class="d-flex justify-space-between align-start mb-3">
                            <div class="d-flex align-center gap-2 overflow-hidden">
                                <v-avatar color="primary" variant="tonal" size="32" class="border">
                                    <span class="text-caption">
                                        {{familyMembers.find(u => u.id === config.user_id)?.avatar || '👤'}}
                                    </span>
                                </v-avatar>
                                <div class="d-flex flex-column" style="min-width: 0;">
                                    <div class="text-subtitle-2 font-weight-bold text-truncate" :title="config.email">
                                        {{ config.email }}
                                    </div>
                                    <div class="d-flex align-center gap-2">
                                        <v-chip size="x-small" color="grey-lighten-3" variant="flat"
                                            class="font-weight-bold text-caption text-medium-emphasis">
                                            {{ config.imap_server }}
                                        </v-chip>
                                        <div v-if="config.auto_sync_enabled"
                                            class="text-success font-weight-bold text-caption d-flex align-center gap-1">
                                            <RefreshCw :size="10" />
                                            Auto
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="d-flex align-center gap-1">
                                <v-btn icon density="comfortable" variant="text" color="medium-emphasis"
                                    @click="openHistoryModal(config)" title="History">
                                    <Clock :size="18" />
                                </v-btn>
                                <v-btn icon density="comfortable" variant="text" color="medium-emphasis"
                                    @click="openEditEmailModal(config)" title="Settings">
                                    <Settings :size="18" />
                                </v-btn>
                            </div>
                        </div>

                        <!-- Footer -->
                        <div class="mt-auto pt-3 border-t d-flex align-center justify-space-between">
                            <div>
                                <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase opacity-70"
                                    style="font-size: 0.65rem;">Last Sync</div>
                                <div v-if="config.last_sync_at" class="text-caption font-weight-medium">
                                    {{ formatDate(config.last_sync_at).meta }}
                                    <span class="text-medium-emphasis">({{ formatDate(config.last_sync_at).day
                                        }})</span>
                                </div>
                                <div v-else class="text-caption text-warning font-weight-bold">Never</div>
                            </div>

                            <v-btn size="small" variant="outlined"
                                :color="syncStatus && syncStatus.status === 'running' && syncStatus.configId === config.id ? 'indigo' : undefined"
                                :loading="syncStatus && syncStatus.status === 'running' && syncStatus.configId === config.id"
                                @click="handleSync(config.id)" class="font-weight-bold">
                                {{ syncStatus && syncStatus.status === 'running' && syncStatus.configId === config.id ?
                                    'Scanning...' : 'Sync' }}
                                <template v-slot:append
                                    v-if="!(syncStatus && syncStatus.status === 'running' && syncStatus.configId === config.id)">
                                    <RefreshCw :size="12" class="ml-1" />
                                </template>
                            </v-btn>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Add New Email Card -->
            <v-col v-if="!searchQuery" cols="12" md="6" lg="4">
                <v-card class="add-account-card h-100 d-flex flex-column align-center justify-center" elevation="0"
                    @click="showEmailModal = true; editingEmailConfig = null">
                    <div class="add-icon-circle mb-3">
                        <Plus :size="32" />
                    </div>
                    <div class="font-weight-bold">Add Email Account</div>
                </v-card>
            </v-col>
        </v-row>

        <div v-if="emailConfigs.length === 0 && searchQuery" class="text-center py-12 text-medium-emphasis">
            <p>No emails match "{{ searchQuery }}"</p>
        </div>

        <!-- RECENT EMAIL SCAN LOGS -->
        <v-card class="mt-12 premium-glass-card" elevation="0">
            <v-card-title class="d-flex align-center justify-space-between py-4 px-6">
                <div class="d-flex align-center gap-3">
                    <v-avatar color="primary" variant="tonal" size="40" rounded>
                        <Mail :size="24" />
                    </v-avatar>
                    <div>
                        <div class="text-subtitle-1 font-weight-bold">Recent Scan Activity</div>
                        <div class="text-caption text-medium-emphasis">Logs of background sync processes</div>
                    </div>
                </div>
                <div class="d-flex align-center gap-2">
                    <v-chip size="small" variant="flat" color="grey-lighten-3" class="font-mono">
                        Total: {{ emailLogPagination.total }}
                    </v-chip>
                    <v-btn icon variant="text" density="comfortable" @click="fetchEmailLogs(undefined, true)">
                        <RefreshCw :size="16" />
                    </v-btn>
                </div>
            </v-card-title>

            <v-divider></v-divider>

            <v-table class="bg-transparent">
                <thead>
                    <tr>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Timestamp</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Account</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Status</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Items</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Message</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="log in emailLogs" :key="log.id" class="hover-row">
                        <td class="text-caption font-weight-medium">{{ formatDate(log.started_at).meta }}</td>
                        <td class="text-caption font-mono text-medium-emphasis">
                            {{(emailConfigs.find(c => c.id === log.config_id)?.email || 'Unknown').split('@')[0]}}
                        </td>
                        <td>
                            <v-chip size="x-small"
                                :color="log.status === 'completed' ? 'success' : log.status === 'running' ? 'info' : 'error'"
                                variant="flat" class="font-weight-bold text-uppercase">
                                {{ log.status }}
                            </v-chip>
                        </td>
                        <td class="text-caption font-mono">{{ log.items_processed || 0 }}</td>
                        <td class="text-caption text-truncate" style="max-width: 200px;" :title="log.message">
                            {{ log.message }}
                        </td>
                    </tr>
                    <tr v-if="emailLogs.length === 0">
                        <td colspan="5" class="text-center py-8 text-medium-emphasis font-italic">
                            <div class="d-flex flex-column align-center gap-2">
                                <MailOpen :size="48" class="text-medium-emphasis opacity-50 mb-2" />
                                No scan history found.
                            </div>
                        </td>
                    </tr>
                </tbody>
            </v-table>

            <v-divider v-if="emailLogPagination.total > emailLogPagination.limit"></v-divider>

            <div v-if="emailLogPagination.total > emailLogPagination.limit"
                class="d-flex align-center justify-space-between pa-4">
                <span class="text-caption text-medium-emphasis">
                    Showing {{ emailLogPagination.skip + 1 }} - {{ Math.min(emailLogPagination.skip +
                        emailLogPagination.limit,
                        emailLogPagination.total) }}
                </span>
                <div class="d-flex gap-2">
                    <v-btn size="small" variant="outlined" :disabled="emailLogPagination.skip === 0"
                        @click="emailLogPagination.skip -= emailLogPagination.limit; fetchEmailLogs()">
                        Previous
                    </v-btn>
                    <v-btn size="small" variant="outlined"
                        :disabled="emailLogPagination.skip + emailLogPagination.limit >= emailLogPagination.total"
                        @click="emailLogPagination.skip += emailLogPagination.limit; fetchEmailLogs()">
                        Next
                    </v-btn>
                </div>
            </div>
        </v-card>

        <!-- Email Config Modal -->
        <v-dialog v-model="showEmailModal" max-width="600">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <div class="d-flex align-center gap-3">
                        <v-avatar color="primary" variant="tonal" rounded>
                            <Mail :size="24" />
                        </v-avatar>
                        <div>
                            <div class="text-h6 font-weight-bold">{{ emailModalTitle }}</div>
                            <div class="text-caption text-medium-emphasis">{{ emailModalSubtitle }}</div>
                        </div>
                    </div>
                    <v-btn icon variant="text" density="comfortable" @click="showEmailModal = false">
                        <X :size="24" />
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-4">
                    <v-form @submit.prevent="saveEmailConfig">
                        <div class="mb-6">
                            <div class="d-flex align-center gap-2 mb-4 text-primary font-weight-bold text-subtitle-2">
                                <Server :size="16" /> Connection Details
                            </div>

                            <v-row>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model="emailForm.email" label="Email Address"
                                        placeholder="name@gmail.com" variant="outlined" required>
                                        <template v-slot:prepend-inner>
                                            <Mail :size="18" class="text-medium-emphasis mr-2" />
                                        </template>
                                    </v-text-field>
                                </v-col>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model="emailForm.password" label="App Password" type="password"
                                        placeholder="•••• •••• •••• ••••" variant="outlined" required>
                                        <template v-slot:prepend-inner>
                                            <Lock :size="18" class="text-medium-emphasis mr-2" />
                                        </template>
                                    </v-text-field>
                                </v-col>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model="emailForm.host" label="IMAP Server"
                                        placeholder="imap.gmail.com" variant="outlined" required></v-text-field>
                                </v-col>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model="emailForm.folder" label="Folder" placeholder="INBOX"
                                        variant="outlined"></v-text-field>
                                </v-col>
                            </v-row>
                            <v-alert type="info" variant="tonal" density="comfortable" class="mt-2 text-caption">
                                Use a generated <strong>App Password</strong>, not your main password.
                            </v-alert>
                        </div>

                        <v-divider class="mb-6"></v-divider>

                        <div class="mb-6">
                            <div class="d-flex align-center gap-2 mb-4 text-primary font-weight-bold text-subtitle-2">
                                <UserCheck :size="16" /> Ownership & Automation
                            </div>

                            <v-row>
                                <v-col cols="12" sm="6">
                                    <v-select v-model="emailForm.user_id" label="Assign to Family Member"
                                        :items="[{ title: '👤 Unassigned (Self)', value: null }, ...familyMembers.map(m => ({ title: `${m.avatar || '👤'} ${m.full_name || m.email}`, value: m.id }))]"
                                        variant="outlined"></v-select>
                                </v-col>
                                <v-col cols="12" sm="6" class="d-flex align-center">
                                    <v-switch v-model="emailForm.auto_sync" label="Auto Sync" color="success"
                                        hide-details inset>
                                        <template v-slot:label>
                                            <div class="d-flex flex-column">
                                                <span class="font-weight-bold">Auto Sync</span>
                                                <span class="text-caption text-medium-emphasis">Runs every 15
                                                    mins</span>
                                            </div>
                                        </template>
                                    </v-switch>
                                </v-col>
                            </v-row>
                        </div>

                        <div v-if="editingEmailConfig" class="mb-6 pa-4 bg-grey-lighten-4 rounded-lg">
                            <div
                                class="d-flex align-center gap-2 mb-4 text-medium-emphasis font-weight-bold text-subtitle-2">
                                <Settings :size="16" /> Advanced Controls
                            </div>
                            <v-row align="end">
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model="emailForm.last_sync_at" label="Custom Sync Point"
                                        type="datetime-local" variant="outlined" density="comfortable"
                                        hide-details></v-text-field>
                                </v-col>
                                <v-col cols="12" sm="6" class="d-flex gap-2">
                                    <v-btn variant="tonal" size="small" class="flex-grow-1" @click="rewindSync(3)">
                                        Rewind 3h
                                    </v-btn>
                                    <v-btn variant="tonal" size="small" class="flex-grow-1" @click="resetSyncHistory">
                                        Reset
                                    </v-btn>
                                </v-col>
                            </v-row>
                        </div>

                        <div class="d-flex gap-3 justify-space-between mt-6">
                            <v-btn v-if="editingEmailConfig" color="error" variant="text"
                                @click="deleteEmailConfig(editingEmailConfig)">
                                Remove
                            </v-btn>
                            <div class="d-flex gap-3 flex-grow-1 justify-end">
                                <v-btn variant="text" @click="showEmailModal = false">Cancel</v-btn>
                                <v-btn type="submit" color="primary">
                                    {{ editingEmailConfig ? 'Update Configuration' : 'Connect Account' }}
                                </v-btn>
                            </div>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Sync History Modal -->
        <v-dialog v-model="showHistoryModal" max-width="700">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">Sync History</span>
                    <v-btn icon variant="text" density="comfortable" @click="showHistoryModal = false">
                        <X :size="24" />
                    </v-btn>
                </v-card-title>

                <div class="pa-0">
                    <v-table>
                        <thead>
                            <tr>
                                <th class="text-left">Status</th>
                                <th class="text-left">Time</th>
                                <th class="text-left">Items</th>
                                <th class="text-left">Message</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="log in syncLogs" :key="log.id">
                                <td>
                                    <CheckCircle2 v-if="log.status === 'completed'" :size="16" class="text-success" />
                                    <XCircle v-else-if="log.status === 'error'" :size="16" class="text-error" />
                                    <Loader2 v-else :size="16" class="text-info animate-spin" />
                                </td>
                                <td class="text-caption">{{ formatDateFull(log.started_at) }}</td>
                                <td class="text-caption font-mono">{{ log.items_processed || 0 }}</td>
                                <td class="text-caption text-truncate" style="max-width: 250px;" :title="log.message">{{
                                    log.message }}</td>
                            </tr>
                            <tr v-if="syncLogs.length === 0">
                                <td colspan="4" class="text-center py-4 text-medium-emphasis">No logs found.</td>
                            </tr>
                        </tbody>
                    </v-table>
                </div>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useConfirmStore } from '@/stores/confirm'
import { localISOString } from '@/utils/time'
import { Settings, RefreshCw, Clock, Plus, Mail, Server, UserCheck, Search, Lock, X, CheckCircle2, XCircle, MailOpen, Loader2 } from 'lucide-vue-next'

const emailConfigs = ref<any[]>([])
const familyMembers = ref<any[]>([])
const searchQuery = ref('')
const loading = ref(false)

const notify = useNotificationStore()
const confirmDialog = useConfirmStore()

const showEmailModal = ref(false)
const editingEmailConfig = ref<string | null>(null)
const showHistoryModal = ref(false)
const syncLogs = ref<any[]>([])
const selectedHistoryConfigId = ref<string | null>(null)
const isSyncing = ref(false)
const syncStatus = ref<any>(null)

const emailForm = ref({
    email: '',
    password: '',
    host: 'imap.gmail.com',
    folder: 'INBOX',
    auto_sync: false,
    user_id: null as string | null,
    last_sync_at: '' as string
})

// Email Logs State
const emailLogs = ref<any[]>([])
const emailLogPagination = ref({ total: 0, limit: 10, skip: 0 })

// --- Computed ---
const emailModalTitle = computed(() => editingEmailConfig.value ? 'Edit Email Configuration' : 'Connect Email Account')
const emailModalSubtitle = computed(() => editingEmailConfig.value ? 'Update your email sync settings' : 'Link your bank email for automatic transaction imports')

// --- Methods ---
const fetchEmailLogs = async (configId?: string, resetSkip = false) => {
    try {
        if (resetSkip) emailLogPagination.value.skip = 0
        const res = await financeApi.getEmailLogs({
            limit: emailLogPagination.value.limit,
            skip: emailLogPagination.value.skip,
            config_id: configId
        })
        emailLogs.value = res.data.items
        emailLogPagination.value.total = res.data.total
    } catch (e) {
        console.error("Failed to fetch email logs", e)
    }
}

async function handleSync(configId: string) {
    isSyncing.value = true
    syncStatus.value = { status: 'running', configId }
    try {
        const res = await financeApi.syncEmailConfig(configId)
        syncStatus.value = { ...res.data, configId }
        if (res.data.status === 'completed') {
            fetchEmailLogs(undefined, true)
            fetchEmailLogs(undefined, true) // double fetch??
            fetchData()
        }
    } catch (e: any) {
        syncStatus.value = { status: 'error', message: e.response?.data?.detail || "Sync failed", configId }
    } finally {
        isSyncing.value = false
    }
}

async function saveEmailConfig() {
    try {
        const payload: any = {
            email: emailForm.value.email,
            password: emailForm.value.password,
            imap_server: emailForm.value.host,
            folder: emailForm.value.folder,
            auto_sync_enabled: emailForm.value.auto_sync,
            user_id: emailForm.value.user_id
        }

        if (emailForm.value.last_sync_at) {
            payload.last_sync_at = new Date(emailForm.value.last_sync_at).toISOString()
        }

        if (editingEmailConfig.value) {
            await financeApi.updateEmailConfig(editingEmailConfig.value, payload)
            notify.success("Email configuration updated")
        } else {
            await financeApi.createEmailConfig(payload)
            notify.success("Email configuration added")
        }

        showEmailModal.value = false
        emailForm.value = { email: '', password: '', host: 'imap.gmail.com', folder: 'INBOX', auto_sync: false, user_id: null, last_sync_at: '' }
        fetchData()
    } catch (e) {
        notify.error("Failed to save email config")
    }
}

function openEditEmailModal(config: any) {
    emailForm.value = {
        email: config.email,
        password: config.password,
        host: config.imap_server,
        folder: config.folder,
        auto_sync: config.auto_sync_enabled || false,
        user_id: config.user_id || null,
        last_sync_at: config.last_sync_at ? localISOString(new Date(config.last_sync_at)) : ''
    }
    editingEmailConfig.value = config.id
    showEmailModal.value = true
}

async function rewindSync(hours: number) {
    if (!editingEmailConfig.value) return
    const configId = editingEmailConfig.value

    const now = new Date()
    now.setHours(now.getHours() - hours)

    try {
        await financeApi.updateEmailConfig(configId, { last_sync_at: now.toISOString() })
        notify.info(`Rewound config. Triggering sync...`)
        showEmailModal.value = false
        await handleSync(configId)
        fetchData()
    } catch (e) {
        notify.error("Failed to rewind sync")
    }
}

async function resetSyncHistory() {
    if (!editingEmailConfig.value) return
    const configId = editingEmailConfig.value
    const isConfirmed = await confirmDialog.prompt("This will force a DEEP SCAN of ALL emails. This takes time. Continue?", "Deep Scan", "Scan Now", "Cancel")
    if (!isConfirmed) return
    try {
        await financeApi.updateEmailConfig(configId, { reset_sync_history: true })
        notify.info("Deep scan requested. Starting...")
        showEmailModal.value = false
        await handleSync(configId)
        fetchData()
    } catch (e) {
        notify.error("Failed to reset sync history")
    }
}

async function deleteEmailConfig(id: string) {
    const isConfirmed = await confirmDialog.prompt("Are you sure you want to remove this email account? This will stop future syncs.", "Remove Account", "Remove", "Cancel")
    if (!isConfirmed) return
    try {
        await financeApi.deleteEmailConfig(id)
        notify.success("Email account removed")
        showEmailModal.value = false
        fetchData()
    } catch (e) {
        notify.error("Failed to remove email config")
    }
}

async function openHistoryModal(config: any) {
    selectedHistoryConfigId.value = config.id
    showHistoryModal.value = true
    syncLogs.value = []
    try {
        const res = await financeApi.getEmailSyncLogs(config.id)
        syncLogs.value = res.data
    } catch (e) {
        notify.error("Failed to fetch logs")
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

function formatDateFull(dateStr: string) {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString()
}

// function getLogIcon removed as it is replaced by inline icons

onMounted(() => {
    fetchEmailLogs()
    fetchData()
})

const fetchData = async () => {
    loading.value = true
    try {
        const [emailRes, usersRes] = await Promise.all([
            financeApi.getEmailConfigs(),
            financeApi.getUsers()
        ])
        emailConfigs.value = emailRes.data
        familyMembers.value = usersRes.data
    } catch (e) {
        console.error("Failed to fetch email settings", e)
        notify.error("Failed to load email settings")
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
/* glass-card and email-card-premium removed - using global premium-glass-card */

.status-stripe-compact {
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 4px;
    background: rgb(var(--v-theme-success));
    opacity: 0.8;
}

.status-stripe-compact.inactive {
    background: rgb(var(--v-theme-grey));
    opacity: 0.5;
}

.status-stripe-compact.auto-sync {
    background: linear-gradient(180deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-secondary)));
    background-size: 100% 200%;
    animation: gradient-slide-v 3s ease infinite;
}

@keyframes gradient-slide-v {

    0%,
    100% {
        background-position: 50% 0%;
    }

    50% {
        background-position: 50% 100%;
    }
}

.add-account-card {
    border: 2px dashed rgba(var(--v-border-color), 0.3);
    background: transparent !important;
    transition: all 0.2s;
    cursor: pointer;
    min-height: 200px;
}

.add-account-card:hover {
    border-color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.05) !important;
    color: rgb(var(--v-theme-primary));
}

.add-icon-circle {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.hover-row:hover {
    background-color: rgba(var(--v-theme-on-surface), 0.03);
}

.gap-1 {
    gap: 4px;
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
</style>
