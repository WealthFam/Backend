<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useNotificationStore } from '@/stores/notification'
import { useConfirmStore } from '@/stores/confirm'
import { useAuthStore } from '@/stores/auth'
import { useGoalStore } from '@/stores/finance/goals'
import PremiumSkeleton from '@/components/common/PremiumSkeleton.vue'
import {
    Plus,
    Calendar,
    Trash2,
    Pencil,
    TrendingUp,
    Building2,
    X,
    Target,
    Activity,
    Wallet,
    ChevronDown
} from 'lucide-vue-next'

const notify = useNotificationStore()
const confirmDialog = useConfirmStore()
const authStore = useAuthStore()
const goalStore = useGoalStore()
const { formatAmount } = useCurrency()

const goals = computed(() => goalStore.goals)
const accounts = computed(() => goalStore.accounts)
const portfolio = computed(() => goalStore.portfolio)
const loading = ref(goalStore.goals.length === 0)
const showModal = ref(false)
const showDeleteModal = ref(false)
const goalToDelete = ref<string | null>(null)
const showAssetModal = ref(false)
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const selectedGoalId = ref<string | null>(null)

const goalForm = ref({
    name: '',
    target_amount: 0,
    target_date: '',
    icon: '🎯',
    color: '#3b82f6',
    owner_id: null as string | null
})

const assetForm = ref({
    type: 'MANUAL', // MANUAL, BANK_ACCOUNT, MUTUAL_FUND
    name: '',
    manual_amount: 0,
    interest_rate: 0,
    linked_account_id: null as string | null,
    holding_id: null as string | null
})

const fetchGoals = async () => {
    if (goalStore.goals.length === 0) loading.value = true
    try {
        await goalStore.fetchGoals(authStore.selectedMemberId || undefined)
    } catch (e) {
        notify.error("Failed to load goals")
    } finally {
        loading.value = false
    }
}

const fetchAccounts = async () => {
    try {
        await goalStore.fetchAccounts(authStore.selectedMemberId || undefined)
    } catch (e) {
        console.error("Failed to fetch accounts")
    }
}

const fetchPortfolio = async () => {
    try {
        await goalStore.fetchPortfolio()
    } catch (e) {
        console.error("Failed to fetch portfolio")
    }
}

const openAddModal = () => {
    isEditing.value = false
    editingId.value = null
    goalForm.value = {
        name: '',
        target_amount: 0,
        target_date: '',
        icon: '🎯',
        color: '#3b82f6',
        owner_id: authStore.selectedMemberId
    }
    showModal.value = true
}

const openEditModal = (goal: any) => {
    isEditing.value = true
    editingId.value = goal.id
    goalForm.value = {
        name: goal.name,
        target_amount: Number(goal.target_amount),
        target_date: goal.target_date ? goal.target_date.split('T')[0] : '',
        icon: goal.icon || '🎯',
        color: goal.color || '#3b82f6',
        owner_id: goal.owner_id
    }
    showModal.value = true
}

const handleGoalSubmit = async () => {
    try {
        if (isEditing.value && editingId.value) {
            await financeApi.updateInvestmentGoal(editingId.value, goalForm.value)
            notify.success("Goal updated")
        } else {
            await financeApi.createInvestmentGoal(goalForm.value)
            notify.success("Goal created")
        }
        showModal.value = false
        fetchGoals()
    } catch (e) {
        notify.error("Failed to save goal")
    }
}

const confirmDelete = (id: string) => {
    goalToDelete.value = id
    showDeleteModal.value = true
}

const deleteGoal = async () => {
    if (!goalToDelete.value) return
    try {
        await financeApi.deleteInvestmentGoal(goalToDelete.value)
        notify.success("Goal deleted")
        showDeleteModal.value = false
        goalToDelete.value = null
        fetchGoals()
    } catch (e) {
        notify.error("Failed to delete goal")
    }
}

const openAssetModal = (goalId: string) => {
    selectedGoalId.value = goalId
    assetForm.value = {
        type: 'MANUAL',
        name: '',
        manual_amount: 0,
        interest_rate: 0,
        linked_account_id: null,
        holding_id: null
    }
    showAssetModal.value = true
    fetchPortfolio() // Refresh when opening
}

