<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Premium Header -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="4">
                        <div class="d-flex align-center">
                            <h1 class="text-h6 font-weight-black text-content">Expense Groups</h1>
                        </div>
                        <p class="text-subtitle-2 text-medium-emphasis font-weight-bold mt-1 opacity-70">
                            Organize and track your family's spending buckets
                        </p>
                    </v-col>

                    <v-col cols="12" md="8" class="d-flex flex-column flex-md-row align-md-center justify-end ga-3">
                        <!-- Navigation Tabs (Pill style) -->
                        <div class="premium-pill-tabs flex-grow-1 flex-md-grow-0 d-flex overflow-x-auto">
                            <v-tabs v-model="showArchived" color="primary" density="comfortable" hide-slider show-arrows
                                class="rounded-xl">
                                <v-tab :value="false" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center ga-2">
                                        <Activity :size="16" />
                                        <span>Active</span>
                                        <v-chip v-if="!showArchived" size="x-small" color="primary"
                                            class="ml-1 font-weight-black">
                                            {{ filteredGroups.length }}
                                        </v-chip>
                                    </div>
                                </v-tab>
                                <v-tab :value="true" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center ga-2">
                                        <Archive :size="16" />
                                        <span>Archived</span>
                                        <v-chip v-if="showArchived" size="x-small" color="primary"
                                            class="ml-1 font-weight-black">
                                            {{ filteredGroups.length }}
                                        </v-chip>
                                    </div>
                                </v-tab>
                            </v-tabs>
                        </div>
                    </v-col>
                </v-row>

                <!-- Filter Bar -->
                <div class="d-flex flex-column flex-sm-row ga-4 mb-8">
                    <v-text-field v-model="searchQuery" placeholder="Search groups..." variant="outlined"
                        density="comfortable" hide-details class="flex-grow-1" bg-color="surface" rounded="lg">
                        <template v-slot:prepend-inner>
                            <Search :size="18" class="text-primary mr-2" />
                        </template>
                    </v-text-field>

                    <div style="width: 160px">
                        <v-select v-model="selectedYear" :items="yearOptions" item-title="label" item-value="value"
                            variant="outlined" density="comfortable" hide-details rounded="lg" bg-color="surface">
                        </v-select>
                    </div>
                </div>

                <!-- Loading State -->
                <div v-if="loading" class="d-flex justify-center align-center py-16">
                    <v-progress-circular indeterminate color="primary" size="64" width="6" />
                </div>

                <!-- Empty State -->
                <div v-else-if="filteredGroups.length === 0"
                    class="elevation-2 d-flex flex-column align-center justify-center py-16 px-10 text-center mx-auto rounded-xl border-dashed"
                    style="max-width: 600px; margin-top: 50px; background: rgba(var(--v-theme-primary), 0.03); border: 2px dashed rgba(var(--v-theme-primary), 0.2) !important;">
                    <v-avatar color="primary" variant="tonal" size="100" class="mb-8">
                        <Wallet :size="50" class="text-primary" />
                    </v-avatar>
                    <h3 class="text-h4 font-weight-black mb-1 text-primary">No Groups Found</h3>
                    <p class="text-subtitle-1 text-medium-emphasis font-weight-bold mb-8 opacity-70">
                        Organize your finances by creating spending buckets for trips, projects, or categories.
                    </p>
                    <v-btn color="primary" variant="flat" rounded="pill" height="52"
                        class="px-10 font-weight-black elevation-8 group-on-hover-scale" @click="openAddModal">
                        <Plus :size="20" class="mr-2" />
                        Create Your First Group
                    </v-btn>
                </div>

                <!-- Groups Grid -->
                <v-row v-else class="pb-16">
                    <!-- Add New Group Card -->
                    <v-col v-if="!showArchived" cols="12" sm="6" md="4" lg="4">
                        <v-card @click="openAddModal"
                            class="elevation-0 d-flex flex-column align-center justify-center h-100 cursor-pointer border-dashed border-primary group premium-add-card"
                            style="border-width: 2px !important; min-height: 280px;" rounded="xl">
                            <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                                style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                                <Plus :size="36" color="white" stroke-width="3" />
                            </v-avatar>
                            <span class="text-h6 font-weight-black text-primary">New Group</span>
                            <span class="text-caption font-weight-bold opacity-60 text-medium-emphasis">Add expense
                                bucket</span>
                        </v-card>
                    </v-col>

                    <!-- Existing Groups -->
                    <v-col v-for="group in filteredGroups" :key="group.id" cols="12" sm="6" md="4" lg="4">
                        <v-card rounded="xl" class="elevation-2 group h-100 d-flex flex-column overflow-hidden"
                            @click="openEditModal(group)">
                            <div class="pa-5 d-flex justify-space-between align-start">
                                <v-avatar :style="{ background: generateColor(group.name).bg }" rounded="lg" size="52"
                                    class="elevation-2 border-thin">
                                    <span class="text-h5" :style="{ color: generateColor(group.name).text }">
                                        {{ group.icon || group.name.charAt(0).toUpperCase() }}
                                    </span>
                                </v-avatar>

                                <div class="d-flex ga-1">
                                    <v-btn icon variant="text" size="x-small" color="medium-emphasis"
                                        class="bg-surface-lighten-1 elevation-1" @click.stop="openEditModal(group)">
                                        <Pencil :size="14" />
                                    </v-btn>
                                    <v-btn icon variant="text" size="x-small" color="error"
                                        class="bg-error-lighten-5 elevation-1" @click.stop="confirmDelete(group)">
                                        <Trash2 :size="14" />
                                    </v-btn>
                                </div>
                            </div>

                            <div class="px-5 pb-5 flex-grow-1 d-flex flex-column">
                                <div class="d-flex justify-space-between align-center mb-1">
                                    <h3 class="text-h6 font-weight-black text-truncate pr-2">{{ group.name }}</h3>
                                    <v-chip size="x-small" variant="tonal" color="primary" class="font-weight-black">
                                        {{ group.start_date ? formatDateShort(group.start_date) : '?' }} - {{
                                            group.end_date ?
                                        formatDateShort(group.end_date) : '?' }}
                                    </v-chip>
                                </div>

                                <div class="text-caption text-medium-emphasis line-clamp-2 mb-4 opacity-70"
                                    style="min-height: 2.6em">
                                    {{ group.description || 'No description provided' }}
                                </div>

                                <v-spacer />

                                <!-- Financial Section -->
                                <div v-if="Number(group.budget) > 0" class="mt-4">
                                    <div class="d-flex justify-space-between align-end mb-2">
                                        <div>
                                            <div
                                                class="text-tiny font-weight-black opacity-50 text-uppercase letter-spacing-1 mb-1">
                                                Total Spent</div>
                                            <span class="text-h5 font-weight-black">{{ formatAmount(group.total_spend ||
                                                0) }}</span>
                                        </div>
                                        <div class="text-right">
                                            <div
                                                class="text-tiny font-weight-black opacity-50 text-uppercase letter-spacing-1 mb-1">
                                                Consumed</div>
                                            <span class="text-subtitle-1 font-weight-black"
                                                :class="getBudgetColor(group)">
                                                {{ getBudgetPercentage(group).toFixed(0) }}%
                                            </span>
                                        </div>
                                    </div>

                                    <v-progress-linear :model-value="getBudgetPercentage(group)"
                                        :color="getBudgetColorCode(group)" height="10" rounded="pill"
                                        class="elevation-0 bg-grey-lighten-4 mb-3" />

                                    <div class="d-flex justify-space-between text-tiny font-weight-bold">
                                        <div class="d-flex flex-column">
                                            <span class="opacity-50 text-uppercase"
                                                style="font-size: 0.65rem">Balance</span>
                                            <span
                                                :class="parseFloat(group.budget) - (group.total_spend || 0) < 0 ? 'text-error' : 'text-success'">
                                                {{ formatAmount(Math.max(0, parseFloat(group.budget) -
                                                (group.total_spend || 0))) }}
                                            </span>
                                        </div>
                                        <div class="d-flex flex-column align-end">
                                            <span class="opacity-50 text-uppercase"
                                                style="font-size: 0.65rem">Target</span>
                                            <span class="text-high-emphasis">{{ formatAmount(group.budget) }}</span>
                                        </div>
                                    </div>
                                </div>

                                <div v-else class="mt-4 pt-4 border-t-dashed">
                                    <div class="d-flex justify-space-between align-center">
                                        <div>
                                            <div
                                                class="text-tiny font-weight-black opacity-50 text-uppercase letter-spacing-1 mb-1">
                                                Total Spent</div>
                                            <span class="text-h5 font-weight-black">{{ formatAmount(group.total_spend ||
                                                0) }}</span>
                                        </div>
                                        <v-chip size="small" variant="tonal" color="medium-emphasis"
                                            class="font-weight-black">
                                            No Budget Set
                                        </v-chip>
                                    </div>
                                </div>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>
            </div>

            <!-- Expense Group Modal Component -->
            <ExpenseGroupModal v-model="showModal" :is-editing="isEditing" :group-data="selectedGroup"
                @saved="fetchGroups" />

            <!-- Delete Confirmation -->
            <v-dialog v-model="showDeleteConfirm" max-width="400">
                <v-card rounded="xl" class="pa-6 text-center bg-surface elevation-24">
                    <div class="d-flex justify-center mb-6">
                        <div class="bg-error-lighten-5 border-error pa-4 rounded-circle">
                            <Trash2 :size="32" class="text-error" />
                        </div>
                    </div>
                    <h3 class="text-h5 font-weight-black mb-2">Delete Group?</h3>
                    <p class="text-medium-emphasis mb-8 px-4">
                        Are you sure you want to delete <strong class="text-high-emphasis">{{ groupToDelete?.name
                            }}</strong>?
                        This action cannot be undone.
                    </p>
                    <div class="d-flex ga-3 justify-center">
                        <v-btn variant="text" rounded="lg" height="48" class="px-6 font-weight-bold"
                            @click="showDeleteConfirm = false">Cancel</v-btn>
                        <v-btn color="error" variant="flat" rounded="lg" height="48" class="px-6 font-weight-bold"
                            @click="doDelete">Delete Group</v-btn>
                    </div>
                </v-card>
            </v-dialog>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { Plus, Wallet, Pencil, Search, Activity, Archive } from 'lucide-vue-next'
