<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import PremiumSkeleton from '@/components/common/PremiumSkeleton.vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'
import {
    ChevronLeft,
    ChevronRight,
    Plus,
    Moon,
    Target
} from 'lucide-vue-next'
import CategoryDetailsModal from '@/components/budgets/CategoryDetailsModal.vue'
import BudgetSummaryCards from '@/components/budgets/BudgetSummaryCards.vue'
import { useBudgetStore } from '@/stores/finance/budgets'
import { useFinanceStore } from '@/stores/finance'

// Sub-components
import BudgetHero from '@/components/budgets/BudgetHero.vue'
import BudgetAiInsights from '@/components/budgets/BudgetAiInsights.vue'
import BudgetCategoryCard from '@/components/budgets/BudgetCategoryCard.vue'
import SetBudgetDialog from '@/components/budgets/SetBudgetDialog.vue'

const notify = useNotificationStore()
const authStore = useAuthStore()
const budgetStore = useBudgetStore()
const financeStore = useFinanceStore()

// State - seed from cache
const budgets = computed(() => budgetStore.budgets)
const overallBudget = computed(() => budgetStore.overallBudget)
const categories = computed(() => financeStore.categories)
const loading = ref(budgetStore.budgets.length === 0)
const loadingInsights = ref(false)
const showModal = ref(false)
const insights = computed(() => budgetStore.insights)

// Category Details Modal
const showDetailsModal = ref(false)
const selectedCategoryForDetails = ref<any>(null)
const selectedCategoryBudget = ref<any>(null)

function openCategoryDetails(category: any, budget?: any) {
    selectedCategoryForDetails.value = category
    selectedCategoryBudget.value = budget
    showDetailsModal.value = true
}

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

const alertGroups = computed(() => {
    return groupedBudgets.value.filter(g => g.parent.percentage > 85)
})

const totalIncome = computed(() => {
    if (overallBudget.value) return Number(overallBudget.value.income || 0)
    return budgets.value
        .filter(b => !b.parent_id)
        .reduce((sum, b) => sum + Number(b.income || 0), 0)
})

const totalSpent = computed(() => {
    if (overallBudget.value) return Number(overallBudget.value.spent)
    return budgets.value
        .filter(b => !b.parent_id)
        .reduce((sum, b) => sum + Number(b.spent), 0)
})


async function fetchData() {
    if (budgetStore.budgets.length === 0) loading.value = true
    budgetStore.insights = [] // Reset insights on month change
    try {
        const year = selectedDate.value.getFullYear()
        const month = selectedDate.value.getMonth() + 1
        const userId = authStore.selectedMemberId || undefined

        await Promise.all([
            budgetStore.fetchBudgets(year, month, userId),
            financeStore.fetchCategories()
        ])
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
        await budgetStore.fetchInsights(year, month, userId)
    } catch (e) {
        notify.error("Failed to generate AI insights")
    } finally {
        loadingInsights.value = false
    }
}

