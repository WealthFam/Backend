<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page py-6">
            <!-- Header section with greeting and premium vibe -->
            <v-row class="mb-4 align-center">
                <v-col cols="12">
                    <div class="d-flex align-center justify-space-between">
                        <div>
                            <h1 class="text-h4 font-weight-black mb-1 d-flex align-center">
                                <span class="mr-3">{{ greetingEmoji }}</span>
                                {{ getGreeting() }}, {{ (auth.user?.full_name || auth.user?.email || 'User').split(' ')[0] }}
                            </h1>
                            <p class="text-subtitle-1 text-on-surface opacity-60 font-weight-medium">
                                Here's what's happening with your family wealth today.
                            </p>
                        </div>
                        <v-btn variant="tonal" rounded="pill" color="primary" class="font-weight-black px-6" @click="fetchAllData()">
                            <template v-slot:prepend>
                                <RefreshCw :size="18" :class="{ 'spin-sync': loading }" />
                            </template>
                            Refresh
                        </v-btn>
                    </div>
                </v-col>
            </v-row>

            <!-- Premium Loading State -->
            <div v-if="loading && !metrics">
                <v-row>
                    <v-col v-for="i in 4" :key="`skel-${i}`" cols="12" sm="6" lg="3">
                        <PremiumSkeleton type="stat-card" glass />
                    </v-col>
                    <v-col cols="12">
                        <PremiumSkeleton type="hero" height="200" glass />
                    </v-col>
                </v-row>
            </div>

            <v-row v-else>
                <!-- TOP ROW: High Impact Metrics -->
                <v-col cols="12" sm="6" lg="3">
                    <v-hover v-slot="{ isHovering, props }">
                        <v-card v-bind="props" class="premium-glass-card metric-card pa-6" :class="{ 'raised': isHovering }" rounded="xl" @click="router.push('/')">
                            <div class="d-flex justify-space-between mb-4">
                                <v-avatar color="primary" variant="tonal" rounded="lg" size="48">
                                    <Landmark :size="24" />
                                </v-avatar>
                                <Sparkline v-if="netWorthTrend.length > 1" :data="netWorthTrend" color="#6366f1" :height="40" width="80" fill />
                            </div>
                            <div class="text-overline opacity-60 font-weight-black">Total Net Worth</div>
                            <div class="text-h4 font-weight-black text-primary mb-1">{{ formatAmount(netWorth) }}</div>
                            <div class="d-flex align-center text-caption font-weight-bold" :class="netWorthChange >= 0 ? 'text-success' : 'text-error'">
                                <TrendingUp v-if="netWorthChange >= 0" :size="14" class="mr-1" />
                                <TrendingDown v-else :size="14" class="mr-1" />
                                {{ Math.abs(netWorthChange).toFixed(1) }}% from last month
                            </div>
                        </v-card>
                    </v-hover>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-hover v-slot="{ isHovering, props }">
                        <v-card v-bind="props" class="premium-glass-card metric-card pa-6" :class="{ 'raised': isHovering }" rounded="xl" @click="router.push('/transactions')">
                            <div class="d-flex justify-space-between mb-4">
                                <v-avatar color="error" variant="tonal" rounded="lg" size="48">
                                    <Wallet :size="24" />
                                </v-avatar>
                                <Sparkline v-if="spendingTrend.length > 1" :data="spendingTrend" color="#e11d48" :height="40" width="80" fill />
                            </div>
                            <div class="text-overline opacity-60 font-weight-black">Monthly Spending</div>
                            <div class="text-h4 font-weight-black text-error mb-1">{{ formatAmount(metrics.monthly_spending) }}</div>
                            <div class="text-caption font-weight-bold opacity-50">Budget: {{ formatAmount(metrics.budget_health?.limit || 0) }}</div>
                        </v-card>
                    </v-hover>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-hover v-slot="{ isHovering, props }">
                        <v-card v-bind="props" class="premium-glass-card metric-card pa-6" :class="{ 'raised': isHovering }" rounded="xl" @click="router.push('/mutual-funds')">
                            <div class="d-flex justify-space-between mb-4">
                                <v-avatar color="success" variant="tonal" rounded="lg" size="48">
                                    <Sparkles :size="24" />
                                </v-avatar>
                                <v-chip size="small" color="success" variant="flat" class="font-weight-black">
                                    {{ (mfPortfolio.xirr || 0).toFixed(1) }}% XIRR
                                </v-chip>
                            </div>
                            <div class="text-overline opacity-60 font-weight-black">Mutual Funds</div>
                            <div class="text-h4 font-weight-black text-success mb-1">{{ formatAmount(mfPortfolio.current) }}</div>
                            <div class="text-caption font-weight-bold text-success">
                                Profit: {{ formatAmount(mfPortfolio.pl) }} ({{ mfPortfolio.plPercent.toFixed(1) }}%)
                            </div>
                        </v-card>
                    </v-hover>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-hover v-slot="{ isHovering, props }">
                        <v-card v-bind="props" class="premium-glass-card metric-card pa-6" :class="{ 'raised': isHovering }" rounded="xl" @click="router.push('/budgets')">
                            <div class="d-flex justify-space-between mb-4">
                                <v-avatar color="warning" variant="tonal" rounded="lg" size="48">
                                    <PieChart :size="24" />
                                </v-avatar>
                                <div class="text-h4 font-weight-black" :class="metrics.budget_health?.percentage > 90 ? 'text-error' : 'text-warning'">
                                    {{ (metrics.budget_health?.percentage || 0).toFixed(0) }}%
                                </div>
                            </div>
                            <div class="text-overline opacity-60 font-weight-black">Budget Health</div>
                            <v-progress-linear 
                                :model-value="Math.min(metrics.budget_health?.percentage || 0, 100)" 
                                height="10" 
                                rounded="pill" 
                                class="mt-4 budget-progress-premium"
                                :class="metrics.budget_health?.percentage > 90 ? 'health-danger' : 'health-warning'"
                            ></v-progress-linear>
                            <div class="text-caption font-weight-bold opacity-50 mt-1">Remaining: {{ formatAmount(Math.max(0, (metrics.budget_health?.limit || 0) - (metrics.budget_health?.spent || 0))) }}</div>
                        </v-card>
                    </v-hover>
                </v-col>

                <!-- MIDDLE ROW: Wealth Compass & AI Intelligence -->
                <v-col cols="12" lg="7">
                    <WealthCompass :metrics="metrics" :portfolio="mfPortfolio" class="h-100" />
                </v-col>

                <v-col cols="12" lg="5">
                    <v-card class="premium-glass-card intelligence-card pa-6 h-100" rounded="xl" elevation="1">
                        <div class="d-flex justify-space-between align-center mb-6">
                            <div class="d-flex align-center">
                                <h2 class="text-h6 font-weight-black d-flex align-center mb-0">
                                    <Zap :size="20" class="text-primary mr-2" />
                                    AI Intelligence
                                </h2>
                                <v-chip v-if="isAiCached" size="small" color="warning" class="ml-3 font-weight-bold" variant="tonal">
                                    Cached
                                </v-chip>
                            </div>
                            <div class="d-flex align-center">
                                <v-btn v-if="aiInsights" icon variant="text" size="small" color="primary" @click="forceRefreshAi" :loading="refreshingAi">
                                    <RefreshCw :size="16" />
                                </v-btn>
                                <v-icon v-if="!aiInsights" class="rotate-anim opacity-40">Loader2</v-icon>
                            </div>
                        </div>
                        
                        <div v-if="aiInsights" class="ai-content">
                            <div v-for="(insight, idx) in formattedInsights" :key="idx" class="insight-pill mb-4 pa-4 border rounded-lg">
                                <div class="d-flex align-center mb-1">
                                    <span class="mr-2 text-h6">{{ insight.icon }}</span>
                                    <span class="text-subtitle-2 font-weight-black">{{ insight.title }}</span>
                                </div>
                                <p class="text-caption font-weight-medium opacity-70 mb-0">
                                    {{ insight.content }}
                                </p>
                            </div>
                        </div>
                        <div v-else class="text-center py-12 opacity-40">
                            <p class="text-caption font-weight-black">Analyzing your financial DNA...</p>
                        </div>

                        <!-- Gradient background glow for AI -->
                        <div class="ai-glow"></div>
                    </v-card>
                </v-col>

                <!-- ROW 3: Budget Pulse & Activity -->
                <v-col cols="12" lg="4">
                    <ActivityPulse />
                </v-col>

                <v-col cols="12" lg="8">
                    <v-card class="premium-glass-card pa-6 h-100" rounded="xl" elevation="1">
                        <div class="d-flex justify-space-between align-center mb-6">
                            <h2 class="text-h6 font-weight-black d-flex align-center">
                                <Activity :size="20" class="text-primary mr-2" />
                                Recent Activity
                            </h2>
                            <v-btn variant="text" size="small" color="primary" @click="router.push('/transactions')" class="text-none font-weight-black">See More</v-btn>
                        </div>
                        <v-list class="pa-0 bg-transparent">
                            <v-list-item v-for="txn in metrics.recent_transactions.slice(0, 5)" :key="txn.id" class="rounded-xl px-4 py-3 mb-2 glass-item border">
                                <template v-slot:prepend>
                                    <v-avatar size="44" :color="getCategoryDetails(txn.category).color + '15'" class="mr-3">
                                        <span class="text-h6">{{ getCategoryDetails(txn.category).icon }}</span>
                                    </v-avatar>
                                </template>
                                <v-list-item-title class="font-weight-bold text-subtitle-1">{{ txn.description }}</v-list-item-title>
                                <v-list-item-subtitle class="text-caption font-weight-medium opacity-60">
                                    {{ formatDate(txn.date).day }} • {{ txn.account_owner_name || 'Personal' }}
                                </v-list-item-subtitle>
                                <template v-slot:append>
                                    <div class="text-subtitle-1 font-weight-black" :class="txn.amount > 0 ? 'text-success' : 'opacity-80'">
                                        {{ txn.amount > 0 ? '+' : '' }}{{ formatAmount(Math.abs(txn.amount)) }}
                                    </div>
                                </template>
                            </v-list-item>
                        </v-list>
                    </v-card>
                </v-col>

                <!-- ROW 4: Bills & Credit Outlook -->
                <v-col cols="12" lg="5">
                    <v-card class="premium-glass-card pa-6 h-100" rounded="xl" elevation="1">
                        <h2 class="text-h6 font-weight-black d-flex align-center mb-6">
                            <CalendarClock :size="20" class="text-primary mr-2" />
                            Upcoming Bills
                        </h2>
                        <div v-if="upcomingBills.length > 0">
                            <v-list class="pa-0 bg-transparent">
                                <v-list-item v-for="bill in upcomingBills" :key="bill.id" class="rounded-xl px-4 py-3 mb-2 glass-item border">
                                    <template v-slot:prepend>
                                        <v-avatar size="40" color="surface-variant" variant="tonal" class="mr-3">
                                            <span>{{ getCategoryDetails(bill.category).icon }}</span>
                                        </v-avatar>
                                    </template>
                                    <v-list-item-title class="font-weight-bold">{{ bill.description }}</v-list-item-title>
                                    <v-list-item-subtitle class="text-caption font-weight-bold text-error">Due {{ formatDate(bill.next_date).day }}</v-list-item-subtitle>
                                    <template v-slot:append>
                                        <div class="text-subtitle-1 font-weight-black">{{ formatAmount(bill.amount) }}</div>
                                    </template>
                                </v-list-item>
                            </v-list>
                        </div>
                        <div v-else class="text-center py-10 opacity-40">
                            <div class="text-h3 mb-2">📅</div>
                            <p class="text-caption font-weight-black">No dues today. You're clear!</p>
                        </div>
                    </v-card>
                </v-col>

                <v-col cols="12" lg="7">
                    <v-card class="premium-glass-card pa-6 h-100 overflow-visible" rounded="xl" elevation="1">
                        <div class="d-flex justify-space-between align-center mb-6">
                            <h2 class="text-h6 font-weight-black d-flex align-center">
                                <CreditCard :size="20" class="text-primary mr-2" />
                                Credit Outlook
                            </h2>
                            <div class="text-right">
                                <div class="text-caption opacity-60 font-weight-black">UTILIZATION</div>
                                <div class="text-h6 font-weight-black text-primary">{{ creditSummary.utilization.toFixed(0) }}%</div>
                            </div>
                        </div>
                        
                        <v-row class="ga-4 pt-1">
                            <v-col v-for="card in sortedCredit.slice(0, 3)" :key="card.id" cols="12" class="py-2">
                                <div class="d-flex align-center justify-space-between">
                                    <div class="d-flex align-center">
                                        <div class="card-miniature mr-4" :style="{ background: getBankBrand(card.name).gradient }">
                                            <div class="chip"></div>
                                        </div>
                                        <div>
                                            <div class="text-subtitle-2 font-weight-black">{{ card.name }}</div>
                                            <div class="text-tiny font-weight-bold opacity-60">Due in {{ card.days_until_due }} days</div>
                                        </div>
                                    </div>
                                    <div class="text-right">
                                        <div class="text-subtitle-2 font-weight-black">{{ formatAmount(card.statement_balance) }}</div>
                                        <v-progress-linear 
                                            :model-value="card.utilization" 
                                            height="4" 
                                            rounded 
                                            class="mt-1"
                                            :color="card.utilization > 70 ? 'error' : 'primary'"
                                            style="width: 80px;"
                                        ></v-progress-linear>
                                    </div>
                                </div>
                            </v-col>
                        </v-row>
                    </v-card>
                </v-col>
            </v-row>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useRouter } from 'vue-router'