const handleAssetSubmit = async () => {
    if (!selectedGoalId.value) return
    try {
        const payload = { ...assetForm.value }
        // Clean up empty strings to avoid DB constraint issues
        if (!payload.linked_account_id) payload.linked_account_id = null
        if (!payload.holding_id) payload.holding_id = null

        if (payload.type === 'MUTUAL_FUND') {
            if (!payload.holding_id) throw new Error("Please select a fund")
            await financeApi.linkHoldingToGoal(selectedGoalId.value, payload.holding_id)
            notify.success("Mutual Fund linked to goal")
        } else {
            await (financeApi as any).addGoalAsset(selectedGoalId.value, payload)
            notify.success("Asset added to goal")
        }
        showAssetModal.value = false
        fetchGoals()
    } catch (e: any) {
        notify.error(e.message || "Failed to add asset")
    }
}

const removeAsset = async (assetId: string) => {
    try {
        await (financeApi as any).removeGoalAsset(assetId)
        notify.success("Asset removed")
        fetchGoals()
    } catch (e) {
        notify.error("Failed to remove asset")
    }
}

const unlinkHolding = async (goalId: string, holdingId: string) => {
    const isConfirmed = await confirmDialog.prompt('Are you sure you want to remove this mutual fund from the goal?', 'Remove Fund', 'Remove', 'Cancel')
    if (!isConfirmed) return
    try {
        await financeApi.unlinkHoldingFromGoal(goalId, holdingId)
        notify.success("Mutual fund unlinked")
        fetchGoals()
    } catch (e) {
        notify.error("Failed to unlink mutual fund")
    }
}

const accountOptions = computed(() => {
    return accounts.value.map(acc => ({
        label: `${acc.name} (${formatAmount(acc.balance)})`,
        value: acc.id,
        type: acc.type // Ensure type is passed for icon logic
    }))
})

const portfolioOptions = computed(() => {
    if (!portfolio.value || !Array.isArray(portfolio.value)) return []
    return portfolio.value.map(fund => ({
        label: `${fund.folio_number || 'No Folio'} • ${formatAmount(fund.current_value || 0)} • ${fund.scheme_name || 'Unnamed Fund'}`,
        value: fund.id
    }))
})

// Asset Summary Calculation
const calculateGoalSummary = (goal: any) => {
    const assetTotal = (goal.assets || []).reduce((sum: number, a: any) => sum + Number(a.current_value || 0), 0)
    const holdingTotal = (goal.holdings || []).reduce((sum: number, h: any) => sum + Number(h.current_value || 0), 0)
    const total = assetTotal + holdingTotal
    const count = (goal.assets?.length || 0) + (goal.holdings?.length || 0)
    return { total, count }
}

const memberOptions = computed(() => {
    const members = authStore.familyMembers.map(m => ({
        title: m.full_name || m.email,
        value: m.id,
        initials: (m.full_name || m.email).substring(0, 2).toUpperCase()
    }))
    return [{ title: 'Shared (Everyone)', value: null, initials: 'ALL' }, ...members]
})

// Lifecycle and Watchers
onMounted(() => {
    fetchGoals()
    fetchAccounts()
})

