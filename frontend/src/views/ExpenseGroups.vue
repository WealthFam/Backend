<template>
    <MainLayout>
        <v-container fluid class="dashboard-page pa-6 pa-md-10 relative-pos overflow-hidden">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Header -->
                <v-row class="mb-10 align-center">
                    <v-col cols="12" md="6">
                        <h1 class="text-h4 font-weight-black mb-1">Expense Groups</h1>
                        <p class="text-subtitle-1 text-on-surface opacity-70 font-weight-bold d-flex align-center">
                            Organize and track your spending buckets
                        </p>
                    </v-col>

                    <v-col cols="12" md="6" class="d-flex justify-md-end align-center gap-3">
                        <div class="glass-toggle-pill mr-4">
                            <span class="toggle-option" :class="{ active: !showArchived }"
                                @click="showArchived = false">Active</span>
                            <span class="toggle-option" :class="{ active: showArchived }"
                                @click="showArchived = true">Archived</span>
                        </div>
                        <v-chip color="primary" variant="tonal" size="small" rounded="pill"
                            class="font-weight-black px-4 bg-surface elevation-0 border">
                            {{ filteredGroups.length }} Groups
                        </v-chip>
                    </v-col>
                </v-row>

                <!-- Filter Bar -->
                <div class="d-flex flex-column flex-sm-row gap-4 mb-8">
                    <v-text-field v-model="searchQuery" placeholder="Search groups..." variant="outlined"
                        density="comfortable" hide-details class="premium-search-field flex-grow-1" bg-color="surface"
                        rounded="lg">
                        <template v-slot:prepend-inner>
                            <Search :size="18" class="text-primary mr-2" />
                        </template>
                    </v-text-field>

                    <div style="width: 160px">
                        <v-select v-model="selectedYear" :items="yearOptions" item-title="label" item-value="value"
                            variant="outlined" density="comfortable" hide-details rounded="lg" bg-color="surface"
                            class="premium-select" :menu-icon="null">
                            <template v-slot:append-inner>
                                <ChevronDown :size="16" class="text-primary opacity-70" />
                            </template>
                        </v-select>
                    </div>
                </div>

                <!-- Loading State -->
                <div v-if="loading" class="d-flex justify-center align-center py-16">
                    <v-progress-circular indeterminate color="primary" size="64" width="6" />
                </div>

                <!-- Empty State -->
                <div v-else-if="filteredGroups.length === 0"
                    class="premium-glass-card d-flex flex-column align-center justify-center py-16 px-10 text-center mx-auto"
                    style="max-width: 600px; margin-top: 50px;">
                    <v-avatar color="primary" variant="tonal" size="100" class="mb-8">
                        <Wallet :size="50" class="text-primary" />
                    </v-avatar>
                    <h3 class="text-h4 font-weight-black mb-1">No Groups Found</h3>
                    <p class="text-subtitle-1 text-on-surface opacity-70 font-weight-bold mb-8">
                        Create a group to start tracking your expenses.
                    </p>
                    <v-btn color="primary" variant="flat" rounded="pill" height="52"
                        class="px-10 font-weight-black elevation-2" @click="openAddModal">
                        Create Expense Group
                    </v-btn>
                </div>

                <!-- Groups Grid -->
                <v-row v-else class="pb-16">
                    <!-- Add New Group Card -->
                    <v-col cols="12" sm="6" md="4" lg="4">
                        <v-card @click="openAddModal"
                            class="premium-glass-card d-flex flex-column align-center justify-center h-100 cursor-pointer border-dashed border-primary group"
                            style="border-width: 2px !important; min-height: 280px; background: rgba(var(--v-theme-primary), 0.05)"
                            rounded="xl">
                            <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                                style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                                <Plus :size="36" color="white" stroke-width="3" />
                            </v-avatar>
                            <span class="text-h6 font-weight-black text-primary">New Group</span>
                            <span class="text-caption font-weight-bold opacity-60 text-slate-500">Add expense
                                bucket</span>
                        </v-card>
                    </v-col>

                    <!-- Existing Groups -->
                    <v-col v-for="group in filteredGroups" :key="group.id" cols="12" sm="6" md="4" lg="4">
                        <v-card rounded="xl" class="premium-glass-card group h-100 d-flex flex-column overflow-hidden"
                            elevation="0" @click="openEditModal(group)">
                            <div class="pa-5 d-flex justify-space-between align-center">
                                <v-avatar :style="{ background: generateColor(group.name).bg }" rounded="lg" size="48"
                                    class="elevation-0 border">
                                    <span class="text-h6" :style="{ color: generateColor(group.name).text }">
                                        {{ group.icon || group.name.charAt(0).toUpperCase() }}
                                    </span>
                                </v-avatar>

                                <div class="d-flex gap-1">
                                    <v-btn icon variant="text" size="x-small" color="medium-emphasis"
                                        @click.stop="openEditModal(group)">
                                        <Pencil :size="14" />
                                    </v-btn>
                                    <v-btn icon variant="text" size="x-small" color="error"
                                        @click.stop="confirmDelete(group)">
                                        <Trash2 :size="14" />
                                    </v-btn>
                                </div>
                            </div>

                            <div class="px-5 pb-5 flex-grow-1">
                                <h3 class="text-subtitle-1 font-weight-black text-truncate mb-0">{{ group.name }}</h3>
                                <div class="d-flex align-center text-tiny font-weight-bold text-medium-emphasis mb-2">
                                    <Calendar :size="12" class="mr-1" />
                                    {{ group.start_date ? formatDate(group.start_date) : 'No Date' }}
                                </div>
                                <div class="text-caption text-medium-emphasis line-clamp-2" style="min-height: 2.6em">
                                    {{ group.description || 'No description' }}
                                </div>

                                <div v-if="Number(group.budget) > 0" class="mt-4">
                                    <div class="d-flex justify-space-between align-end mb-1">
                                        <div>
                                            <span class="text-h6 font-weight-black">{{
                                                formatAmount(group.total_spend || 0) }}</span>
                                            <span class="text-tiny font-weight-bold text-medium-emphasis ml-1">of {{
                                                formatAmount(group.budget) }}</span>
                                        </div>
                                        <span class="text-caption font-weight-black" :class="getBudgetColor(group)">
                                            {{ getBudgetPercentage(group).toFixed(0) }}%
                                        </span>
                                    </div>
                                    <v-progress-linear :model-value="getBudgetPercentage(group)"
                                        :color="getBudgetColorCode(group)" height="8" rounded="pill"
                                        class="elevation-1 opacity-90" />
                                </div>

                                <div v-else
                                    class="mt-4 py-2 bg-surface-variant bg-opacity-10 rounded-lg text-center border border-dashed border-opacity-20">
                                    <span class="text-caption font-weight-bold text-medium-emphasis">No Budget
                                        Set</span>
                                </div>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>
            </div>

            <!-- Create/Edit Modal -->
            <v-dialog v-model="showModal" max-width="500" transition="dialog-bottom-transition">
                <v-card rounded="xl" class="premium-glass-modal elevation-24">
                    <div class="px-6 pt-6 pb-2 d-flex justify-space-between align-center">
                        <div>
                            <div class="text-overline font-weight-black text-primary mb-1 letter-spacing-2">
                                {{ isEditing ? 'Edit Group' : 'New Group' }}
                            </div>
                            <h2 class="text-h5 font-weight-black text-content">
                                {{ isEditing ? 'Refine Details' : 'Create Bucket' }}
                            </h2>
                        </div>
                        <v-btn icon variant="text" @click="showModal = false" density="comfortable"
                            class="bg-surface-variant bg-opacity-10 opacity-70 hover:opacity-100">
                            <X :size="20" />
                        </v-btn>
                    </div>

                    <v-card-text class="px-6 py-4">
                        <v-form @submit.prevent="handleSubmit">
                            <!-- Icon Picker -->
                            <div class="mb-6 text-center">
                                <v-avatar size="64" :color="generateColor(form.name).bg" variant="flat" class="mb-4">
                                    <span class="text-h3">{{ form.icon || '?' }}</span>
                                </v-avatar>
                                <div class="d-flex justify-center gap-2 flex-wrap">
                                    <v-btn
                                        v-for="emoji in ['✈️', '🏠', '🍔', '🛒', '💊', '🎓', '🎮', '🎁', '💸', '💼', '🚗', '👶']"
                                        :key="emoji" icon variant="text" density="comfortable"
                                        :color="form.icon === emoji ? 'primary' : 'medium-emphasis'" class="emoji-btn"
                                        :class="{ 'selected-emoji': form.icon === emoji }" @click="form.icon = emoji">
                                        <span class="text-h6">{{ emoji }}</span>
                                    </v-btn>
                                </div>
                            </div>

                            <v-text-field v-model="form.name" label="Group Name" placeholder="e.g. Thailand Trip"
                                variant="outlined" density="comfortable" hide-details rounded="lg" bg-color="surface"
                                class="mb-4 font-weight-bold text-body-1" autofocus>
                                <template v-slot:prepend-inner>
                                    <Type :size="18" class="text-medium-emphasis" />
                                </template>
                            </v-text-field>

                            <v-textarea v-model="form.description" label="Description" rows="2" variant="outlined"
                                density="comfortable" hide-details rounded="lg" bg-color="surface"
                                class="mb-4 text-body-2" />

                            <v-row dense>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model.number="form.budget" label="Total Budget" type="number"
                                        prefix="₹" variant="outlined" density="comfortable" hide-details rounded="lg"
                                        bg-color="surface" class="font-weight-black">
                                    </v-text-field>
                                </v-col>
                                <v-col cols="12" sm="6">
                                    <div class="d-flex align-center h-100 px-2">
                                        <v-switch v-model="form.is_active" color="success" hide-details
                                            density="compact" inset>
                                            <template v-slot:label>
                                                <span class="text-caption font-weight-bold ml-2">
                                                    {{ form.is_active ? 'ACTIVE' : 'ARCHIVED' }}
                                                </span>
                                            </template>
                                        </v-switch>
                                    </div>
                                </v-col>
                            </v-row>

                            <div class="mt-4">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">DURATION
                                    (OPTIONAL)</label>
                                <v-row dense>
                                    <v-col cols="6">
                                        <v-text-field v-model="form.start_date" type="date" variant="outlined"
                                            density="comfortable" hide-details rounded="lg" bg-color="surface" />
                                    </v-col>
                                    <v-col cols="6">
                                        <v-text-field v-model="form.end_date" type="date" variant="outlined"
                                            density="comfortable" hide-details rounded="lg" bg-color="surface" />
                                    </v-col>
                                </v-row>
                            </div>
                        </v-form>
                    </v-card-text>

                    <v-card-actions class="px-6 pb-6 pt-2">
                        <v-btn variant="text" @click="showModal = false" height="48" rounded="lg"
                            class="px-6 font-weight-bold text-none text-medium-emphasis">
                            Cancel
                        </v-btn>
                        <v-spacer />
                        <v-btn color="primary" variant="flat" rounded="lg" height="48"
                            class="px-8 font-weight-black text-none elevation-4" @click="handleSubmit">
                            {{ isEditing ? 'Save Changes' : 'Create Group' }}
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <!-- Delete Confirmation -->
            <v-dialog v-model="showDeleteConfirm" max-width="400">
                <v-card rounded="xl" class="pa-6 text-center premium-glass-modal elevation-24">
                    <div class="d-flex justify-center mb-6">
                        <div class="error-glow pa-4 rounded-circle">
                            <Trash2 :size="32" class="text-error" />
                        </div>
                    </div>
                    <h3 class="text-h5 font-weight-black mb-2">Delete Group?</h3>
                    <p class="text-medium-emphasis mb-8 px-4">
                        Are you sure you want to delete <strong class="text-high-emphasis">{{ groupToDelete?.name
                        }}</strong>?
                        This action cannot be undone.
                    </p>
                    <div class="d-flex gap-3 justify-center">
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
import { Plus, Trash2, Calendar, Wallet, Type, X, Pencil, Search, ChevronDown } from 'lucide-vue-next'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useNotificationStore } from '@/stores/notification'