import { useTransactionHelpers } from '@/composables/useTransactionHelpers'
import { useDashboardHelpers } from '@/composables/useDashboardHelpers'
import { useAuthStore } from '@/stores/auth'
import { useCurrency } from '@/composables/useCurrency'
import PremiumSkeleton from '@/components/common/PremiumSkeleton.vue'
import Sparkline from '@/components/Sparkline.vue'
import WealthCompass from '@/components/dashboard/WealthCompass.vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useBudgetStore } from '@/stores/finance/budgets'
import { useExpenseGroupStore } from '@/stores/expenseGroups'
import { useFinanceStore } from '@/stores/finance'
import ActivityPulse from '@/components/dashboard/ActivityPulse.vue'
import {
    Activity,
    Landmark,
    Wallet,
    PieChart,
    Sparkles,
    CalendarClock,
    CreditCard,
    TrendingUp,
    TrendingDown,
    RefreshCw,
    Zap
} from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const dashboardStore = useDashboardStore()
const financeStore = useFinanceStore()
const budgetStore = useBudgetStore()
const expenseGroupStore = useExpenseGroupStore()
const { formatAmount } = useCurrency()

// --- State & Computed ---
const metrics = computed(() => dashboardStore.metrics)
const mfPortfolio = computed(() => dashboardStore.mfPortfolio || { current: 0, invested: 0, pl: 0, plPercent: 0, xirr: 0, loading: true })
const netWorthTrend = computed(() => dashboardStore.netWorthTrend || [])
const spendingTrend = computed(() => dashboardStore.spendingTrend || [])
const aiInsights = computed(() => dashboardStore.aiInsights)
const loading = computed(() => dashboardStore.loading)

