<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'
import {
    ChevronLeft,
    ChevronRight,
    Plus,
    Pencil,
    RefreshCw,
    Sparkles,
    Target,
    Wallet,
    TrendingUp,
    TrendingDown,
    Ban
} from 'lucide-vue-next'

const { formatAmount } = useCurrency()
const notify = useNotificationStore()
const authStore = useAuthStore()
const router = useRouter()

// State
const budgets = ref<any[]>([])
const categories = ref<any[]>([])
const loading = ref(true)
const loadingInsights = ref(false)
const showModal = ref(false)
const insights = ref<any[]>([])

// Month Selection
const now = new Date()
const selectedDate = ref(new Date(now.getFullYear(), now.getMonth(), 1))

const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
]

const monthYearLabel = computed(() => {
    return `${months[selectedDate.value.getMonth()]} ${selectedDate.value.getFullYear()}`
})

function changeMonth(delta: number) {
    const d = new Date(selectedDate.value)
    d.setMonth(d.getMonth() + delta)
    selectedDate.value = d
    fetchData()
}

function resetToCurrent() {
    selectedDate.value = new Date(now.getFullYear(), now.getMonth(), 1)
    fetchData()
}

const newBudget = ref({
    category: '',
    icon: '',
    amount_limit: null as number | null
})

const activeTab = ref<'expense' | 'income'>('expense')

// Metrics
const overallBudget = ref<any>(null)

// Metrics - categoryBudgets no longer needs to filter ALL
// But wait, the API now returns list WITHOUT OVERALL, so we don't need to filter it out.
const categoryBudgets = computed(() => {
    const list = budgets.value; // backend already filtered OVERALL
    if (activeTab.value === 'income') return list.filter(b => b.income > 0 || b.excluded > 0)
    // Default to expense
    return list.filter(b => b.spent > 0 || b.excluded > 0 || (b.amount_limit && b.amount_limit > 0))
})

const groupedBudgets = computed(() => {
    // 1. Get raw list (backend already excluded OVERALL)
    const rawList = budgets.value

    // 2. Identify Parents and Children
    const parents = rawList.filter(b => !b.parent_id)
    const children = rawList.filter(b => b.parent_id)

    // 3. Map children to parents
    const groups = parents.map(p => {
        // If parent has a category_id, find its children
        const myChildren = p.category_id
            ? children.filter(c => c.parent_id === p.category_id)
            : []

        return {
            parent: p,
            children: myChildren.sort((a, b) => b.spent - a.spent)
        }
    })

    // 4. Tab Filter (Expense vs Income)
    return groups.filter(g => {
        const isIncomeTab = activeTab.value === 'income'
        const isIncomeGroup = g.parent.type === 'income' || g.parent.income > 0 || g.parent.category === 'Salary'

        if (isIncomeTab && !isIncomeGroup) return false
        if (!isIncomeTab && isIncomeGroup) return false
        return true
    }).sort((a, b) => b.parent.percentage - a.parent.percentage)
})

const activeGroups = computed(() => {
    return groupedBudgets.value.filter(g => {
        // Active check: Parent OR Child has > 0 spent, limit set, or excluded amount
        const parentActive = g.parent.spent > 0 || g.parent.excluded > 0 || (g.parent.amount_limit && g.parent.amount_limit > 0)
        const childActive = g.children.some(c => c.spent > 0 || c.excluded > 0 || (c.amount_limit && c.amount_limit > 0))
        return parentActive || childActive
    })
})

const inactiveGroups = computed(() => {
    return groupedBudgets.value.filter(g => {
        // Inactive check: Neither parent nor child is active
        const parentActive = g.parent.spent > 0 || g.parent.excluded > 0 || (g.parent.amount_limit && g.parent.amount_limit > 0)
        const childActive = g.children.some(c => c.spent > 0 || c.excluded > 0 || (c.amount_limit && c.amount_limit > 0))
        return !parentActive && !childActive
    })
})

const totalIncome = computed(() => {
    if (overallBudget.value) return Number(overallBudget.value.income || 0)
    return budgets.value
        .reduce((sum, b) => sum + Number(b.income || 0), 0)
})

const totalSpent = computed(() => {
    if (overallBudget.value) return Number(overallBudget.value.spent)
    return categoryBudgets.value.reduce((sum, b) => sum + Number(b.spent), 0)
})