const notify = useNotificationStore()
const { formatAmount } = useCurrency()
const loading = ref(true)
const expenseGroups = ref<any[]>([])
const searchQuery = ref('')
const showArchived = ref(false)

const showModal = ref(false)
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const form = ref({
    name: '',
    description: '',
    is_active: true,
    budget: 0,
    start_date: '',
    end_date: '',
    icon: ''
})

const selectedYear = ref<string>('All')
const showDeleteConfirm = ref(false)
const groupToDelete = ref<any>(null)

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
    editingId.value = null
    form.value = {
        name: '',
        description: '',
        is_active: true,
        budget: 0,
        start_date: '',
        end_date: '',
        icon: ''
    }
    showModal.value = true
}

const openEditModal = (group: any) => {
    isEditing.value = true
    editingId.value = group.id
    form.value = {
        name: group.name,
        description: group.description || '',
        is_active: group.is_active,
        budget: group.budget || 0,
        start_date: group.start_date ? group.start_date.split('T')[0] : '',
        end_date: group.end_date ? group.end_date.split('T')[0] : '',
        icon: group.icon || ''
    }
    showModal.value = true
}

const getBudgetPercentage = (group: any) => {
    if (!group.budget || group.budget === 0) return 0
    return Math.min(100, ((group.total_spend || 0) / group.budget) * 100)
}

