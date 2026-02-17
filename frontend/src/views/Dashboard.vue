<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Header -->
            <v-row class="mb-8 align-center">
                <v-col cols="12">
                    <h1 class="text-h6 font-weight-black mb-1 d-flex align-center">
                        <span class="mr-3">{{ greetingEmoji }}</span>
                        {{ getGreeting() }}, {{ (auth.user?.full_name || auth.user?.email || 'User').split(' ')[0] }}
                    </h1>
                    <p class="text-subtitle-2 text-on-surface opacity-70 font-weight-bold">
                        Your family's financial state at a glance.
                    </p>
                </v-col>
            </v-row>

            <!-- Premium Loading State -->
            <div v-if="loading">
                <v-row>
                    <!-- Metric Cards Skel -->
                    <v-col v-for="i in 4" :key="`skel-${i}`" cols="12" sm="6" lg="3">
                        <PremiumSkeleton type="stat-card" glass />
                    </v-col>

                    <!-- Budget Pulse Skel -->
                    <v-col cols="12" class="mt-4">
                        <div class="d-flex align-center ga-3 mb-6">
                            <v-skeleton-loader type="avatar" size="32"></v-skeleton-loader>
                            <v-skeleton-loader type="heading" width="200"></v-skeleton-loader>
                        </div>
                        <v-row>
                            <v-col v-for="i in 4" :key="`pulse-skel-${i}`" cols="12" sm="6" md="4" lg="3">
                                <PremiumSkeleton type="stat-card" height="100" glass />
                            </v-col>
                        </v-row>
                    </v-col>

                    <!-- Activity & Bills Skel -->
                    <v-col cols="12" lg="7">
                        <PremiumSkeleton type="insight-card" height="400" glass />
                    </v-col>
                    <v-col cols="12" lg="5">
                        <PremiumSkeleton type="insight-card" height="400" glass />
                    </v-col>

                    <!-- Credit Intelligence Skel -->
                    <v-col cols="12">
                        <PremiumSkeleton type="hero" height="300" glass />
                    </v-col>
                </v-row>
            </div>

            <v-row v-else>
                <!-- ROW 1: Metric Cards -->
                <v-col cols="12" sm="6" lg="3">
                    <v-card class="premium-glass-card pa-6 d-flex flex-column justify-space-between" height="170"
                        rounded="xl" elevation="2" @click="router.push('/')">
                        <div class="d-flex justify-space-between align-start">
                            <v-avatar color="primary" variant="tonal" rounded="lg" size="48">
                                <Landmark :size="24" />
                            </v-avatar>
                            <Sparkline v-if="netWorthTrend.length > 1" :data="netWorthTrend" color="#6366f1"
                                :height="32" width="70" />
                        </div>
                        <div>
                            <div class="text-overline opacity-60 font-weight-black mb-1">Total Net Worth</div>
                            <div class="text-h5 font-weight-black text-primary">{{ formatAmount(netWorth) }}
                            </div>
                        </div>
                    </v-card>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-card class="premium-glass-card pa-6 d-flex flex-column justify-space-between" height="170"
                        rounded="xl" elevation="2" @click="router.push('/transactions')">
                        <div class="d-flex justify-space-between align-start">
                            <v-avatar color="error" variant="tonal" rounded="lg" size="48">
                                <Wallet :size="24" />
                            </v-avatar>
                            <Sparkline v-if="spendingTrend.length > 1" :data="spendingTrend" color="#e11d48"
                                :height="32" width="70" />
                        </div>
                        <div>
                            <div class="text-overline opacity-60 font-weight-black mb-1">Monthly Spending
                            </div>
                            <div class="text-h5 font-weight-black text-error">{{ formatAmount(metrics.monthly_spending,
                                metrics.currency) }}</div>
                        </div>
                    </v-card>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-card class="premium-glass-card pa-6 d-flex flex-column justify-space-between" height="170"
                        rounded="xl" elevation="2" @click="router.push('/budgets')">
                        <div class="d-flex justify-space-between align-start">
                            <v-avatar color="warning" variant="tonal" rounded="lg" size="48">
                                <PieChart :size="24" />
                            </v-avatar>
                            <div class="text-h6 font-weight-black"
                                :class="metrics.budget_health.percentage > 90 ? 'text-error' : 'text-warning'">
                                {{ metrics.budget_health.percentage.toFixed(0) }}%
                            </div>
                        </div>
                        <div>
                            <div class="text-overline opacity-60 font-weight-black mb-1">Budget Health</div>
                            <v-progress-linear :model-value="Math.min(metrics.budget_health.percentage, 100)"
                                height="10" rounded="pill" class="mt-2 budget-progress-premium"
                                :class="metrics.budget_health.percentage > 90 ? 'health-danger' : 'health-warning'"></v-progress-linear>
                        </div>
                    </v-card>
                </v-col>

                <v-col cols="12" sm="6" lg="3">
                    <v-card class="premium-glass-card pa-6 d-flex flex-column justify-space-between" height="170"
                        rounded="xl" elevation="2" @click="router.push('/mutual-funds')">
                        <div class="d-flex justify-space-between align-start">
                            <v-avatar color="success" variant="tonal" rounded="lg" size="48">
                                <Sparkles :size="24" />
                            </v-avatar>
                            <v-chip v-if="!mfPortfolio.loading && mfPortfolio.invested > 0" size="small" color="success"
                                variant="flat" class="font-weight-black">
                                {{ mfPortfolio.xirr.toFixed(1) }}% XIRR
                            </v-chip>
                        </div>
                        <div>
                            <div class="text-overline opacity-60 font-weight-black mb-1">Investments</div>
                            <div class="text-h5 font-weight-black text-success">{{ formatAmount(mfPortfolio.current) }}
                            </div>
                        </div>
                    </v-card>
                </v-col>

                <!-- ROW 2: Budget Pulse -->
                <v-col cols="12" v-if="budgetPulse.length > 0" class="mt-4">
                    <div class="d-flex justify-space-between align-center mb-6">
                        <h2 class="text-h6 font-weight-black d-flex align-center">
                            <PieChart :size="20" class="text-primary mr-2" />
                            Budget Pulse
                        </h2>
                        <v-btn variant="text" size="small" color="primary" @click="router.push('/budgets')"
                            class="font-weight-black text-none">Manage</v-btn>
                    </div>

                    <v-row>
                        <v-col v-for="b in budgetPulse" :key="b.id" cols="12" sm="6" md="4" lg="3">
                            <v-card class="premium-glass-card pa-5" rounded="xl" elevation="1"
                                @click="router.push('/budgets')">
                                <div class="d-flex justify-space-between align-center mb-3">
                                    <div class="d-flex align-center ga-2">
                                        <v-avatar size="32" color="surface-variant" variant="tonal">
                                            <span class="text-subtitle-2">{{ getCategoryDetails(b.category).icon
                                                }}</span>
                                        </v-avatar>
                                        <span class="text-subtitle-2 font-weight-black">
                                            {{ b.category }}
                                        </span>
                                        <v-chip size="x-small"
                                            :color="b.percentage > 100 ? 'error' : (b.percentage > 85 ? 'warning' : 'success')"
                                            variant="flat" class="font-weight-bold">
                                            {{ b.percentage > 100 ? 'Crit' : (b.percentage > 85 ? 'Warn' : 'Good') }}
                                        </v-chip>
                                    </div>
                                    <span class="text-caption font-weight-black"
                                        :class="b.percentage > 100 ? 'text-error' : 'text-primary'">
                                        {{ b.percentage.toFixed(0) }}%
                                    </span>
                                </div>
                                <v-progress-linear :model-value="Math.min(b.percentage, 100)" height="6" rounded="pill"
                                    class="mb-3 budget-progress-premium"
                                    :class="b.percentage > 100 ? 'health-danger' : (b.percentage > 85 ? 'health-warning' : 'health-success')">
                                </v-progress-linear>
                                <div class="d-flex justify-space-between text-caption font-weight-bold opacity-60">
                                    <span>{{ formatAmount(b.spent, metrics.currency) }}</span>
                                    <span>of {{ formatAmount(b.amount_limit, metrics.currency) }}</span>
                                </div>

                                <!-- Subtle background icon -->
                                <div class="card-bg-icon-standard">
                                    <PieChart :size="120" />
                                </div>
                            </v-card>
                        </v-col>
                    </v-row>
                </v-col>

                <!-- ROW 3: Side-by-Side Activity and Bills -->
                <v-col cols="12" lg="7">
                    <v-card class="premium-glass-card pa-6 pa-md-8 h-100" rounded="xl" elevation="1">
                        <div class="d-flex justify-space-between align-center mb-8">
                            <h2 class="text-h6 font-weight-black d-flex align-center">
                                <Activity :size="20" class="text-primary mr-2" />
                                Recent Activity
                            </h2>
                            <v-btn variant="tonal" rounded="pill" size="small" color="primary"
                                @click="router.push('/transactions')" class="font-weight-black px-6 text-none">View
                                All</v-btn>
                        </div>
                        <v-list class="pa-0">
                            <v-list-item v-for="txn in metrics.recent_transactions.slice(0, 5)" :key="txn.id"
                                class="rounded-xl px-4 py-3 mb-2 border border-dashed">
                                <template v-slot:prepend>
                                    <v-avatar size="48" :color="getCategoryDetails(txn.category).color + '15'"
                                        class="mr-4">
                                        <span class="text-h6">{{ getCategoryDetails(txn.category).icon }}</span>
                                    </v-avatar>
                                </template>
                                <v-list-item-title class="font-weight-bold text-subtitle-1">{{ txn.description ||
                                    'Transaction'
                                    }}</v-list-item-title>
                                <v-list-item-subtitle class="text-caption font-weight-bold opacity-60 mt-1">
                                    {{ formatDate(txn.date).day }} • {{ txn.account_owner_name || 'Personal' }}
                                </v-list-item-subtitle>
                                <template v-slot:append>
                                    <div class="text-subtitle-1 font-weight-black"
                                        :class="txn.amount > 0 ? 'text-success' : 'opacity-80'">
                                        {{ txn.amount > 0 ? '+' : '' }}{{ formatAmount(Math.abs(txn.amount),
                                            metrics.currency) }}
                                    </div>
                                </template>
                            </v-list-item>
                        </v-list>
                    </v-card>
                </v-col>

                <v-col cols="12" lg="5">
                    <v-card class="premium-glass-card pa-6 pa-md-8 h-100" rounded="xl" elevation="1">
                        <div class="d-flex justify-space-between align-center mb-8">
                            <h2 class="text-h6 font-weight-black d-flex align-center">
                                <CalendarClock :size="20" class="text-primary mr-2" />
                                Upcoming Bills
                            </h2>
                        </div>
                        <div v-if="upcomingBills.length > 0">
                            <v-list class="pa-0">
                                <v-list-item v-for="bill in upcomingBills" :key="bill.id"
                                    class="rounded-xl px-4 py-3 mb-2 border border-dashed">
                                    <template v-slot:prepend>
                                        <v-avatar size="40" color="surface-variant" variant="tonal" class="mr-4">
                                            <span class="text-subtitle-2">{{ getCategoryDetails(bill.category).icon
                                                }}</span>
                                        </v-avatar>
                                    </template>
                                    <v-list-item-title class="font-weight-bold">{{ bill.description
                                        }}</v-list-item-title>
                                    <v-list-item-subtitle class="text-caption font-weight-bold text-error">Due {{
                                        formatDate(bill.next_date).day }}</v-list-item-subtitle>
                                    <template v-slot:append>
                                        <div class="text-subtitle-1 font-weight-black">{{ formatAmount(bill.amount) }}
                                        </div>
                                    </template>
                                </v-list-item>
                            </v-list>
                        </div>
                        <div v-else class="text-center py-10">
                            <div class="text-h2 mb-4 opacity-20">📅</div>
                            <p class="opacity-60 font-weight-bold">Relax, no bills due soon.</p>
                        </div>
                    </v-card>
                </v-col>

                <!-- ROW 4: Credit Intelligence -->
                <v-col cols="12">
                    <v-card class="premium-glass-card pa-6 pa-md-8 overflow-visible" rounded="xl" elevation="1">
                        <div
                            class="d-flex flex-column flex-md-row justify-space-between align-start align-md-center mb-8 ga-4">
                            <h2 class="text-h6 font-weight-black d-flex align-center">
                                <CreditCard :size="20" class="text-primary mr-2" />
                                Credit Intelligence
                            </h2>

                            <div v-if="metrics.credit_intelligence.length > 0" class="flex-grow-1 ml-md-10"
                                style="max-width: 400px; width: 100%;">
                                <div class="d-flex justify-space-between mb-2">
                                    <span class="text-overline opacity-60 font-weight-black">TOTAL CREDIT
                                        OUTLOOK</span>
                                    <span class="text-caption font-weight-black text-primary">
                                        {{ formatAmount(creditSummary.totalDebt) }} utilized
                                    </span>
                                </div>
                                <v-progress-linear :model-value="Math.min(creditSummary.utilization, 100)" height="10"
                                    rounded="pill" class="credit-progress-premium">
                                </v-progress-linear>
                                <div class="d-flex justify-space-between mt-1">
                                    <span class="text-caption font-weight-bold opacity-50">0%</span>
                                    <span class="text-caption font-weight-bold opacity-50">Limit: {{
                                        formatAmount(creditSummary.totalLimit) }}</span>
                                </div>
                            </div>
                        </div>

                        <div v-if="sortedCredit.length > 0">
                            <v-row v-for="(card, index) in sortedCredit" :key="card.id" class="align-center py-4 px-2">
                                <v-col cols="12" md="4" class="d-flex align-center">
                                    <v-card width="100" height="64"
                                        class="flex-shrink-0 d-flex flex-column justify-end pa-2"
                                        :style="{ background: getBankBrand(card.name).gradient, borderRadius: '8px' }"
                                        elevation="4">
                                        <div class="text-caption font-weight-black"
                                            :style="{ color: getBankBrand(card.name).logoColor, fontSize: '0.6rem', lineHeight: '1' }">
                                            {{ getBankBrand(card.name).logo }}</div>
                                        <div class="mt-auto d-flex justify-space-between align-center">
                                            <div class="bg-amber-lighten-4 rounded-sm"
                                                style="width: 14px; height: 10px;"></div>
                                            <div class="text-caption font-weight-black"
                                                :style="{ color: getBankBrand(card.name).textColor, fontSize: '0.55rem' }">
                                                •••• {{
                                                    card.last_digits || '0000' }}</div>
                                        </div>
                                    </v-card>
                                    <div class="ml-4 overflow-hidden">
                                        <div class="text-subtitle-1 font-weight-black text-truncate">{{ card.name }}
                                        </div>
                                        <div class="text-caption font-weight-bold opacity-60">....{{
                                            card.last_digits ||
                                            '0000' }}</div>
                                    </div>
                                </v-col>

                                <v-col cols="12" md="4">
                                    <div class="d-flex justify-space-between mb-1">
                                        <div class="d-flex align-center ga-2">
                                            <span class="text-overline opacity-60 font-weight-black">Utilization</span>
                                            <v-chip size="x-small"
                                                :color="card.utilization > 30 ? (card.utilization > 70 ? 'error' : 'warning') : 'success'"
                                                variant="flat" class="font-weight-black">
                                                {{ card.utilization > 30 ? (card.utilization > 70 ? 'Critical' :
                                                    'Caution') : 'Healthy'
                                                }}
                                            </v-chip>
                                        </div>
                                        <span class="text-caption font-weight-black"
                                            :class="card.utilization > 70 ? 'text-error' : 'text-primary'">
                                            {{ card.utilization.toFixed(0) }}%
                                        </span>
                                    </div>
                                    <v-progress-linear :model-value="Math.min(card.utilization, 100)" height="10"
                                        rounded="pill" class="credit-progress-premium"
                                        :class="card.utilization > 70 ? 'health-danger' : ''"></v-progress-linear>
                                </v-col>

                                <v-col cols="12" md="4" class="text-md-right">
                                    <div class="d-flex flex-md-column justify-space-between align-end">
                                        <div class="d-flex ga-6 mb-1">
                                            <div class="text-right">
                                                <div class="text-overline opacity-60 font-weight-black"
                                                    style="line-height:1">
                                                    Balance</div>
                                                <div class="text-subtitle-1 font-weight-black">{{
                                                    formatAmount(card.balance) }}</div>
                                            </div>
                                            <div class="text-right">
                                                <div class="text-overline opacity-60 font-weight-black"
                                                    style="line-height:1">
                                                    Available</div>
                                                <div class="text-subtitle-1 font-weight-black text-primary">{{
                                                    formatAmount((card.limit
                                                        || 0) - (card.balance || 0)) }}</div>
                                            </div>
                                        </div>
                                        <div class="text-caption font-weight-black d-flex align-center"
                                            :class="card.days_until_due < 7 && card.days_until_due !== null ? 'text-error' : 'text-slate-500'">
                                            <AlertCircle v-if="card.days_until_due < 7 && card.days_until_due !== null"
                                                :size="14" class="mr-1" />
                                            <span v-if="card.days_until_due !== null">Due in {{ card.days_until_due }}
                                                days</span>
                                            <span v-else>No Cycle Data</span>
                                        </div>
                                    </div>
                                </v-col>
                                <v-col cols="12" v-if="index < sortedCredit.length - 1" class="py-0">
                                    <v-divider class="my-2 opacity-20"></v-divider>
                                </v-col>
                            </v-row>
                        </div>
                        <div v-else class="text-center py-12">
                            <p class="opacity-60 font-weight-bold italic">No credit lines detected in your
                                accounts.</p>
                        </div>
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
import {
    Wallet,
    PieChart,
    Landmark,
    Sparkles,
    Activity,
    CalendarClock,
    CreditCard,
    AlertCircle
} from 'lucide-vue-next'