const budgetStatusPrefix = computed(() => {
    if (!overallBudget.value) return ''
    return overallBudget.value.spent > overallBudget.value.amount_limit ? 'Overspent by' : 'Safe Capacity'
})



const spendingVelocity = computed(() => {
    const d = new Date()
    const isCurrentMonth = selectedDate.value.getMonth() === d.getMonth() &&
        selectedDate.value.getFullYear() === d.getFullYear()

    if (!isCurrentMonth) return { status: 'neutral', diff: 0, monthProgress: 100 }

    const daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
    const dayOfMonth = d.getDate()
    const monthProgress = (dayOfMonth / daysInMonth) * 100

    if (!overallBudget.value || !overallBudget.value.amount_limit) return { status: 'stable', diff: 0, monthProgress }

    const diff = overallBudget.value.percentage - monthProgress
    let status = 'stable'
    if (diff > 15) status = 'aggressive'
    else if (diff > 5) status = 'warning'

    return { status, diff, monthProgress }
})

const categoryOptions = computed(() => {
    return categories.value.map(c => ({
        label: `${c.icon || '🏷️'} ${c.name}`,
        value: c.name
    }))
})

async function fetchData() {
    loading.value = true
    insights.value = [] // Reset insights on month change
    try {
        const year = selectedDate.value.getFullYear()
        const month = selectedDate.value.getMonth() + 1
        const userId = authStore.selectedMemberId || undefined

        const [budgetRes, overviewRes, catRes] = await Promise.all([
            financeApi.getBudgets(year, month, userId),
            financeApi.getBudgetOverview(year, month, userId),
            financeApi.getCategories()
        ])
        budgets.value = budgetRes.data
        overallBudget.value = overviewRes.data
        categories.value = catRes.data
    } catch (e) {
        console.error(e)
        notify.error("Failed to load budgets")
    } finally {
        loading.value = false
    }
}

async function fetchInsights() {
    loadingInsights.value = true
    try {
        const year = selectedDate.value.getFullYear()
        const month = selectedDate.value.getMonth() + 1
        const userId = authStore.selectedMemberId || undefined
        const res = await financeApi.getBudgetsInsights(year, month, userId)
        insights.value = res.data
    } catch (e) {
        notify.error("Failed to generate AI insights")
    } finally {
        loadingInsights.value = false
    }
}

// Watch for member changes
import { watch } from 'vue'
watch(() => authStore.selectedMemberId, () => {
    fetchData()
})

function openSetBudgetModal(isOverall = false) {
    if (isOverall) {
        newBudget.value = { category: 'OVERALL', icon: '🏁', amount_limit: null }
    } else {
        newBudget.value = { category: '', icon: '', amount_limit: null }
    }
    showModal.value = true
}

function editBudget(b: any) {
    newBudget.value = {
        category: b.category,
        icon: b.icon || '🏷️',
        amount_limit: b.amount_limit
    }
    showModal.value = true
}

async function saveBudget() {
    if (!newBudget.value.category || !newBudget.value.amount_limit) return
    try {
        await financeApi.setBudget(newBudget.value)
        notify.success("Budget saved")
        showModal.value = false
        fetchData()
    } catch (e) {
        notify.error("Failed to save budget")
    }
}



onMounted(() => {
    fetchData()
})
</script>