const accounts = computed(() => financeStore.accounts)
const categories = computed(() => financeStore.categories)
const expenseGroups = computed(() => expenseGroupStore.groups)
const recurringTransactions = ref<any[]>([])

const netWorth = computed(() => {
    const liquid = (metrics.value?.breakdown?.bank_balance || 0) + (metrics.value?.breakdown?.cash_balance || 0)
    const investment = mfPortfolio.value?.current || 0
    const debt = metrics.value?.breakdown?.credit_debt || 0
    return liquid + investment - debt
})

const netWorthChange = computed(() => {
    if (netWorthTrend.value.length < 2) return 0
    const current = netWorthTrend.value[netWorthTrend.value.length - 1]
    const previous = netWorthTrend.value[netWorthTrend.value.length - 2]
    if (previous === 0) return 0
    return ((current - previous) / previous) * 100
})

const formattedInsights = computed(() => {
    if (!aiInsights.value) return []
    // If its a string (classic bullet points), try to parse or just wrap
    if (typeof aiInsights.value === 'string') {
        return aiInsights.value.split('\n').filter((l: string) => l.trim()).map((l: string) => {
            const clean = l.replace(/^[-*•]\s+/, '')
            return { icon: '✨', title: 'Observation', content: clean }
        }).slice(0, 3)
    }
    // If its structured (array from backend)
    if (Array.isArray(aiInsights.value)) return aiInsights.value.slice(0, 3)
    return []
})