const router = useRouter()
const auth = useAuthStore()
const { formatAmount } = useCurrency()

// --- State ---
const loading = ref(true)
const accounts = ref<any[]>([])
const categories = ref<any[]>([])
const budgets = ref<any[]>([])
const expenseGroups = ref<any[]>([])

const mfPortfolio = ref({
    invested: 0,
    current: 0,
    pl: 0,
    plPercent: 0,
    xirr: 0,
    trend: [] as number[],
    allocation: { equity: 0, debt: 0, hybrid: 0, other: 0 } as any,
    topPerformer: null as any,
    loading: true
})

const netWorthTrend = ref<number[]>([])
const spendingTrend = ref<number[]>([])
const recurringTransactions = ref<any[]>([])

const metrics = ref({
    breakdown: {
        net_worth: 0,
        bank_balance: 0,
        cash_balance: 0,
        credit_debt: 0,
        investment_value: 0,
        total_credit_limit: 0,
        available_credit: 0,
        overall_credit_utilization: 0
    },
    monthly_spending: 0,
    total_excluded: 0,
    excluded_income: 0,
    top_spending_category: null as { name: string, amount: number } | null,
    budget_health: {
        limit: 0,
        spent: 0,
        percentage: 0
    },
    credit_intelligence: [] as any[],
    recent_transactions: [] as any[],
    currency: 'INR'
})