<template>
    <MainLayout>
        <v-container fluid class="dashboard-page pa-6 pa-md-10">
            <!-- Header -->
            <v-row class="mb-10 align-center">
                <v-col cols="12" md="6">
                    <h1 class="text-h4 font-weight-black mb-1">Budgets & Activity</h1>
                    <p class="text-subtitle-1 text-on-surface opacity-70 font-weight-bold">Personal finance intelligence
                    </p>
                </v-col>

                <v-col cols="12" md="6" class="d-flex justify-md-end align-center ga-4">
                    <!-- Month Selector (Refined Vuetify Style) -->
                    <v-sheet rounded="pill" border class="d-flex align-center px-1" height="44">
                        <v-btn icon variant="text" size="small" @click="changeMonth(-1)" color="primary">
                            <ChevronLeft :size="18" />
                        </v-btn>
                        <v-btn variant="text" class="text-none font-weight-black px-2 mx-1" @click="resetToCurrent"
                            min-width="120">
                            {{ monthYearLabel }}
                        </v-btn>
                        <v-btn icon variant="text" size="small" @click="changeMonth(1)" color="primary">
                            <ChevronRight :size="18" />
                        </v-btn>
                    </v-sheet>

                    <v-btn v-if="!overallBudget" color="primary" variant="outlined" rounded="pill"
                        class="text-none px-6 font-weight-black" height="44" @click="openSetBudgetModal(true)">
                        <Plus :size="18" class="mr-2" /> Limit
                    </v-btn>
                </v-col>
            </v-row>

            <v-row v-if="loading" class="mb-8">
                <v-col cols="12">
                    <v-skeleton-loader type="card" height="300" rounded="xl"></v-skeleton-loader>
                </v-col>
            </v-row>

            <v-fade-transition v-else>
                <div v-show="!loading">
                    <!-- Overall Budget Hero Card (Midnight Variant) -->
                    <v-card v-if="overallBudget" class="midnight-premium-card overflow-hidden mb-10 no-hover"
                        rounded="xl" elevation="12">
                        <!-- Animated Mesh Background -->
                        <div class="mesh-blob blob-1"
                            style="background: rgba(255, 255, 255, 0.2); width: 600px; height: 600px; top: -200px; right: -100px;">
                        </div>
                        <div class="mesh-blob blob-2"
                            style="background: rgba(255, 255, 255, 0.1); width: 400px; height: 400px; bottom: -100px; left: -100px;">
                        </div>

                        <div class="pa-8 pa-md-12 relative-pos z-10">
                            <v-row align="center">
                                <v-col cols="12" md="8">
                                    <div class="d-flex align-center mb-6">
                                        <v-chip color="rgba(255,255,255,0.15)" size="small" variant="flat"
                                            class="font-weight-black px-4 text-white" border>
                                            MONTHLY TARGET
                                        </v-chip>
                                    </div>

                                    <div class="d-flex align-baseline ga-3 mb-8">
                                        <span class="text-h2 font-weight-black text-white letter-spacing-tight">{{
                                            formatAmount(overallBudget.spent)
                                        }}</span>
                                        <span class="text-h4 text-white opacity-30">/</span>
                                        <span class="text-h4 font-weight-bold text-white opacity-60">
                                            {{ overallBudget.amount_limit ? formatAmount(overallBudget.amount_limit) :
                                                '∞' }}
                                        </span>
                                    </div>

                                    <div v-if="overallBudget.amount_limit"
                                        class="glass-card pa-4 d-flex align-center ga-4 mb-8"
                                        style="background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.1);">
                                        <v-avatar size="44" :color="spendingVelocity.status === 'aggressive' ? 'error' :
                                            (spendingVelocity.status === 'warning' ? 'warning' : 'success')"
                                            variant="flat" class="elevation-4">
                                            <v-icon size="24" color="white">
                                                {{ spendingVelocity.status === 'aggressive' ? 'mdi-alert-decagram' :
                                                    (spendingVelocity.status === 'warning' ? 'mdi-bell-ring' :
                                                        'mdi-check-decagram')
                                                }}
                                            </v-icon>
                                        </v-avatar>
                                        <div>
                                            <div
                                                class="text-overline font-weight-black text-white opacity-60 line-height-1 mb-1">
                                                Status Analysis</div>
                                            <div class="text-subtitle-1 font-weight-bold text-white">
                                                <template v-if="spendingVelocity.status === 'aggressive'">
                                                    Spending is <strong class="text-red-lighten-2">{{
                                                        spendingVelocity.diff.toFixed(0) }}% ahead</strong> of the
                                                    monthly curve.
                                                </template>
                                                <template v-else-if="spendingVelocity.status === 'warning'">
                                                    Slightly above pace. {{ formatAmount(overallBudget.remaining) }}
                                                    left.
                                                </template>
                                                <template v-else-if="spendingVelocity.status === 'stable'">
                                                    Under control. Spend-aligned with month progress.
                                                </template>
                                                <template v-else>
                                                    Monthly activity snapshot.
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </v-col>

                                <v-col cols="12" md="4" class="text-md-right">
                                    <v-btn v-if="overallBudget.budget_id" icon variant="tonal" rounded="xl" size="large"
                                        @click="editBudget(overallBudget)" color="white">
                                        <Pencil :size="24" />
                                    </v-btn>
                                    <v-btn v-else icon variant="tonal" rounded="xl" size="large"
                                        @click="openSetBudgetModal(true)" color="white">
                                        <Plus :size="24" />
                                    </v-btn>
                                </v-col>
                            </v-row>

                            <div v-if="overallBudget.amount_limit" class="mt-8">
                                <div class="relative-pos mb-4">
                                    <v-progress-linear :model-value="Math.min(overallBudget.percentage, 100)"
                                        height="16" rounded="pill" :color="overallBudget.percentage > 100 ? 'error' :
                                            (overallBudget.percentage > 80 ? 'warning' : 'white')"
                                        class="premium-progress-lg elevation-4">
                                    </v-progress-linear>
                                    <!-- Today marker -->
                                    <div v-if="spendingVelocity.status !== 'neutral'"
                                        class="month-progress-marker d-flex flex-column align-center"
                                        :style="{ left: spendingVelocity.monthProgress + '%' }">
                                        <div class="marker-line-white elevation-4"></div>
                                        <span
                                            class="text-overline font-weight-black mt-2 text-white opacity-60">Today</span>
                                    </div>
                                </div>

                                <div class="d-flex justify-space-between align-center px-2">
                                    <div class="text-h6 font-weight-black text-white">
                                        {{ overallBudget.percentage?.toFixed(1) }}% <span
                                            class="text-subtitle-2 opacity-60">Utilized</span>
                                    </div>
                                    <div class="text-h6 font-weight-black text-white">
                                        {{ formatAmount(Math.abs(overallBudget.remaining)) }}
                                        <span class="text-subtitle-2 opacity-60 ml-1">{{ budgetStatusPrefix }}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </v-card>

                    <!-- AI Insights Section -->
                    <div class="mb-10">
                        <div class="d-flex align-center ga-3 mb-6">
                            <v-avatar color="primary" variant="tonal" size="44">
                                <Sparkles class="text-primary" :size="24" />
                            </v-avatar>
                            <div>
                                <h2 class="text-h6 font-weight-black line-height-1 mb-1">AI Intelligence</h2>
                                <p class="text-caption font-weight-bold opacity-60">Smart financial analysis &
                                    recommendations</p>
                            </div>
                            <v-spacer></v-spacer>
                            <v-btn v-if="insights.length === 0" variant="tonal" color="primary" rounded="pill"
                                size="small" :loading="loadingInsights" @click="fetchInsights"
                                class="text-none px-6 font-weight-bold">
                                Analyze Now
                            </v-btn>
                            <v-btn v-else icon variant="text" size="small" :loading="loadingInsights"
                                @click="fetchInsights" color="primary">
                                <RefreshCw :size="20" />
                            </v-btn>
                        </div>

                        <div v-if="insights.length > 0" class="d-flex flex-column ga-4">
                            <v-card v-for="insight in insights" :key="insight.id" class="premium-glass-card pa-6"
                                rounded="xl" elevation="2"
                                @click="insight.action === 'settings' ? router.push('/settings') : null"
                                :class="{ 'cursor-pointer hover-scale': insight.action }">
                                <div class="d-flex align-start ga-4">
                                    <v-avatar size="48"
                                        :color="insight.type === 'danger' ? 'error' : (insight.type === 'warning' ? 'warning' : 'primary')"
                                        variant="tonal" rounded="lg">
                                        <span class="text-h5">{{ insight.icon || '✨' }}</span>
                                    </v-avatar>
                                    <div class="flex-grow-1">
                                        <div class="d-flex justify-space-between align-start">
                                            <h4 class="text-h6 font-weight-black line-height-1 mb-2">{{ insight.title }}
                                            </h4>
                                            <v-chip size="small" variant="outlined"
                                                :color="insight.type === 'danger' ? 'error' : 'primary'"
                                                class="font-weight-black">
                                                {{ insight.action ? 'Action Required' : 'AI Insight' }}
                                            </v-chip>
                                        </div>
                                        <p class="text-body-1 font-weight-medium opacity-80 line-height-relaxed">{{
                                            insight.content }}</p>
                                    </div>
                                </div>
                            </v-card>
                        </div>
                    </div>

                    <!-- Summary Grid -->
                    <v-row class="mb-10">
                        <v-col cols="12" sm="6" lg="3">
                            <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
                                <div class="d-flex justify-space-between align-center mb-6">
                                    <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Income
                                        In</span>
                                    <v-avatar color="success-lighten-5" rounded="lg" size="48">
                                        <TrendingUp class="text-success" :size="24" />
                                    </v-avatar>
                                </div>
                                <div class="text-h4 font-weight-black text-success">{{ formatAmount(totalIncome) }}
                                </div>
                            </v-card>
                        </v-col>

                        <v-col cols="12" sm="6" lg="3">
                            <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
                                <div class="d-flex justify-space-between align-center mb-6">
                                    <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Total
                                        Outflow</span>
                                    <v-avatar color="rose-lighten-5" rounded="lg" size="48">
                                        <TrendingDown class="text-error" :size="24" />
                                    </v-avatar>
                                </div>
                                <div class="text-h4 font-weight-black text-error">{{ formatAmount(totalSpent) }}</div>
                            </v-card>
                        </v-col>

                        <v-col cols="12" sm="6" lg="3">
                            <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
                                <div class="d-flex justify-space-between align-center mb-6">
                                    <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Net
                                        Balance</span>
                                    <v-avatar color="indigo-lighten-5" rounded="lg" size="48">
                                        <Wallet class="text-indigo" :size="24" />
                                    </v-avatar>
                                </div>
                                <div class="text-h4 font-weight-black"
                                    :class="(totalIncome - totalSpent) < 0 ? 'text-error' : 'text-indigo-darken-1'">
                                    {{ formatAmount(totalIncome - totalSpent) }}
                                </div>
                            </v-card>
                        </v-col>

                        <v-col v-if="overallBudget?.total_excluded || overallBudget?.excluded_income" cols="12" sm="6"
                            lg="3">
                            <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
                                <div class="d-flex justify-space-between align-center mb-4">
                                    <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Excluded
                                        Items</span>
                                    <v-avatar color="slate-lighten-5" rounded="lg" size="48">
                                        <Ban class="text-slate-400" :size="24" />
                                    </v-avatar>
                                </div>
                                <div class="d-flex flex-column gap-2 mt-2">
                                    <div v-if="overallBudget.total_excluded > 0"
                                        class="text-subtitle-2 font-weight-black opacity-60 d-flex justify-space-between align-center">
                                        <span>Outflow</span>
                                        <span class="text-subtitle-1">{{ formatAmount(overallBudget.total_excluded)
                                        }}</span>
                                    </div>
                                    <div v-if="overallBudget.excluded_income > 0"
                                        class="text-subtitle-2 font-weight-black text-success d-flex justify-space-between align-center">
                                        <span>Inflow</span>
                                        <span class="text-subtitle-1">+{{ formatAmount(overallBudget.excluded_income)
                                        }}</span>
                                    </div>
                                </div>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- Category Intelligence -->
                    <div
                        class="mb-8 d-flex flex-column flex-sm-row justify-space-between align-start align-sm-center ga-4">
                        <div>
                            <h2 class="text-h5 font-weight-black mb-1">Category Intelligence</h2>
                            <p class="text-subtitle-2 font-weight-bold opacity-60">Breakdown of your monthly activity
                            </p>
                        </div>

                        <!-- Redesigned Tab Switcher (Segmented Control) -->
                        <div class="glass-card pa-1 border rounded-pill d-flex"
                            style="background: rgba(var(--v-theme-surface), 0.5)">
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-6 letter-spacing-1"
                                :color="activeTab === 'expense' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'expense' ? 'text-disabled' : ''" @click="activeTab = 'expense'">
                                Expense
                            </v-btn>
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-6 letter-spacing-1"
                                :color="activeTab === 'income' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'income' ? 'text-disabled' : ''" @click="activeTab = 'income'">
                                Income
                            </v-btn>
                        </div>
                    </div>

                    <v-row v-if="activeGroups.length > 0">
                        <v-col v-for="group in activeGroups" :key="group.parent.budget_id || group.parent.category"
                            cols="12" sm="6" lg="4">
                            <!-- Changed lg-3 to lg-4 for wider cards -->
                            <v-card class="premium-glass-card h-100 d-flex flex-column" rounded="xl">
                                <div class="pa-6 flex-grow-1">
                                    <!-- Card Header -->
                                    <div class="d-flex justify-space-between align-start mb-6">
                                        <div class="d-flex align-center ga-3">
                                            <v-avatar
                                                :color="group.parent.color ? group.parent.color + '15' : (activeTab === 'expense' ? 'rose-lighten-5' : 'emerald-lighten-5')"
                                                rounded="lg" size="52" border class="elevation-2">
                                                <span class="text-h4">{{ group.parent.icon || '🏷️' }}</span>
                                            </v-avatar>
                                            <div>
                                                <span class="text-h6 font-weight-black line-height-1 mb-1 d-block">{{
                                                    group.parent.category
                                                    }}</span>
                                                <div class="d-flex gap-2">
                                                    <v-chip v-if="group.children.length > 0" size="x-small"
                                                        variant="tonal" color="primary" class="font-weight-bold">
                                                        {{ group.children.length }} Sub-categories
                                                    </v-chip>
                                                    <v-chip v-if="group.parent.percentage > 100" color="error"
                                                        size="x-small" variant="flat" class="font-weight-black">Over
                                                        Limit</v-chip>
                                                </div>
                                            </div>
                                        </div>
                                        <v-menu offset="8">
                                            <template v-slot:activator="{ props }">
                                                <v-btn icon variant="text" size="small" v-bind="props"
                                                    color="slate-400">
                                                    <v-icon>mdi-dots-vertical</v-icon>
                                                </v-btn>
                                            </template>
                                            <v-list density="compact" rounded="lg" class="py-1">
                                                <v-list-item @click="editBudget(group.parent)">
                                                    <template v-slot:prepend>
                                                        <Pencil :size="14" class="mr-3" />
                                                    </template>
                                                    <v-list-item-title class="font-weight-bold">Edit
                                                        Parent</v-list-item-title>
                                                </v-list-item>
                                            </v-list>
                                        </v-menu>
                                    </div>

                                    <!-- Main Values (Parent Rollup) -->
                                    <div class="d-flex flex-column gap-3 mb-6">
                                        <!-- Spent Metric -->
                                        <div class="inset-glass-metric d-flex align-center gap-3 pa-4 border"
                                            style="border-left: 4px solid #F43F5E !important;">
                                            <v-avatar size="36" color="rose-lighten-5" rounded="lg">
                                                <TrendingDown class="text-error" :size="18" />
                                            </v-avatar>
                                            <div>
                                                <div
                                                    class="text-overline font-weight-black opacity-60 line-height-1 mb-1">
                                                    Total Spent</div>
                                                <div class="text-h6 font-weight-black">
                                                    {{ group.parent.spent > 0 ? formatAmount(group.parent.spent) : '₹0'
                                                    }}
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Parent Progress -->
                                    <div v-if="group.parent.amount_limit" class="mb-6">
                                        <v-progress-linear :model-value="Math.min(group.parent.percentage, 100)"
                                            height="8" rounded="pill"
                                            :color="group.parent.percentage > 100 ? 'error' : (group.parent.percentage > 80 ? 'warning' : 'primary')"
                                            class="mb-3 elevation-1"></v-progress-linear>
                                        <div class="d-flex justify-space-between text-caption font-weight-black opacity-50"
                                            :class="{ 'text-error opacity-100': group.parent.percentage > 100 }">
                                            <span>{{ group.parent.percentage.toFixed(0) }}% OF LIMIT</span>
                                            <span>{{ formatAmount(group.parent.amount_limit) }}</span>
                                        </div>
                                    </div>
                                    <div v-else class="text-center pa-2 mb-4">
                                        <v-btn variant="tonal" size="small" color="primary" rounded="pill"
                                            @click="editBudget(group.parent)" class="text-none font-weight-black px-6">
                                            Set Parent Limit
                                        </v-btn>
                                    </div>

                                    <!-- Sub-categories List (Accordion style) -->
                                    <v-expansion-panels v-if="group.children.length > 0" variant="accordion"
                                        class="premium-accordion">
                                        <v-expansion-panel elevation="0" bg-color="transparent">
                                            <v-expansion-panel-title class="px-0 py-2 min-h-0"
                                                collapse-icon="mdi-chevron-up" expand-icon="mdi-chevron-down">
                                                <span class="text-caption font-weight-bold opacity-70">
                                                    Breakdown ({{ group.children.length }})
                                                </span>
                                            </v-expansion-panel-title>
                                            <v-expansion-panel-text class="pa-0">
                                                <div class="d-flex flex-column gap-2 mt-2">
                                                    <div v-for="child in group.children" :key="child.category"
                                                        class="glass-card pa-2 border-thin">
                                                        <div class="d-flex justify-space-between align-center mb-1">
                                                            <div class="d-flex align-center gap-2">
                                                                <span
                                                                    class="text-caption font-weight-black text-no-wrap text-truncate"
                                                                    style="max-width: 120px;">
                                                                    {{ child.icon }} {{ child.category }}
                                                                </span>
                                                            </div>
                                                            <span class="text-caption font-weight-bold">{{
                                                                formatAmount(child.spent)
                                                                }}</span>
                                                        </div>
                                                        <div v-if="child.amount_limit">
                                                            <v-progress-linear
                                                                :model-value="Math.min(child.percentage, 100)"
                                                                height="3" rounded="pill"
                                                                :color="child.percentage > 100 ? 'error' : 'primary'"
                                                                class="mb-1"></v-progress-linear>
                                                            <div
                                                                class="d-flex justify-space-between text-caption font-weight-medium opacity-60 line-height-1">
                                                                <span style="font-size: 10px;">{{
                                                                    child.percentage.toFixed(0) }}%</span>
                                                                <span style="font-size: 10px;">{{
                                                                    formatAmount(child.amount_limit) }}</span>
                                                            </div>
                                                        </div>
                                                        <div v-else class="d-flex justify-end">
                                                            <v-btn size="x-small" variant="text" color="primary"
                                                                @click="editBudget(child)" class="px-0 text-none"
                                                                style="height: 20px;">
                                                                Set Limit
                                                            </v-btn>
                                                        </div>
                                                    </div>
                                                </div>
                                            </v-expansion-panel-text>
                                        </v-expansion-panel>
                                    </v-expansion-panels>
                                </div>

                                <!-- Subtle background icon -->
                                <v-icon class="card-bg-icon-standard">mdi-chart-donut</v-icon>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- Inactive Groups Section -->
                    <div v-if="inactiveGroups.length > 0" class="mt-8">
                        <div class="d-flex align-center gap-3 mb-4">
                            <v-icon color="slate-400">mdi-sleep</v-icon>
                            <h3 class="text-h6 font-weight-bold opacity-60">Inactive Categories</h3>
                        </div>
                        <v-row>
                            <v-col v-for="group in inactiveGroups"
                                :key="group.parent.budget_id || group.parent.category" cols="12" sm="6" lg="4">
                                <v-card class="premium-glass-card h-100 d-flex flex-column opacity-70" rounded="xl"
                                    style="background: rgba(var(--v-theme-surface), 0.3) !important">
                                    <div class="pa-6 flex-grow-1">
                                        <div class="d-flex justify-space-between align-start mb-6">
                                            <div class="d-flex align-center gap-3">
                                                <v-avatar color="surface-variant" variant="tonal" rounded="lg" size="44"
                                                    border>
                                                    <span class="text-h5">{{ group.parent.icon || '🏷️' }}</span>
                                                </v-avatar>
                                                <div>
                                                    <span
                                                        class="text-subtitle-1 font-weight-black line-height-1 mb-1 d-block">{{
                                                            group.parent.category
                                                        }}</span>
                                                    <v-chip size="x-small" variant="tonal" class="font-weight-bold">No
                                                        Activity</v-chip>
                                                </div>
                                            </div>
                                            <v-btn icon variant="text" size="small" @click="editBudget(group.parent)"
                                                color="slate-400">
                                                <Pencil :size="16" />
                                            </v-btn>
                                        </div>
                                        <div class="text-center pa-2">
                                            <v-btn variant="tonal" size="small" color="primary" rounded="pill"
                                                @click="editBudget(group.parent)"
                                                class="text-none font-weight-black px-6">
                                                Set Limit
                                            </v-btn>
                                        </div>
                                    </div>
                                </v-card>
                            </v-col>
                        </v-row>
                    </div>

                    <v-row v-if="activeGroups.length === 0 && inactiveGroups.length === 0" class="justify-center py-16">
                        <v-col cols="12" sm="8" md="6" class="text-center">
                            <v-avatar size="100" color="surface-variant" variant="tonal" class="mb-6 elevation-2">
                                <Target :size="48" class="opacity-30" />
                            </v-avatar>
                            <h3 class="text-h5 font-weight-black mb-2">No activity detected</h3>
                            <p class="text-subtitle-1 opacity-60 mb-8 font-weight-medium">Start by setting a budget or
                                recording transactions to see analysis.</p>
                            <v-btn color="primary" rounded="pill" size="large" variant="elevated"
                                class="text-none px-10 elevation-4 btn-primary-glow font-weight-black"
                                @click="openSetBudgetModal(false)">
                                Set Category Budget
                            </v-btn>
                        </v-col>
                    </v-row>
                </div>
            </v-fade-transition>
        </v-container>

        <!-- Budget Modal -->
        <v-dialog v-model="showModal" max-width="500">
            <v-card class="premium-glass-card no-hover" rounded="xl">
                <v-card-title class="pa-6 border-b d-flex align-center">
                    <div class="d-flex align-center gap-3 flex-grow-1">
                        <v-avatar color="primary" variant="tonal" rounded="lg" size="40">
                            <span class="text-h6">{{ newBudget.icon || '🏷️' }}</span>
                        </v-avatar>
                        <div>
                            <div class="text-caption font-weight-bold opacity-60 line-height-1 mb-1">SET BUDGET FOR
                            </div>
                            <div class="text-h6 font-weight-black line-height-1">
                                {{ newBudget.category || 'Select Category' }}
                            </div>
                        </div>
                    </div>
                    <v-btn icon variant="text" size="small" @click="showModal = false" color="slate-400">
                        <v-icon>mdi-close</v-icon>
                    </v-btn>
                </v-card-title>

                <v-card-text class="pa-6">
                    <v-form @submit.prevent="saveBudget">
                        <div v-if="!newBudget.category" class="mb-6">
                            <label class="d-block text-caption font-weight-black mb-2 opacity-60">CATEGORY</label>
                            <v-select v-model="newBudget.category" :items="categoryOptions" item-title="label"
                                item-value="value" variant="outlined" rounded="lg" density="comfortable"
                                placeholder="Choose a category" class="font-weight-bold" @update:model-value="val => {
                                    const cat = categories.find(c => c.name === val)
                                    if (cat) newBudget.icon = cat.icon
                                }"></v-select>
                        </div>

                        <div class="mb-4">
                            <label class="d-block text-subtitle-2 font-weight-black mb-3 opacity-60">MONTHLY BUDGET
                                LIMIT
                                (₹)</label>
                            <v-text-field v-model="newBudget.amount_limit" type="number" variant="outlined" rounded="lg"
                                prefix="₹" placeholder="Enter amount" hide-details required
                                class="font-weight-black text-h6"></v-text-field>
                        </div>

                        <div class="d-flex gap-4 justify-end mt-10">
                            <v-btn variant="text" rounded="pill" class="text-none px-8 font-weight-black"
                                @click="showModal = false">Cancel</v-btn>
                            <v-btn color="primary" rounded="pill"
                                class="text-none px-8 btn-primary-glow font-weight-black" type="submit" size="large">
                                Save Budget
                            </v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>
    </MainLayout>