const isAiCached = computed(() => {
    if (Array.isArray(aiInsights.value)) {
        return aiInsights.value.some((i: any) => i.is_cached)
    }
    return false
})

const refreshingAi = ref(false)
async function forceRefreshAi() {
    refreshingAi.value = true
    await dashboardStore.fetchAiInsights(true)
    refreshingAi.value = false
}

const creditSummary = computed(() => {
    const limit = metrics.value?.breakdown?.total_credit_limit || 0
    const debt = metrics.value?.breakdown?.credit_debt || 0
    const utilization = limit > 0 ? (debt / limit) * 100 : 0
    return { utilization, debt }
})

const sortedCredit = computed(() => {
    return [...(metrics.value?.credit_intelligence || [])].sort((a, b) => (a.days_until_due || 999) - (b.days_until_due || 999))
})

const upcomingBills = computed(() => {
    return recurringTransactions.value.filter(t => t.status === 'ACTIVE').slice(0, 3)
})

// --- Helpers ---
const { formatDate, getCategoryDisplay } = useTransactionHelpers(accounts, categories, expenseGroups)
const { getGreeting, getBankBrand } = useDashboardHelpers()

function getCategoryDetails(name: string) {
    const display = getCategoryDisplay(name)
    return { icon: display.icon, color: display.color }
}