import MainLayout from '@/layouts/MainLayout.vue'
import ExpenseGroupModal from '@/components/groups/ExpenseGroupModal.vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useNotificationStore } from '@/stores/notification'

const notify = useNotificationStore()
const { formatAmount } = useCurrency()
const loading = ref(true)
const expenseGroups = ref<any[]>([])
const searchQuery = ref('')
const showArchived = ref(false)

const selectedYear = ref<string>('All')
const showDeleteConfirm = ref(false)
const groupToDelete = ref<any>(null)
const selectedGroup = ref<any>(null)
const showModal = ref(false)
const isEditing = ref(false)

const yearOptions = computed(() => {
    const currentYear = new Date().getFullYear()
    const years = []
    years.push({ label: 'All Years', value: 'All' })
    for (let y = currentYear + 1; y >= 2018; y--) {
        years.push({ label: y.toString(), value: y.toString() })
    }
    return years
})

const filteredGroups = computed(() => {
    let result = expenseGroups.value.filter(g => g.is_active === !showArchived.value)

    if (selectedYear.value && selectedYear.value !== 'All') {
        result = result.filter(g => {
            const dateToUse = g.start_date || g.created_at
            if (!dateToUse) return false
            return new Date(dateToUse).getFullYear().toString() === selectedYear.value
        })
    }

    if (searchQuery.value) {
        const q = searchQuery.value.toLowerCase()
        result = result.filter(g =>
            g.name.toLowerCase().includes(q) ||
            (g.description && g.description.toLowerCase().includes(q))
        )
    }

    return result
})