const budgetPulse = computed(() => {
    return budgets.value
        .filter(b => b.category !== 'OVERALL')
        .sort((a, b) => b.percentage - a.percentage)
        .slice(0, 3)
})

const netWorth = computed(() => {
    const liquid = (metrics.value.breakdown.bank_balance || 0) + (metrics.value.breakdown.cash_balance || 0)
    const totalInvestments = mfPortfolio.value.current || 0
    const totalDebt = metrics.value.breakdown.credit_debt || 0
    return liquid + totalInvestments - totalDebt
})

const sortedCredit = computed(() => {
    return [...metrics.value.credit_intelligence].sort((a, b) => {
        if (a.days_until_due === null) return 1
        if (b.days_until_due === null) return -1
        return a.days_until_due - b.days_until_due
    })
})

const creditSummary = computed(() => {
    const totalLimit = metrics.value.breakdown.total_credit_limit || 0
    const totalDebt = metrics.value.breakdown.credit_debt || 0
    const utilization = totalLimit > 0 ? (totalDebt / totalLimit) * 100 : 0
    return { totalLimit, totalDebt, utilization }
})

const upcomingBills = computed(() => {
    return recurringTransactions.value
        .filter(t => t.status === 'ACTIVE')
        .slice(0, 3)
})

// --- Helpers & Composables ---
const { formatDate, getCategoryDisplay } = useTransactionHelpers(accounts, categories, expenseGroups)
const { getGreeting, getBankBrand } = useDashboardHelpers()