watch(() => authStore.selectedMemberId, () => {
    fetchGoals()
    fetchAccounts()
})
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <div class="relative-pos z-10">
                <!-- Header (Title left, Actions right) -->
                <v-row class="mb-10 align-center">
                    <v-col cols="12" md="6">
                        <h1 class="text-h4 font-weight-black mb-1">Financial Goals</h1>
                        <p class="text-subtitle-1 text-on-surface opacity-70 font-weight-bold d-flex align-center">
                            Track and achieve your aspirations
                            <v-chip v-if="authStore.selectedMemberId" size="x-small" color="primary" variant="flat"
                                class="ml-3 font-weight-black letter-spacing-1">
                                MEMBER FILTER ACTIVE
                            </v-chip>
                        </p>
                    </v-col>

                    <v-col cols="12" md="6" class="d-flex justify-md-end align-center gap-3">
                        <v-chip color="primary" variant="tonal" size="small" rounded="pill"
                            class="font-weight-black px-4 bg-surface elevation-0 border">
                            <Target :size="14" class="mr-2" />
                            {{ goals.length }} Active Goals
                        </v-chip>
                    </v-col>
                </v-row>

                <!-- Loading State -->
                <v-row v-if="loading" class="pb-16 pt-8">
                    <v-col v-for="i in 3" :key="`skel-goal-${i}`" cols="12" sm="6" md="4" lg="4">
                        <PremiumSkeleton type="category-card" glass />
                    </v-col>
                </v-row>

                <!-- Empty State -->
                <div v-else-if="goals.length === 0"
                    class="premium-glass-card d-flex flex-column align-center justify-center py-16 px-10 text-center mx-auto"
                    style="max-width: 600px; margin-top: 50px;">
                    <v-avatar color="primary" variant="tonal" size="100" class="mb-8">
                        <Target :size="50" class="text-primary" />
                    </v-avatar>
                    <h3 class="text-h4 font-weight-black mb-1">No Goals Set Yet</h3>
                    <p class="text-subtitle-1 text-on-surface opacity-70 font-weight-bold mb-8">
                        Define your financial aspirations and link your assets to track your progress in real-time.
                    </p>
                    <v-btn color="primary" variant="flat" rounded="pill" height="52"
                        class="px-10 font-weight-black elevation-2" @click="openAddModal">
                        Set Your First Goal
                    </v-btn>
                </div>

                <!-- Goals Grid -->
                <v-row v-else class="pb-16">
                    <!-- Add New Goal Card (New Pattern) -->
                    <v-col cols="12" sm="6" md="4" lg="4">
                        <v-card @click="openAddModal"
                            class="premium-glass-card d-flex flex-column align-center justify-center h-100 cursor-pointer border-dashed border-primary group"
                            style="border-width: 2px !important; min-height: 380px; background: rgba(var(--v-theme-primary), 0.05)"
                            rounded="xl">
                            <v-avatar color="primary" size="64" class="mb-4 elevation-8 group-on-hover-scale"
                                style="box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.3)">
                                <Plus :size="36" color="white" stroke-width="3" />
                            </v-avatar>
                            <span class="text-h6 font-weight-black text-primary">Add New Goal</span>
                            <span class="text-caption font-weight-bold opacity-60">Define your next
                                aspiration</span>
                        </v-card>
                    </v-col>

                    <v-col v-for="goal in goals" :key="goal.id" cols="12" sm="6" md="4" lg="4">
                        <v-card rounded="xl" class="premium-glass-card group h-100 d-flex flex-column overflow-hidden"
                            elevation="0">
                            <div class="pa-5 d-flex justify-space-between align-center">
                                <v-avatar :style="{ background: goal.color + '15' }" rounded="lg" size="48"
                                    class="elevation-0 border" :class="`border-${goal.color}`">
                                    <span class="text-h6" :style="{ color: goal.color }">{{ goal.icon }}</span>
                                </v-avatar>

                                <div class="goal-card-actions d-flex gap-1">
                                    <v-btn icon variant="text" size="x-small" color="medium-emphasis"
                                        @click="openEditModal(goal)">
                                        <Pencil :size="14" />
                                        <v-tooltip activator="parent" location="top">Edit Goal</v-tooltip>
                                    </v-btn>
                                    <v-btn icon variant="text" size="x-small" color="error"
                                        @click="confirmDelete(goal.id)">
                                        <Trash2 :size="14" />
                                        <v-tooltip activator="parent" location="top">Delete Goal</v-tooltip>
                                    </v-btn>
                                </div>
                            </div>

                            <div class="px-5 pb-5">
                                <h3 class="text-subtitle-1 font-weight-black text-truncate mb-0">{{ goal.name }}
                                </h3>
                                <div class="d-flex align-center text-tiny font-weight-bold text-medium-emphasis">
                                    <Calendar :size="12" class="mr-1" />
                                    {{ goal.target_date ? new Date(goal.target_date).toLocaleDateString() :
                                        'No Target Date' }}
                                </div>

                                <div class="mt-4">
                                    <div class="d-flex justify-space-between align-end mb-1">
                                        <div>
                                            <span class="text-h6 font-weight-black">{{
                                                formatAmount(goal.current_amount)
                                            }}</span>
                                            <span class="text-tiny font-weight-bold text-medium-emphasis ml-1">of {{
                                                formatAmount(goal.target_amount) }}</span>
                                        </div>
                                        <span class="text-caption font-weight-black" :style="{ color: goal.color }">{{
                                            Math.round(goal.progress_percentage) }}%</span>
                                    </div>
                                    <v-progress-linear :model-value="goal.progress_percentage" :color="goal.color"
                                        height="8" rounded="pill" class="goal-progress-bar elevation-1" />
                                </div>
                            </div>

                            <div v-if="goal.remaining_amount > 0" class="mt-4">
                                <div
                                    class="d-inline-flex align-center text-caption font-weight-bold text-medium-emphasis bg-surface-variant bg-opacity-10 px-3 py-1 rounded-pill blur-backdrop">
                                    <Activity :size="12" class="mr-2 text-primary" />
                                    <span>{{ formatAmount(goal.remaining_amount) }} left to reach goal</span>
                                </div>
                            </div>

                            <v-divider :color="goal.color" class="opacity-10" />

                            <!-- Linked Assets Overhaul -->
                            <div class="pa-4 bg-surface bg-opacity-1">
                                <div class="d-flex justify-space-between align-center mb-1">
                                    <h4 class="text-overline font-weight-black text-medium-emphasis letter-spacing-1">
                                        Linked Assets</h4>
                                    <v-btn variant="text" size="x-small" color="primary" density="compact"
                                        class="text-none font-weight-bold" @click="openAssetModal(goal.id)">
                                        <Plus :size="14" class="mr-1" /> Add Asset
                                    </v-btn>
                                </div>

                                <!-- Asset Summary Bar -->
                                <div class="d-flex align-center mb-4 opacity-70">
                                    <Activity :size="12" class="mr-1 text-primary" />
                                    <span class="text-tiny font-weight-black">
                                        Total Linked: {{ formatAmount(calculateGoalSummary(goal).total) }}
                                        <span class="mx-1 text-medium-emphasis">•</span>
                                        {{ calculateGoalSummary(goal).count }} {{ calculateGoalSummary(goal).count
                                            === 1
                                            ? 'source' : 'sources' }}
                                    </span>
                                </div>

                                <div class="assets-scroll-area">
                                    <!-- Empty State -->
                                    <div v-if="!goal.assets?.length && !goal.holdings?.length"
                                        class="text-center py-6 bg-surface-variant bg-opacity-5 rounded-xl border border-dashed border-opacity-20 d-flex flex-column align-center">
                                        <Wallet :size="32" class="text-medium-emphasis mb-2 opacity-20" />
                                        <span class="text-caption font-weight-bold text-medium-emphasis opacity-60">No
                                            assets linked yet</span>
                                    </div>

                                    <div v-else class="asset-rows">
                                        <!-- Section: Mutual Funds -->
                                        <template v-if="goal.holdings?.length">
                                            <div
                                                class="text-tiny font-weight-black text-uppercase text-medium-emphasis mb-3 letter-spacing-1 d-flex align-center">
                                                <TrendingUp :size="10" class="mr-1" /> Mutual Funds
                                            </div>
                                            <div v-for="(h, index) in goal.holdings" :key="h.id" class="asset-row-item">
                                                <v-divider v-if="index > 0" class="my-2 border-opacity-5" />
                                                <div class="d-flex align-center justify-space-between py-2">
                                                    <div class="d-flex align-center overflow-hidden">
                                                        <div class="d-flex flex-column">
                                                            <div class="text-caption font-weight-black text-truncate">
                                                                {{ h.scheme_name }}</div>
                                                            <div
                                                                class="text-tiny font-weight-bold text-medium-emphasis text-truncate opacity-70">
                                                                Folio: {{ h.folio_number }}</div>
                                                        </div>
                                                    </div>
                                                    <div class="d-flex align-center pl-4">
                                                        <div class="text-right mr-4">
                                                            <div class="text-caption font-weight-black">{{
                                                                formatAmount(h.current_value) }}</div>
                                                        </div>
                                                        <v-btn icon variant="text" size="x-small" color="error"
                                                            class="opacity-30 hover-opacity-100"
                                                            @click="unlinkHolding(goal.id, h.id)">
                                                            <X :size="14" />
                                                        </v-btn>
                                                    </div>
                                                </div>
                                            </div>
                                        </template>

                                        <!-- Section: Other Assets -->
                                        <template v-if="goal.assets?.length">
                                            <div
                                                class="text-tiny font-weight-black text-uppercase text-medium-emphasis mb-3 mt-4 letter-spacing-1 d-flex align-center">
                                                <Building2 :size="10" class="mr-1" /> Accounts & Other Assets
                                            </div>
                                            <div v-for="(a, index) in goal.assets" :key="a.id" class="asset-row-item">
                                                <v-divider v-if="index > 0" class="my-2 border-opacity-5" />
                                                <div class="d-flex align-center justify-space-between py-2">
                                                    <div class="d-flex align-center overflow-hidden">
                                                        <div class="d-flex flex-column">
                                                            <div class="text-caption font-weight-black text-truncate">
                                                                {{ a.display_name }}</div>
                                                            <div
                                                                class="text-tiny font-weight-bold text-medium-emphasis opacity-70">
                                                                {{ a.type.split('_').join(' ') }}</div>
                                                        </div>
                                                    </div>
                                                    <div class="d-flex align-center pl-4">
                                                        <div class="text-right mr-4">
                                                            <div class="text-caption font-weight-black">{{
                                                                formatAmount(a.current_value) }}</div>
                                                        </div>
                                                        <v-btn icon variant="text" size="x-small" color="error"
                                                            class="opacity-30 hover-opacity-100"
                                                            @click="removeAsset(a.id)">
                                                            <X :size="14" />
                                                        </v-btn>
                                                    </div>
                                                </div>
                                            </div>
                                        </template>
                                    </div>
                                </div>
                            </div>
                        </v-card>
                    </v-col>
                </v-row>
            </div>
            <!-- Goal Create/Edit Dialog -->
            <v-dialog v-model="showModal" max-width="500" persistent transition="dialog-bottom-transition">
                <v-card rounded="xl" class="premium-glass-modal elevation-24">
                    <div class="px-6 pt-6 pb-2 d-flex justify-space-between align-start">
                        <div>
                            <div class="text-overline font-weight-black text-primary mb-1 letter-spacing-2">
                                {{ isEditing ? 'Edit Goal' : 'New Goal' }}
                            </div>
                            <h2 class="text-h4 font-weight-black text-content">
                                {{ isEditing ? 'Refine Strategy' : 'Define Target' }}
                            </h2>
                        </div>
                        <v-btn icon variant="text" @click="showModal = false" density="comfortable"
                            class="bg-surface-variant bg-opacity-10 opacity-70 hover:opacity-100">
                            <X :size="20" />
                        </v-btn>
                    </div>

                    <v-card-text class="px-6 py-4">
                        <v-row dense>
                            <v-col cols="12" class="mb-4">
                                <div class="d-flex gap-4">
                                    <div style="width: 80px">
                                        <label
                                            class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">ICON</label>
                                        <v-text-field v-model="goalForm.icon" variant="outlined" density="comfortable"
                                            hide-details rounded="lg" class="icon-picker-field centered-input"
                                            bg-color="surface" />
                                    </div>
                                    <div class="flex-grow-1">
                                        <label
                                            class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">GOAL
                                            NAME</label>
                                        <v-text-field v-model="goalForm.name" placeholder="e.g. Dream Home"
                                            variant="outlined" density="comfortable" hide-details rounded="lg"
                                            bg-color="surface" color="primary" class="font-weight-bold" />
                                    </div>
                                </div>
                            </v-col>

                            <v-col cols="12" sm="6">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">TARGET
                                    AMOUNT</label>
                                <v-text-field v-model.number="goalForm.target_amount" type="number" prefix="₹"
                                    variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" color="primary" class="font-weight-black" />
                            </v-col>

                            <v-col cols="12" sm="6">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">TARGET
                                    DATE</label>
                                <v-text-field v-model="goalForm.target_date" type="date" variant="outlined"
                                    density="comfortable" hide-details rounded="lg" bg-color="surface" color="primary"
                                    class="font-weight-bold" />
                            </v-col>

                            <v-col cols="12" class="mt-4">
                                <label
                                    class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">OWNERSHIP</label>
                                <v-select v-model="goalForm.owner_id" :items="memberOptions" item-title="title"
                                    item-value="value" variant="outlined" density="comfortable" hide-details
                                    rounded="lg" bg-color="surface" placeholder="Assign Owner" color="primary">
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
                                    <template v-slot:item="{ props, item }">
                                        <v-list-item v-bind="props" :title="item.raw.title" class="rounded-lg ma-1">
                                            <template v-slot:prepend>
                                                <v-avatar size="28" color="primary" variant="tonal" class="mr-2">
                                                    <span class="text-caption font-weight-black">{{
                                                        item.raw.initials
                                                    }}</span>
                                                </v-avatar>
                                            </template>
                                        </v-list-item>
                                    </template>
                                    <template v-slot:selection="{ item }">
                                        <div class="d-flex align-center">
                                            <v-avatar size="24" color="primary" variant="tonal" class="mr-2">
                                                <span class="text-tiny font-weight-black">{{ item.raw.initials
                                                }}</span>
                                            </v-avatar>
                                            <span class="text-body-2 font-weight-bold">{{ item.raw.title }}</span>
                                        </div>
                                    </template>
                                </v-select>
                            </v-col>

                            <v-col cols="12" class="mt-4">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-3 d-block">THEME
                                    COLOR</label>
                                <div class="d-flex flex-wrap justify-space-between align-center px-2">
                                    <div v-for="c in ['#4f46e5', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']"
                                        :key="c" class="color-dot-premium" :style="{ background: c }"
                                        :class="{ active: goalForm.color === c }" @click="goalForm.color = c">
                                        <div v-if="goalForm.color === c" class="color-dot-ring"></div>
                                    </div>
                                </div>
                            </v-col>
                        </v-row>
                    </v-card-text>

                    <v-card-actions class="px-6 pb-6 pt-2">
                        <v-btn variant="text" @click="showModal = false" height="48" rounded="lg"
                            class="px-6 font-weight-bold text-none text-medium-emphasis">
                            Cancel
                        </v-btn>
                        <v-spacer />
                        <v-btn color="primary" variant="flat" rounded="lg" height="48"
                            class="px-8 font-weight-black text-none elevation-4" @click="handleGoalSubmit">
                            <span class="text-white">{{ isEditing ? 'Save Changes' : 'Create Goal' }}</span>
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <!-- Asset Linking Dialog -->
            <v-dialog v-model="showAssetModal" max-width="450" transition="dialog-bottom-transition">
                <v-card rounded="xl" class="premium-glass-modal elevation-24">
                    <div class="px-6 pt-6 pb-2 d-flex justify-space-between align-center">
                        <div>
                            <div class="text-overline font-weight-black text-primary mb-1 letter-spacing-2">Link
                                Assets
                            </div>
                            <h2 class="text-h5 font-weight-black text-content">Connect Wealth</h2>
                        </div>
                        <v-btn icon variant="text" @click="showAssetModal = false" density="comfortable"
                            class="bg-surface-variant bg-opacity-10 opacity-70 hover:opacity-100">
                            <X :size="20" />
                        </v-btn>
                    </div>

                    <v-card-text class="px-6 py-4">
                        <div class="d-flex mb-6 pa-1 bg-surface rounded-lg border border-opacity-10 elevation-0">
                            <v-btn v-for="t in ['MANUAL', 'BANK_ACCOUNT', 'MUTUAL_FUND']" :key="t" variant="flat"
                                rounded="md" size="small"
                                class="flex-grow-1 text-none font-weight-black h-36 letter-spacing-0"
                                :color="assetForm.type === t ? 'primary' : 'transparent'"
                                :class="assetForm.type === t ? 'elevation-2' : 'text-medium-emphasis opacity-60 hover:opacity-100'"
                                @click="assetForm.type = t">
                                <component
                                    :is="t === 'MANUAL' ? Activity : (t === 'BANK_ACCOUNT' ? Building2 : TrendingUp)"
                                    :size="14" class="mr-2" />
                                {{ t === 'BANK_ACCOUNT' ? 'Bank' : (t === 'MUTUAL_FUND' ? 'Funds' : 'Manual') }}
                            </v-btn>
                        </div>

                        <v-form @submit.prevent="handleAssetSubmit">
                            <div v-if="assetForm.type === 'MANUAL'">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">ASSET
                                    NAME</label>
                                <v-text-field v-model="assetForm.name" label="Asset Name" placeholder="e.g. EPF, Gold"
                                    variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" class="mb-4" />
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">CURRENT
                                    VALUE</label>
                                <v-text-field v-model.number="assetForm.manual_amount" type="number" margin-top="8"
                                    prefix="₹" variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" class="mb-4" />
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">INTEREST
                                    RATE</label>
                                <v-text-field v-model.number="assetForm.interest_rate" type="number" suffix="%"
                                    variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" />
                            </div>

                            <div v-else-if="assetForm.type === 'BANK_ACCOUNT'">
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">SELECT
                                    ACCOUNT</label>
                                <v-select v-model="assetForm.linked_account_id" :items="accountOptions"
                                    item-title="label" item-value="value" label="Select Account" variant="outlined"
                                    density="comfortable" hide-details rounded="lg" bg-color="surface">
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
                                    <template v-slot:item="{ props, item }">
                                        <v-list-item v-bind="props" :title="item.raw.label" class="rounded-lg ma-1">
                                            <template v-slot:prepend>
                                                <v-avatar size="28" color="success" variant="tonal" class="mr-2">
                                                    <Building2 :size="14" />
                                                </v-avatar>
                                            </template>
                                        </v-list-item>
                                    </template>
                                    <template v-slot:selection="{ item }">
                                        <div class="d-flex align-center">
                                            <Building2 :size="16" class="mr-2 text-success" />
                                            <span class="text-body-2 font-weight-bold">{{ item.raw.label }}</span>
                                        </div>
                                    </template>
                                </v-select>
                            </div>

                            <div v-else>
                                <label class="text-caption font-weight-bold text-medium-emphasis mb-2 d-block">SELECT
                                    FUND</label>
                                <v-autocomplete v-model="assetForm.holding_id" :items="portfolioOptions"
                                    item-title="label" item-value="value" label="Search Mutual Fund" variant="outlined"
                                    density="comfortable" hide-details rounded="lg" bg-color="surface"
                                    auto-select-first>
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
                                    <template v-slot:item="{ props, item }">
                                        <v-list-item v-bind="props" :title="item.raw.label" class="rounded-lg ma-1">
                                            <template v-slot:prepend>
                                                <v-avatar size="28" color="info" variant="tonal" class="mr-2">
                                                    <TrendingUp :size="14" />
                                                </v-avatar>
                                            </template>
                                        </v-list-item>
                                    </template>
                                </v-autocomplete>
                            </div>
                        </v-form>
                    </v-card-text>

                    <v-card-actions class="px-6 pb-6 pt-2">
                        <v-btn variant="text" @click="showAssetModal = false" height="48" rounded="lg"
                            class="px-6 font-weight-bold text-none text-medium-emphasis">
                            Cancel
                        </v-btn>
                        <v-spacer />
                        <v-btn color="primary" variant="flat" rounded="lg" height="48"
                            class="px-8 font-weight-black text-none elevation-4" @click="handleAssetSubmit">
                            Link Asset
                        </v-btn>
                    </v-card-actions>
                </v-card>
            </v-dialog>

            <!-- Delete confirmation -->
            <v-dialog v-model="showDeleteModal" max-width="400">
                <v-card rounded="xl" class="pa-6 text-center premium-glass-modal">
                    <div class="d-flex justify-center mb-6">
                        <div class="error-glow pa-4 rounded-circle">
                            <Trash2 :size="32" class="text-error" />
                        </div>
                    </div>
                    <h3 class="text-h5 font-weight-black mb-2">Delete Goal?</h3>
                    <p class="text-medium-emphasis mb-8 px-4">This will permanently remove the goal and all its
                        asset links.
                        This
                        action cannot be undone.</p>
                    <div class="d-flex gap-4">
                        <v-btn variant="text" rounded="lg" class="flex-grow-1 font-weight-bold text-none"
                            @click="showDeleteModal = false">Cancel</v-btn>
                        <v-btn color="error" variant="flat" rounded="lg" class="flex-grow-1 font-weight-black text-none"
                            @click="deleteGoal">Delete
                            Permanently</v-btn>
                    </div>
                </v-card>
            </v-dialog>
        </v-container>
    </MainLayout>