</template>

<style scoped>
.relative-pos {
    position: relative;
}

.inset-glass-metric {
    background: rgba(var(--v-theme-surface-variant), 0.1);
    backdrop-filter: blur(8px);
    border-radius: 12px;
    transition: all 0.3s ease;
}

.inset-glass-metric:hover {
    background: rgba(var(--v-theme-surface-variant), 0.2);
    transform: translateX(4px);
}

.z-10 {
    z-index: 10;
}

/* .gap-*, .ga-*, .no-scrollbar removed */

.letter-spacing-1 {
    letter-spacing: 0.1em;
}

.letter-spacing-tight {
    letter-spacing: -0.04em;
}

.line-height-1 {
    line-height: 1;
}

.line-height-relaxed {
    line-height: 1.6;
}

.premium-progress-lg :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #fff 0%, #cbd5e1 100%) !important;
}

.month-progress-marker {
    position: absolute;
    top: -6px;
    bottom: -25px;
    width: 2px;
    z-index: 5;
    transition: left 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.marker-line-white {
    height: 28px;
    width: 2px;
    background: white;
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.8);
    position: relative;
}

.marker-line-white::after {
    content: '';
    position: absolute;
    top: -4px;
    left: -3px;
    width: 8px;
    height: 8px;
    background: white;
    border-radius: 50%;
    box-shadow: 0 0 10px white;
}

.card-bg-icon-standard {
    position: absolute;
    bottom: -1.5rem;
    right: -1rem;
    font-size: 8rem;
    opacity: 0.03;
    pointer-events: none;
    line-height: 1;
    transform: rotate(-12deg);
    transition: all 0.5s ease;
}

.premium-glass-card:hover .card-bg-icon-standard {
    transform: rotate(0deg) scale(1.1);
    opacity: 0.06;
}

.snap-x {
    scroll-snap-type: x mandatory;
}

.snap-start {
    scroll-snap-align: start;
}

.hover-lift {
    transition: all 0.3s ease;
}

.hover-lift:hover {
    transform: translateY(-8px);
}

@media (max-width: 600px) {
    .card-bg-icon-standard {
        font-size: 6rem;
    }

    .text-h2 {
        font-size: 2.5rem !important;
    }
}
</style>