const greetingEmoji = computed(() => {
    const hour = new Date().getHours()
    if (hour < 12) return '🌅'
    if (hour < 18) return '☀️'
    return '🌙'
})

// --- Actions ---
async function fetchAllData() {
    dashboardStore.fetchDashboardData()
    financeApi.getRecurringTransactions()
        .then(res => { recurringTransactions.value = res.data })
}

async function fetchMetadata() {
    const userId = auth.selectedMemberId || undefined
    await Promise.all([
        financeStore.fetchCategories(),
        budgetStore.fetchBudgets(new Date().getFullYear(), new Date().getMonth() + 1, userId),
        financeStore.fetchAccounts(),
        expenseGroupStore.fetchGroups()
    ])
}

onMounted(async () => {
    await fetchMetadata()
    fetchAllData()
})

watch(() => auth.selectedMemberId, async () => {
    await fetchMetadata()
    fetchAllData()
})
</script>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(12px) saturate(150%);
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.metric-card.raised {
    transform: translateY(-8px) scale(1.02);
    background: rgba(var(--v-theme-surface), 0.8) !important;
    border-color: rgba(var(--v-theme-primary), 0.2) !important;
    box-shadow: 0 15px 30px -10px rgba(var(--v-theme-primary), 0.15) !important;
}

.intelligence-card {
    position: relative;
    overflow: hidden;
    background: linear-gradient(135deg, rgba(var(--v-theme-surface), 0.8) 0%, rgba(var(--v-theme-primary), 0.05) 100%) !important;
}

.ai-glow {
    position: absolute;
    top: -50px;
    right: -50px;
    width: 200px;
    height: 200px;
    background: radial-gradient(circle, rgba(var(--v-theme-primary), 0.1) 0%, transparent 70%);
    z-index: 0;
    pointer-events: none;
}

.insight-pill {
    background: rgba(var(--v-theme-on-surface), 0.03);
    border-color: rgba(var(--v-border-color), 0.05) !important;
    transition: all 0.2s;
}

.insight-pill:hover {
    background: rgba(var(--v-theme-primary), 0.05);
}

.glass-item {
    background: rgba(var(--v-theme-on-surface), 0.02);
    border-color: rgba(var(--v-border-color), 0.03) !important;
}

.glass-item:hover {
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.card-miniature {
    width: 40px;
    height: 26px;
    border-radius: 4px;
    position: relative;
    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.card-miniature .chip {
    position: absolute;
    width: 8px;
    height: 6px;
    background: rgba(255,255,255,0.4);
    border-radius: 2px;
    top: 6px;
    left: 4px;
}

.rotate-anim {
    animation: rotate 2s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.spin-sync {
    animation: rotate 1.5s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.letter-spacing-1 {
    letter-spacing: 0.05em;
}

.uppercase {
    text-transform: uppercase;
}

.budget-progress-premium :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, rgb(var(--v-theme-primary)) 0%, #a5b4fc 100%) !important;
}

.health-danger :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #ef4444 0%, #f87171 100%) !important;
}
</style>