function getCategoryDetails(name: string) {
    const display = getCategoryDisplay(name)
    return { icon: display.icon, color: display.color }
}

const greetingEmoji = computed(() => {
    const g = getGreeting()
    if (g.includes('Morning')) return '🌅'
    if (g.includes('Afternoon')) return '☀️'
    return '🌙'
})

// --- Data Fetching ---
async function fetchAllData() {
    loading.value = true
    mfPortfolio.value.loading = true
    const userId = auth.selectedMemberId || undefined

    setTimeout(() => { loading.value = false }, 300)

    // 1. Metrics
    financeApi.getMetrics(undefined, undefined, undefined, userId)
        .then(res => { metrics.value = res.data })
        .catch(e => console.warn("Metrics fetch failed", e))

    // 2. Portfolio
    financeApi.getPortfolio(userId)
        .then(pfRes => {
            if (pfRes && pfRes.data && Array.isArray(pfRes.data)) {
                let invested = 0, current = 0
                pfRes.data.forEach((h: any) => {
                    invested += Number(h.invested_value || h.investedValue || h.invested_amount || 0)
                    current += Number(h.current_value || h.currentValue || h.value || 0)
                })
                mfPortfolio.value.invested = invested
                mfPortfolio.value.current = current
                mfPortfolio.value.pl = current - invested
                mfPortfolio.value.plPercent = invested > 0 ? ((current - invested) / invested) * 100 : 0
            }
        })
        .catch(e => console.warn("Portfolio fetch failed", e))

    // 3. Analytics
    financeApi.getAnalytics(userId)
        .then(anRes => {
            if (anRes && anRes.data) {
                mfPortfolio.value.xirr = Number(anRes.data.xirr || 0)
                mfPortfolio.value.allocation = anRes.data.asset_allocation || { equity: 0, debt: 0, hybrid: 0, other: 0 }
                if (anRes.data.top_gainers?.length > 0) {
                    const top = anRes.data.top_gainers[0]
                    mfPortfolio.value.topPerformer = {
                        schemeName: top.scheme_name || top.scheme,
                        plPercent: Number(top.pl_percent || top.returns || 0)
                    }
                }
                mfPortfolio.value.loading = false
            }
        })
        .catch(e => {
            console.warn("Analytics fetch failed", e)
            mfPortfolio.value.loading = false
        })

    // 4. Timeline
    financeApi.getPerformanceTimeline('1m', '1d', userId)
        .then(res => {
            const timeline = Array.isArray(res.data) ? res.data : (res.data.timeline || [])
            mfPortfolio.value.trend = timeline.map((p: any) => Number(p.value || 0))
        })
        .catch(e => console.warn("Timeline fetch failed", e))

    // 5. Recurring
    financeApi.getRecurringTransactions()
        .then(res => { recurringTransactions.value = res.data })
        .catch(e => console.warn("Recurring fetch failed", e))

    // 6. Net Worth Trend
    financeApi.getNetWorthTimeline(30, userId)
        .then(res => { netWorthTrend.value = res.data.map((p: any) => Number(p.total || 0)) })
        .catch(e => console.warn("Net worth trend failed", e))

    // 7. Spending Trend
    financeApi.getSpendingTrend(userId)
        .then(res => { spendingTrend.value = res.data.map((p: any) => Number(p.amount || 0)) })
        .catch(e => console.warn("Spending trend failed", e))
}