const getBudgetColor = (group: any) => {
    if (!group.budget) return 'text-medium-emphasis'
    const pct = getBudgetPercentage(group)
    if (pct >= 100) return 'text-error'
    if (pct >= 80) return 'text-warning'
    return 'text-success'
}

const getBudgetColorCode = (group: any) => {
    if (!group.budget) return '#cbd5e1'
    const pct = getBudgetPercentage(group)
    if (pct >= 100) return '#ef4444'
    if (pct >= 80) return '#f97316'
    return '#10b981'
}

const handleSubmit = async () => {
    try {
        if (isEditing.value && editingId.value) {
            await financeApi.updateExpenseGroup(editingId.value, form.value)
            notify.success("Group updated successfully")
        } else {
            await financeApi.createExpenseGroup(form.value)
            notify.success("Group created successfully")
        }
        showModal.value = false
        fetchGroups()
    } catch (e) {
        notify.error("Failed to save group")
    }
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

const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    })
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

.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    border-radius: 50%;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.gap-3 {
    gap: 12px;
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    box-shadow: none !important;
}

.premium-glass-card:hover {
    transform: translateY(-4px);
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
    background: rgba(var(--v-theme-surface), 0.85) !important;
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1) !important;
}

.glass-toggle-pill {
    background: rgba(var(--v-theme-surface-variant), 0.1);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 20px;
    padding: 4px;
    display: flex;
    gap: 4px;
}

.toggle-option {
    padding: 6px 16px;
    border-radius: 16px;
    font-size: 0.8rem;
    font-weight: 600;
    cursor: pointer;
    color: rgba(var(--v-theme-on-surface), 0.6);
    transition: all 0.2s ease;
}

.toggle-option.active {
    background: rgb(var(--v-theme-surface));
    color: rgb(var(--v-theme-primary));
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.premium-glass-modal {
    background: rgba(var(--v-theme-surface), 0.9) !important;
    backdrop-filter: blur(24px) saturate(200%);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.emoji-btn {
    opacity: 0.6;
    transition: all 0.2s;
}

.emoji-btn:hover,
.emoji-btn.selected-emoji {
    opacity: 1;
    transform: scale(1.2);
}

.group-on-hover-scale {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.group:hover .group-on-hover-scale {
    transform: scale(1.1);
}

.error-glow {
    background: rgba(var(--v-theme-error), 0.05);
    border: 1px solid rgba(var(--v-theme-error), 0.1);
}
</style>