// Watch for member changes
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
        <v-container fluid class="page-container dashboard-page">
            <!-- Header -->
            <v-row class="mb-10 align-center">
                <v-col cols="12" md="6">
                    <h1 class="text-h6 font-weight-black mb-1">Budgets & Activity</h1>
                    <p class="text-subtitle-2 text-on-surface opacity-70 font-weight-bold">Personal finance intelligence
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

            <!-- Premium Skeleton Loading State -->
            <div v-if="loading">
                <v-row class="mb-10">
                    <v-col cols="12">
                        <PremiumSkeleton type="hero" height="360" glass />
                    </v-col>
                </v-row>

                <v-row class="mb-10">
                    <v-col v-for="i in 4" :key="`summary-skel-${i}`" cols="12" sm="6" lg="3">
                        <PremiumSkeleton type="stat-card" glass />
                    </v-col>
                </v-row>

                <div class="mb-10">
                    <div class="d-flex align-center ga-3 mb-6">
                        <v-skeleton-loader type="avatar" size="44"></v-skeleton-loader>
                        <v-skeleton-loader type="heading" width="200"></v-skeleton-loader>
                    </div>
                    <v-row>
                        <v-col v-for="i in 3" :key="`cat-skel-${i}`" cols="12" sm="6" lg="4">
                            <PremiumSkeleton type="category-card" glass />
                        </v-col>
                    </v-row>
                </div>
            </div>

            <v-fade-transition v-else>
                <div v-show="!loading">
                    <!-- Overall Budget Hero Card (Midnight Variant) -->
                    <BudgetHero 
                        :overallBudget="overallBudget" 
                        @edit="editBudget" 
                        @set-limit="openSetBudgetModal(false)" 
                    />

                    <!-- AI Insights Section -->
                    <BudgetAiInsights 
                        :insights="insights" 
                        :loading="loadingInsights" 
                        @analyze="fetchInsights" 
                    />

                    <!-- Summary Grid & Alerts -->
                    <BudgetSummaryCards 
                        :totalIncome="totalIncome" 
                        :totalSpent="totalSpent" 
                        :overallBudget="overallBudget" 
                        :alertGroups="alertGroups" 
                        @edit="editBudget" 
                        @open-details="openCategoryDetails" 
                    />

                    <!-- Category Intelligence -->
                    <div
                        class="mb-8 d-flex flex-column flex-sm-row justify-space-between align-start align-sm-center ga-4">
                        <div>
                            <h2 class="text-h6 font-weight-black mb-1">Category Intelligence</h2>
                            <p class="text-subtitle-2 font-weight-bold opacity-60">Breakdown of your monthly activity
                            </p>
                        </div>

                        <!-- Redesigned Tab Switcher (Segmented Control) -->
                        <div class="glass-card pa-1 border rounded-pill d-flex"
                            style="background: rgba(var(--v-theme-surface), 0.5)">
                            <v-btn variant="flat" rounded="pill" height="36"
                                class="text-none font-weight-black px-6 letter-spacing-1"
                                :color="activeTab === 'expense' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'expense' ? 'text-disabled' : ''" @click="activeTab = 'expense'">
                                Expense
                            </v-btn>
                            <v-btn variant="flat" rounded="pill" height="36"
                                class="text-none font-weight-black px-6 letter-spacing-1"
                                :color="activeTab === 'income' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'income' ? 'text-disabled' : ''" @click="activeTab = 'income'">
                                Income
                            </v-btn>
                        </div>
                    </div>

                    <v-row v-if="activeGroups.length > 0">
                        <v-col v-for="group in activeGroups" :key="group.parent.budget_id || group.parent.category"
                            cols="12" sm="6" md="4" lg="3">
                            <BudgetCategoryCard 
                                :group="group" 
                                :activeTab="activeTab" 
                                @edit="editBudget" 
                                @open-details="openCategoryDetails" 
                            />
                        </v-col>
                    </v-row>

                    <!-- Inactive Groups Section -->
                    <div v-if="inactiveGroups.length > 0" class="mt-8">
                        <div class="d-flex align-center ga-3 mb-4">
                            <Moon color="rgb(var(--v-theme-primary))" opacity="0.6" :size="20" />
                            <h3 class="text-h6 font-weight-black opacity-60">Inactive Categories</h3>
                        </div>
                        <v-row>
                            <v-col v-for="group in inactiveGroups" :key="group.parent.budget_id || group.parent.category" cols="12" sm="6" lg="4">
                                <BudgetCategoryCard 
                                    :group="group" 
                                    :activeTab="activeTab" 
                                    isInactive 
                                    @edit="editBudget" 
                                />
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
        <SetBudgetDialog 
            v-model="showModal" 
            :newBudget="newBudget" 
            :categories="categories" 
            @save="saveBudget" 
            @close="showModal = false" 
        />
        <CategoryDetailsModal v-if="showDetailsModal" :isOpen="showDetailsModal" :category="selectedCategoryForDetails"
            :budget="selectedCategoryBudget" :month="selectedDate.getMonth() + 1" :year="selectedDate.getFullYear()"
            @close="showDetailsModal = false" />
    </MainLayout>
</template>

<style scoped>
.pulse-glow {
    animation: pulse-red 2s infinite;
}

@keyframes pulse-red {
    0% {
        box-shadow: 0 0 0 0 rgba(var(--v-theme-error), 0.4);
    }

    70% {
        box-shadow: 0 0 0 10px rgba(var(--v-theme-error), 0);
    }

    100% {
        box-shadow: 0 0 0 0 rgba(var(--v-theme-error), 0);
    }
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(12px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-primary-glow {
    box-shadow: 0 4px 15px rgba(var(--v-theme-primary), 0.3);
}

.hover-scale {
    transition: transform 0.2s;
}

.hover-scale:hover {
    transform: translateY(-2px);
}
</style>