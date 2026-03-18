<template>
    <div class="animate-in">
        <!-- Search Bar -->
        <div class="d-flex flex-column flex-sm-row align-center justify-space-between gap-4 mb-6">
            <v-text-field v-model="searchQuery" prepend-inner-icon="Search" placeholder="Search devices..."
                variant="outlined" density="comfortable" hide-details class="flex-grow-1"
                style="max-width: 400px; width: 100%;" bg-color="surface"></v-text-field>

            <div class="d-flex align-center gap-3">
                <v-btn color="error" variant="tonal" rounded="pill" size="small" @click="handleLogoutAll"
                    class="font-weight-bold text-none px-4">
                    Logout from All Devices
                </v-btn>
                <h3 class="text-subtitle-1 font-weight-bold">Mobile Devices</h3>
                <v-chip color="success" size="small" variant="flat" class="font-weight-bold">
                    {{ devices.length }} Total
                </v-chip>
            </div>
        </div>

        <!-- PENDING DEVICES -->
        <div v-if="devices.some(d => !d.is_approved && !d.is_ignored)" class="mb-8">
            <div class="d-flex align-center gap-2 mb-4">
                <h3 class="text-h6 font-weight-bold text-warning">🔔 Pending Approval</h3>
                <v-chip color="warning" size="small" variant="flat" class="font-weight-bold">
                    {{devices.filter(d => !d.is_approved && !d.is_ignored).length}}
                </v-chip>
            </div>
            <v-row>
                <v-col v-for="device in devices.filter(d => !d.is_approved && !d.is_ignored)" :key="device.id" cols="12"
                    sm="6" md="4" lg="3">
                    <v-card class="premium-glass-card unapproved h-100" elevation="0">
                        <v-card-text>
                            <div class="d-flex align-center gap-3 mb-3">
                                <div class="dev-icon-wrapper"
                                    :class="{ 'android': device.device_name.toLowerCase().includes('pixel') || device.device_name.toLowerCase().includes('samsung'), 'apple': device.device_name.toLowerCase().includes('iphone') || device.device_name.toLowerCase().includes('ipad') }">
                                    <Smartphone :size="20"
                                        v-if="!(device.device_name.toLowerCase().includes('iphone') || device.device_name.toLowerCase().includes('ipad'))" />
                                    <span v-else class="text-h6"></span>
                                </div>
                                <div class="flex-grow-1 overflow-hidden">
                                    <div class="text-subtitle-2 font-weight-bold text-truncate"
                                        :title="device.device_name">
                                        {{ device.device_name }}
                                    </div>
                                </div>
                            </div>

                            <div class="bg-grey-lighten-4 rounded pa-2 mb-3">
                                <div class="d-flex justify-space-between align-center mb-1">
                                    <div class="d-flex align-center gap-1 text-caption font-weight-medium">
                                        <User :size="12" class="text-medium-emphasis" />
                                        {{ (getDeviceUser(device.user_id)?.full_name ||
                                            getDeviceUser(device.user_id)?.email || 'Unassigned').split('@')[0] }}
                                    </div>
                                    <v-btn icon density="compact" variant="text" size="u-small" color="primary"
                                        @click="openAssignModal(device)">
                                        <Edit2 :size="12" />
                                    </v-btn>
                                </div>
                                <div class="text-caption text-medium-emphasis d-flex align-center gap-1">
                                    <Clock :size="12" /> {{ formatDate(device.created_at).day }}
                                </div>
                            </div>

                            <div class="dev-id-footer mb-3">
                                <div class="d-flex justify-space-between align-center">
                                    <span class="text-caption font-mono text-medium-emphasis text-truncate">{{
                                        device.device_id }}</span>
                                    <v-btn icon density="compact" variant="text" size="small" color="medium-emphasis"
                                        @click="copyToClipboard(device.device_id)">
                                        <Copy :size="14" />
                                    </v-btn>
                                </div>
                            </div>

                            <div class="d-flex gap-2">
                                <v-btn color="primary" variant="flat" size="small" class="flex-grow-1"
                                    @click="toggleDeviceApproval(device)">
                                    Approve
                                </v-btn>
                                <v-btn color="grey-lighten-3" variant="flat" size="small" class="flex-grow-1"
                                    @click="toggleDeviceIgnored(device, true)">
                                    Ignore
                                </v-btn>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </div>

        <!-- ACTIVE DEVICES -->
        <div class="d-flex align-center gap-2 mb-4">
            <h3 class="text-h6 font-weight-bold display-1">✅ Active Devices</h3>
            <v-chip color="grey-lighten-3" size="small" variant="flat" class="font-weight-bold">
                {{devices.filter(d => d.is_approved).length}}
            </v-chip>
        </div>

        <v-row class="mb-12">
            <v-col v-for="device in devices.filter(d => d.is_approved)" :key="device.id" cols="12" sm="6" md="4" lg="3">
                <v-card class="premium-glass-card h-100" elevation="0" :class="{
                    'ignored': device.is_ignored,
                    'online-accent': isOnline(device.last_seen_at),
                    'offline-accent': !isOnline(device.last_seen_at)
                }">
                    <v-card-text>
                        <div class="d-flex align-center gap-3 mb-3">
                            <div class="dev-icon-wrapper"
                                :class="{ 'android': device.device_name.toLowerCase().includes('pixel') || device.device_name.toLowerCase().includes('samsung'), 'apple': device.device_name.toLowerCase().includes('iphone') || device.device_name.toLowerCase().includes('ipad') }">
                                <Smartphone :size="20"
                                    v-if="!(device.device_name.toLowerCase().includes('iphone') || device.device_name.toLowerCase().includes('ipad'))" />
                                <span v-else class="text-h6"></span>
                            </div>
                            <div class="flex-grow-1 overflow-hidden">
                                <div class="text-subtitle-2 font-weight-bold text-truncate" :title="device.device_name">
                                    {{ device.device_name }}
                                </div>
                            </div>
                        </div>

                        <div class="bg-grey-lighten-5 rounded pa-2 mb-3 border">
                            <div class="d-flex justify-space-between align-center mb-1">
                                <div class="d-flex align-center gap-1 text-caption font-weight-medium">
                                    <v-avatar size="16" class="mr-1">
                                        <v-img v-if="getDeviceUser(device.user_id)?.avatar?.length > 4"
                                            :src="getDeviceUser(device.user_id)?.avatar" cover></v-img>
                                        <span v-else class="text-caption">👤</span>
                                    </v-avatar>
                                    {{ (getDeviceUser(device.user_id)?.full_name || getDeviceUser(device.user_id)?.email
                                        || 'Unassigned').split('@')[0] }}
                                </div>
                                <v-btn icon density="compact" variant="text" size="x-small" color="primary"
                                    @click="openAssignModal(device)">
                                    <Edit2 :size="12" />
                                </v-btn>
                            </div>
                            <div class="text-caption text-medium-emphasis d-flex align-center gap-1"
                                :title="'Last Synchronization: ' + formatDate(device.last_seen_at || device.created_at).full">
                                <RefreshCw :size="10" /> {{ formatDate(device.last_seen_at || device.created_at).meta }}
                            </div>
                        </div>

                        <div class="dev-id-footer mb-3">
                            <div class="d-flex justify-space-between align-center">
                                <span class="text-caption font-mono text-medium-emphasis text-truncate">{{
                                    device.device_id }}</span>
                                <v-btn icon density="compact" variant="text" size="small" color="medium-emphasis"
                                    @click="copyToClipboard(device.device_id)">
                                    <Copy :size="14" />
                                </v-btn>
                            </div>
                        </div>

                        <div class="d-flex gap-2">
                            <v-btn :color="device.is_enabled ? 'grey-lighten-3' : 'success'" variant="flat" size="small"
                                class="flex-grow-1" @click="toggleDeviceEnabled(device)">
                                {{ device.is_enabled ? 'Pause' : 'Resume' }}
                            </v-btn>
                            <v-btn color="indigo-lighten-4" variant="flat" size="small"
                                style="min-width: 36px; padding: 0;" @click="testNotification(device)"
                                :loading="isTestingDevice === device.id" title="Test Notification">
                                <Bell v-if="isTestingDevice !== device.id" :size="14" class="text-indigo" />
                            </v-btn>
                            <v-btn color="error" variant="tonal" size="small" style="min-width: 36px; padding: 0;"
                                @click="deleteDeviceRequest(device)">
                                <Trash2 :size="14" />
                            </v-btn>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col v-if="devices.filter(d => d.is_approved).length === 0" cols="12">
                <div class="text-center py-12 text-medium-emphasis">
                    <div class="text-h2 mb-2">📱</div>
                    <h3 class="text-subtitle-1 font-weight-bold">No Devices Connected</h3>
                    <p class="text-body-2">Login from the mobile app to see your devices here.</p>
                </div>
            </v-col>
        </v-row>

        <!-- IGNORED DEVICES -->
        <div v-if="devices.some(d => d.is_ignored)" class="mt-8">
            <div class="d-flex align-center gap-2 mb-4 text-medium-emphasis opacity-70">
                <h3 class="text-subtitle-2 font-weight-bold text-uppercase">🚫 Ignored Devices</h3>
            </div>
            <v-row>
                <v-col v-for="device in devices.filter(d => d.is_ignored)" :key="device.id" cols="12" sm="6" md="4"
                    lg="3">
                    <v-card class="premium-glass-card ignored h-100" elevation="0">
                        <v-card-text>
                            <div class="d-flex align-center gap-3 mb-3">
                                <div class="dev-icon-wrapper">
                                    <Smartphone :size="20" class="text-medium-emphasis" />
                                </div>
                                <div class="flex-grow-1 overflow-hidden">
                                    <div class="text-subtitle-2 font-weight-bold text-medium-emphasis text-truncate">{{
                                        device.device_name }}</div>
                                    <div class="text-caption font-mono text-disabled text-truncate">{{ device.device_id
                                        }}</div>
                                </div>
                                <v-chip size="x-small" color="grey" variant="flat">Ignored</v-chip>
                            </div>
                            <div class="d-flex gap-2">
                                <v-btn color="grey-lighten-3" variant="flat" size="small" class="flex-grow-1"
                                    @click="toggleDeviceIgnored(device, false)">
                                    Restore
                                </v-btn>
                                <v-btn color="error" variant="tonal" size="small" class="flex-grow-1"
                                    @click="deleteDeviceRequest(device)">
                                    Delete
                                </v-btn>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </div>

        <!-- RECENT ACTIVITY LOG -->
        <v-card class="mt-12 premium-glass-card" elevation="0">
            <v-card-title class="d-flex align-center justify-space-between py-4 px-6">
                <div class="d-flex align-center gap-3">
                    <v-avatar color="indigo-lighten-5" variant="flat" size="40" rounded>
                        <ClipboardList :size="24" class="text-indigo" />
                    </v-avatar>
                    <div>
                        <div class="text-subtitle-1 font-weight-bold">Recent Activity Log</div>
                    </div>
                    <v-btn v-if="selectedEvents.length > 0" color="error" variant="tonal" size="small" class="ml-4"
                        @click="handleBulkDeleteEvents" :loading="isDeletingEvents">
                        Delete {{ selectedEvents.length }} Selected
                    </v-btn>
                </div>
                <div class="d-flex align-center gap-2">
                    <v-chip size="small" variant="flat" color="grey-lighten-3" class="font-mono">
                        Total: {{ eventPagination.total }}
                    </v-chip>
                    <v-btn icon variant="text" density="comfortable" @click="fetchIngestionEvents(undefined, true)">
                        <RefreshCw :size="16" />
                    </v-btn>
                </div>
            </v-card-title>

            <v-divider></v-divider>

            <v-table class="bg-transparent">
                <thead>
                    <tr>
                        <th class="width-40 px-4">
                            <v-checkbox-btn
                                :model-value="selectedEvents.length === ingestionEvents.length && ingestionEvents.length > 0"
                                @update:model-value="toggleSelectAllEvents" color="primary"></v-checkbox-btn>
                        </th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Timestamp</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Event</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Device</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Status</th>
                        <th class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Message</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="event in ingestionEvents" :key="event.id" class="hover-row">
                        <td class="px-4">
                            <v-checkbox-btn :model-value="selectedEvents.includes(event.id)"
                                @update:model-value="selectedEvents.includes(event.id) ? selectedEvents = selectedEvents.filter(id => id !== event.id) : selectedEvents.push(event.id)"
                                color="primary" density="compact"></v-checkbox-btn>
                        </td>
                        <td class="text-caption font-weight-medium">{{ formatDate(event.created_at).meta }}</td>
                        <td>
                            <v-chip size="x-small" variant="flat"
                                class="font-weight-bold text-uppercase bg-grey-lighten-4">
                                {{ event.event_type.replace('_', ' ') }}
                            </v-chip>
                        </td>
                        <td class="text-caption font-mono text-medium-emphasis">{{ event.device_id }}</td>
                        <td>
                            <v-chip size="x-small"
                                :color="event.status === 'success' ? 'success' : event.status === 'warning' ? 'warning' : 'error'"
                                variant="flat" class="font-weight-bold text-uppercase">
                                {{ event.status }}
                            </v-chip>
                        </td>
                        <td class="text-caption text-truncate" style="max-width: 200px;" :title="event.message">
                            {{ event.message }}
                        </td>
                    </tr>
                    <tr v-if="ingestionEvents.length === 0">
                        <td colspan="6" class="text-center py-8 text-medium-emphasis font-italic">
                            <div class="d-flex flex-column align-center gap-2">
                                <span class="text-h4">🔍</span>
                                No activity logs found.
                            </div>
                        </td>
                    </tr>
                </tbody>
            </v-table>
            <div v-if="eventPagination.total > eventPagination.limit"
                class="d-flex align-center justify-space-between pa-4 border-t">
                <span class="text-caption text-medium-emphasis">
                    Showing {{ eventPagination.skip + 1 }} - {{ Math.min(eventPagination.skip + eventPagination.limit,
                        eventPagination.total) }}
                </span>
                <div class="d-flex gap-2">
                    <v-btn size="small" variant="outlined" :disabled="eventPagination.skip === 0"
                        @click="eventPagination.skip -= eventPagination.limit; fetchIngestionEvents()">
                        Previous
                    </v-btn>
                    <v-btn size="small" variant="outlined"
                        :disabled="eventPagination.skip + eventPagination.limit >= eventPagination.total"
                        @click="eventPagination.skip += eventPagination.limit; fetchIngestionEvents()">
                        Next
                    </v-btn>
                </div>
            </div>
        </v-card>

        <!-- Device Assignment Modal -->
        <v-dialog v-model="showDeviceAssignModal" max-width="450">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <div class="d-flex align-center gap-2">
                        <Smartphone :size="20" class="text-primary" />
                        <span class="text-h6 font-weight-bold">Assign Device</span>
                    </div>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showDeviceAssignModal = false"></v-btn>
                </v-card-title>
                <v-card-text class="pa-4">
                    <v-form @submit.prevent="confirmAssignUser">
                        <v-text-field v-model="editDeviceName" label="Display Name" placeholder="e.g. iPhone 15 Pro"
                            variant="outlined" class="mb-2"></v-text-field>
                        <v-select v-model="selectedAssignUserId" label="Assign to Member"
                            :items="familyMembers.map(m => ({ title: m.full_name || m.email, value: m.id }))"
                            variant="outlined"></v-select>
                        <div class="d-flex justify-end gap-3 mt-4">
                            <v-btn variant="text" @click="showDeviceAssignModal = false">Cancel</v-btn>
                            <v-btn type="submit" color="primary">Save Changes</v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Device Delete Confirmation -->
        <v-dialog v-model="showDeviceDeleteConfirm" max-width="400">
            <v-card class="rounded-xl text-center pa-6">
                <div class="d-flex justify-center mb-4">
                    <div class="text-h2">🗑️</div>
                </div>
                <h3 class="text-h5 font-weight-bold mb-2">Remove Device?</h3>
                <p class="text-body-2 text-medium-emphasis mb-6">
                    Permanently remove <strong>{{ deviceToDelete?.device_name }}</strong>? This action cannot be undone.
                </p>
                <div class="d-flex gap-3">
                    <v-btn variant="text" class="flex-grow-1" @click="showDeviceDeleteConfirm = false">Cancel</v-btn>
                    <v-btn color="error" class="flex-grow-1" @click="confirmDeleteDevice">Yes, Delete</v-btn>
                </div>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { mobileApi, financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { Smartphone, Edit2, User, Clock, Copy, Trash2, RefreshCw, ClipboardList, Bell } from 'lucide-vue-next'

const notify = useNotificationStore()

// --- Internal State ---
const devices = ref<any[]>([])
const familyMembers = ref<any[]>([])
const searchQuery = ref('')


// Modal State
const showDeviceAssignModal = ref(false)
const deviceToAssign = ref<any>(null)
const selectedAssignUserId = ref<string | null>(null)
const editDeviceName = ref('')
const showDeviceDeleteConfirm = ref(false)
const deviceToDelete = ref<any>(null)



// Ingestion Events State
const ingestionEvents = ref<any[]>([])
const eventPagination = ref({ total: 0, limit: 10, skip: 0 })
const selectedEvents = ref<string[]>([])
const isDeletingEvents = ref(false)
const isTestingDevice = ref<string | null>(null)

function formatDate(dateStr: string) {
    if (!dateStr) return { day: 'N/A', meta: '' }
    const d = new Date(dateStr)
    return {
        day: d.toLocaleDateString(),
        meta: d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        full: d.toLocaleString()
    }
}

const getDeviceUser = (userId: string) => {
    if (!userId) return null
    return familyMembers.value.find(u => u.id === userId)
}

const isOnline = (dateStr: string) => {
    if (!dateStr) return false
    const lastSeen = new Date(dateStr).getTime()
    const now = new Date().getTime()
    return (now - lastSeen) < (10 * 60 * 1000) // 10 minutes
}

const fetchIngestionEvents = async (deviceId?: string, resetSkip = false) => {
    try {
        if (resetSkip) eventPagination.value.skip = 0
        const res = await financeApi.getIngestionEvents({
            limit: eventPagination.value.limit,
            skip: eventPagination.value.skip,
            device_id: deviceId
        })
        ingestionEvents.value = res.data.items
        eventPagination.value.total = res.data.total
        selectedEvents.value = []
    } catch (e) {
        console.error("Failed to fetch events", e)
    }
}

const toggleSelectAllEvents = () => {
    if (selectedEvents.value.length === ingestionEvents.value.length) {
        selectedEvents.value = []
    } else {
        selectedEvents.value = ingestionEvents.value.map(e => e.id)
    }
}

const fetchData = async () => {
    try {
        const [devicesRes, usersRes] = await Promise.all([
            mobileApi.getDevices(),
            financeApi.getUsers()
        ])
        devices.value = devicesRes.data
        familyMembers.value = usersRes.data
    } catch (e) {
        console.error("Failed to fetch device settings", e)
        notify.error("Failed to load device settings")
    }
}

onMounted(() => {
    fetchIngestionEvents()
    fetchData()
})

function openAssignModal(device: any) {
    deviceToAssign.value = device
    selectedAssignUserId.value = device.user_id || null
    editDeviceName.value = device.device_name || ''
    showDeviceAssignModal.value = true
}

async function confirmAssignUser() {
    if (!deviceToAssign.value) return
    try {
        await mobileApi.updateDevice(deviceToAssign.value.id, {
            device_name: editDeviceName.value,
            user_id: selectedAssignUserId.value
        })
        notify.success("Device settings updated")
        showDeviceAssignModal.value = false
        fetchData()
    } catch (e: any) {
        notify.error("Failed to update device")
    }
}

const toggleDeviceApproval = async (device: any) => {
    try {
        await mobileApi.toggleApproval(device.id, !device.is_approved)
        fetchData()
    } catch (e) {
        notify.error("Failed to toggle device approval")
    }
}

const toggleDeviceIgnored = async (device: any, ignored: boolean) => {
    try {
        await mobileApi.toggleIgnored(device.id, ignored)
        notify.success(ignored ? "Device ignored" : "Device restored")
        fetchData()
    } catch (e) {
        notify.error("Failed to update status")
    }
}

const toggleDeviceEnabled = async (device: any) => {
    try {
        await mobileApi.toggleEnabled(device.id, !device.is_enabled)
        notify.success(device.is_enabled ? "Device ingestion disabled" : "Device ingestion enabled")
        fetchData()
    } catch (e) {
        notify.error("Failed to update device status")
    }
}

const testNotification = async (device: any) => {
    isTestingDevice.value = device.id
    try {
        await mobileApi.testNotification(device.id)
        notify.success(`Test notification sent to ${device.device_name}`)
    } catch (e) {
        notify.error("Failed to send test notification")
    } finally {
        isTestingDevice.value = null
    }
}

const deleteDeviceRequest = (device: any) => {
    deviceToDelete.value = device
    showDeviceDeleteConfirm.value = true
}

const confirmDeleteDevice = async () => {
    if (!deviceToDelete.value) return
    try {
        await mobileApi.deleteDevice(deviceToDelete.value.id)
        notify.success("Device permanently removed")
        showDeviceDeleteConfirm.value = false
        fetchData()
    } catch (e) {
        notify.error("Failed to delete device")
    } finally {
        deviceToDelete.value = null
    }
}

const handleBulkDeleteEvents = async () => {
    if (selectedEvents.value.length === 0) return
    isDeletingEvents.value = true
    try {
        await financeApi.bulkDeleteEvents(selectedEvents.value)
        notify.success(`Deleted ${selectedEvents.value.length} events`)
        fetchIngestionEvents(undefined, true)
    } catch (e) {
        notify.error("Failed to delete events")
    } finally {
        isDeletingEvents.value = false
    }
}

const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    notify.success("Device ID copied!")
}

const handleLogoutAll = async () => {
    try {
        await financeApi.logoutAll();
        notify.success("Successfully logged out from all devices");
        
        // Clear local session
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        
        // Redirect to login
        window.location.href = '/login';
    } catch (e) {
        notify.error("Failed to logout from all devices");
    }
}
</script>

<style scoped>
.premium-glass-card.unapproved {
    border-top: 3px solid rgb(var(--v-theme-warning)) !important;
    background: rgba(var(--v-theme-warning), 0.05) !important;
}

.premium-glass-card.ignored {
    opacity: 0.7;
    background: rgba(var(--v-theme-surface), 0.5) !important;
}

.premium-glass-card.online-accent {
    border-top: 3px solid rgb(var(--v-theme-success)) !important;
}

.premium-glass-card.offline-accent {
    border-top: 3px solid rgb(var(--v-theme-error)) !important;
}

.dev-id-footer {
    padding: 6px 8px;
    background: rgba(var(--v-theme-surface-variant), 0.1);
    border-radius: 6px;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}
</style>