const fetchGroups = async () => {
    loading.value = true
    try {
        const res = await financeApi.getExpenseGroups()
        expenseGroups.value = res.data
    } catch (e) {
        console.error("Failed to fetch expense groups", e)
        notify.error("Failed to load expense groups")
    } finally {
        loading.value = false
    }
}

const openAddModal = () => {
    isEditing.value = false
    selectedGroup.value = null
    showModal.value = true
}

const openEditModal = (group: any) => {
    isEditing.value = true
    selectedGroup.value = group
    showModal.value = true
}

const formatDateShort = (dateStr: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    })
}

const getBudgetPercentage = (group: any) => {
    if (!group.budget || group.budget === 0) return 0
    return Math.min(100, ((group.total_spend || 0) / group.budget) * 100)
}

const getBudgetColorCode = (group: any) => {
    if (!group.budget) return '#cbd5e1'
    const pct = getBudgetPercentage(group)
    if (pct >= 100) return '#ef4444'
    if (pct >= 80) return '#f97316'
    return '#10b981'
}

const getBudgetColor = (group: any) => {
    if (!group.budget) return 'text-medium-emphasis'
    const pct = getBudgetPercentage(group)
    if (pct >= 100) return 'text-error'
    if (pct >= 80) return 'text-warning'
    return 'text-success'
}