async function fetchMetadata() {
    const userId = auth.selectedMemberId || undefined
    try {
        const [catRes, budgetRes, accRes, expRes] = await Promise.all([
            financeApi.getCategories(),
            financeApi.getBudgets(undefined, undefined, userId),
            financeApi.getAccounts(userId),
            financeApi.getExpenseGroups(userId)
        ])
        categories.value = catRes.data
        budgets.value = budgetRes.data
        accounts.value = accRes.data
        expenseGroups.value = expRes.data
    } catch (e) {
        console.error("Failed to fetch dashboard metadata", e)
    }
}

onMounted(async () => {
    await fetchMetadata()
    await fetchAllData()
})

watch(() => auth.selectedMemberId, async () => {
    await fetchMetadata()
    await fetchAllData()
})
</script>

<style scoped>
.snap-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface), 0.6);
}

.snap-val {
    font-size: 1rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
}

/* Premium Progress Gradients */
.budget-progress-premium :deep(.v-progress-linear__determinate) {
    transition: all 0.5s ease;
}

.budget-progress-premium.health-success :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #059669 0%, #10b981 50%, #34d399 100%) !important;
}

.budget-progress-premium.health-warning :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #d97706 0%, #f59e0b 50%, #fbbf24 100%) !important;
}

.budget-progress-premium.health-danger :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #991b1b 0%, #ef4444 50%, #f87171 100%) !important;
}

.credit-progress-premium :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%) !important;
}

.credit-progress-premium.health-danger :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #991b1b 0%, #ef4444 100%) !important;
}

:deep(.v-progress-linear__background) {
    opacity: 0.1 !important;
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
    z-index: 0;
}

.premium-glass-card:hover .card-bg-icon-standard {
    transform: rotate(0deg) scale(1.1);
    opacity: 0.05;
}
</style>