</template>

<style scoped>
/* Relies on base.css dashboard-page */

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.gap-3 {
    gap: 12px;
}

/* Relies on base.css premium-glass-card */

.premium-glass-card:not(.border-dashed) {
    border-color: rgba(var(--v-border-color), 0.15) !important;
}

.card-actions-overlay {
    transition: opacity 0.2s ease;
}

.goal-progress-bar :deep(.v-progress-linear__background) {
    opacity: 0.1;
}

.assets-scroll-area {
    max-height: 280px;
    overflow-y: auto;
    padding-right: 4px;
}

.hover-lift {
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.hover-lift:hover {
    background: rgba(var(--v-theme-surface), 1) !important;
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1);
}

.hover-opacity-100 {
    transition: opacity 0.2s ease;
}

.hover-opacity-100:hover {
    opacity: 1 !important;
}

.leading-tight {
    line-height: 1.25;
}

.text-tiny {
    font-size: 0.65rem;
}

.assets-scroll-area {
    max-height: 200px;
    overflow-y: auto;
    padding-right: 4px;
}

.assets-scroll-area::-webkit-scrollbar {
    width: 4px;
}

.assets-scroll-area::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.2);
    border-radius: 10px;
}

.icon-picker-field :deep(input) {
    text-align: center;
    font-size: 1.5rem;
}