const confirmDelete = (group: any) => {
    groupToDelete.value = group
    showDeleteConfirm.value = true
}

const doDelete = async () => {
    if (!groupToDelete.value) return
    try {
        await financeApi.deleteExpenseGroup(groupToDelete.value.id)
        notify.success("Group deleted")
        fetchGroups()
    } catch (e) {
        notify.error("Failed to delete group")
    } finally {
        showDeleteConfirm.value = false
        groupToDelete.value = null
    }
}

const generateColor = (name: string) => {
    const colors = ['#eff6ff', '#f0fdf4', '#fef2f2', '#fff7ed', '#f0f9ff', '#faf5ff']
    const textColors = ['#1d4ed8', '#15803d', '#b91c1c', '#c2410c', '#0369a1', '#7e22ce']
    let hash = 0
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    const index = Math.abs(hash) % colors.length
    return { bg: colors[index], text: textColors[index] }
}

onMounted(() => {
    fetchGroups()
})
</script>

<style scoped>
.dashboard-page {
    position: relative;
    min-height: calc(100vh - 64px);
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.elevation-1 {
    box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06) !important;
}

.elevation-2 {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    box-shadow: none !important;
}

.elevation-2:hover {
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
    background: rgba(var(--v-theme-surface), 0.85) !important;
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1) !important;
}

.text-tiny {
    font-size: 0.75rem;
    letter-spacing: 0.025em;
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
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
    background: rgb(var(--v-theme-primary));
    width: 600px;
    height: 600px;
    top: -200px;
    right: -100px;
}

.blob-2 {
    background: rgb(var(--v-theme-secondary));
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

/* Premium Tabs */
.premium-pill-tabs {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(10px);
    padding: 6px;
    border-radius: 24px;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-tab {
    text-transform: none !important;
    letter-spacing: 0;
    font-weight: 700;
    font-size: 0.9rem;
    color: rgb(var(--v-theme-on-surface), 0.6);
    transition: all 0.3s ease;
    min-width: 120px;
}

.premium-tab.v-tab--selected {
    background: rgb(var(--v-theme-primary));
    color: white !important;
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

.group {
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    border: 1px solid rgba(var(--v-border-color), 0.05);
}

.premium-add-card {
    background: rgba(var(--v-theme-primary), 0.05) !important;
    transition: all 0.3s ease;
}

.premium-add-card:hover {
    background: rgba(var(--v-theme-primary), 0.1) !important;
    transform: translateY(-4px);
}

.text-primary {
    color: rgb(var(--v-theme-primary)) !important;
}
</style>