.color-dot-premium {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    cursor: pointer;
    position: relative;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    border: 2px solid transparent;
}

.color-dot-premium:hover {
    transform: scale(1.1);
}

.color-dot-premium.active {
    border-color: rgba(var(--v-theme-surface), 1);
    box-shadow: 0 0 0 2px rgb(var(--v-theme-primary));
}

.color-dot-ring {
    position: absolute;
    top: -4px;
    left: -4px;
    right: -4px;
    bottom: -4px;
    border-radius: 50%;
    border: 2px solid rgba(var(--v-theme-primary), 0.3);
    animation: pulse-ring 1.5s infinite;
}

@keyframes pulse-ring {
    0% {
        transform: scale(0.8);
        opacity: 1;
    }

    100% {
        transform: scale(1.2);
        opacity: 0;
    }
}

.centered-input :deep(input) {
    text-align: center;
    font-size: 1.25rem;
}

.premium-glass-modal {
    background: rgba(var(--v-theme-surface), 0.85) !important;
    backdrop-filter: blur(24px) saturate(200%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
}

.color-dot.active {
    border-color: #fff;
    box-shadow: 0 0 0 2px rgba(var(--v-theme-primary), 0.5);
    transform: scale(1.1);
}

.premium-glass-modal {
    background: rgba(var(--v-theme-surface), 0.9) !important;
    backdrop-filter: blur(30px) !important;
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
}

.error-glow {
    background: rgba(var(--v-theme-error), 0.1);
    box-shadow: 0 0 20px rgba(var(--v-theme-error), 0.2);
}

.h-32 {
    height: 32px !important;
}

.letter-spacing-1 {
    letter-spacing: 1px;
}

.group-on-hover-scale {
    transition: transform 0.3s ease;
}

.group:hover .group-on-hover-scale {
    transform: scale(1.1);
}

.border-dashed {
    border-style: dashed !important;
}

.border-primary {
    border-color: rgba(var(--v-theme-primary), 0.5) !important;
}

@media (max-width: 960px) {
    .gap-3 {
        flex-wrap: wrap;
    }
}
</style>
