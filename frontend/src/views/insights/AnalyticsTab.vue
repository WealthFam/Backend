<template>
    <div class="analytics-content px-0 pb-6">
        <!-- Redesigned Period Filter Bar -->
        <v-card variant="flat" class="premium-glass-card mb-8 no-hover" rounded="xl">
            <v-row align="center" class="pa-2">
                <v-col cols="12" md="auto" class="d-flex align-center px-4">
                    <CalendarRange :size="20" class="text-primary mr-3" />
                    <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Analysis Period</span>
                </v-col>

                <v-col cols="12" md="auto" class="d-flex align-center px-4">
                    <div class="d-flex align-center gap-2">
                        <div class="premium-button-group pa-1 border rounded-pill d-flex"
                            style="background: rgba(var(--v-theme-surface), 0.5)">
                            <v-btn v-for="opt in timeRangeOptions" :key="opt.value" variant="flat" rounded="pill"
                                size="small" class="text-none font-weight-black px-5 letter-spacing-1 h-32"
                                :color="selectedTimeRange === opt.value ? 'primary' : 'transparent'"
                                :class="selectedTimeRange === opt.value ? 'elevation-4 border' : 'text-medium-emphasis'"
                                @click="handleTimeRangeChange(opt.value)">
                                {{ opt.label }}
                            </v-btn>
                        </div>

                        <v-btn v-if="selectedTimeRange !== 'this-month' && selectedTimeRange !== 'all'" variant="text"
                            size="small" color="primary" rounded="pill"
                            @click="selectedTimeRange = 'this-month'; handleTimeRangeChange('this-month')"
                            class="text-none font-weight-black ml-2">
                            <template v-slot:prepend>
                                <RefreshCcw :size="14" />
                            </template>
                            Reset
                        </v-btn>
                    </div>
                </v-col>

                <v-spacer />

                <v-col cols="12" md="auto" class="px-4 d-flex align-center">
                    <v-expand-x-transition>
                        <div v-if="selectedTimeRange === 'custom'" class="d-flex align-center gap-3">
                            <v-text-field v-model="startDate" type="date" hide-details density="compact"
                                variant="solo-filled" flat @change="fetchAnalyticsData"
                                class="date-picker-compact rounded-lg" rounded="lg"
                                style="background: rgba(var(--v-theme-surface-variant), 0.2);" />
                            <ArrowRight :size="16" class="text-medium-emphasis" />
                            <v-text-field v-model="endDate" type="date" hide-details density="compact"
                                variant="solo-filled" flat @change="fetchAnalyticsData"
                                class="date-picker-compact rounded-lg" rounded="lg"
                                style="background: rgba(var(--v-theme-surface-variant), 0.2);" />
                        </div>
                    </v-expand-x-transition>

                </v-col>
            </v-row>
        </v-card>

        <v-row>
            <!-- AI Insight Card -->
            <v-col cols="12">
                <v-card class="premium-ai-card" rounded="xl" elevation="10">
                    <div class="ai-card-inner">
                        <div class="d-flex align-center justify-space-between mb-6">
                            <div class="d-flex align-center">
                                <div class="ai-glow-icon mr-4">
                                    <Sparkles :size="24" color="white" />
                                </div>
                                <div>
                                    <h3 class="text-h5 font-weight-black text-white">Financial Intelligence</h3>
                                    <p class="text-caption text-blue-lighten-4">AI-driven spending vectors and strategy
                                    </p>
                                </div>
                            </div>
                            <v-btn variant="tonal" color="white" rounded="lg" :loading="generatingAI"
                                @click="generateAIInsights" class="text-none font-weight-bold">
                                {{ aiInsights ? 'Update Insights' : 'Generate Intelligence' }}
                            </v-btn>
                        </div>

                        <v-expand-transition>
                            <div v-if="aiInsights" class="ai-markdown-container premium-scroll">
                                <div class="markdown-content" v-html="marked(aiInsights)"></div>
                            </div>
                            <div v-else-if="generatingAI" class="ai-shimmer-container">
                                <div v-for="i in 3" :key="i" class="shimmer-line"></div>
                            </div>
                            <div v-else class="ai-empty-state text-center py-6">
                                <Brain :size="48" class="text-blue-lighten-4 mb-2" />
                                <p class="text-body-2 text-blue-lighten-4">Analysis ready. Generate smart optimization
                                    tips based on your patterns.</p>
                            </div>
                        </v-expand-transition>
                    </div>
                    <div class="ai-background-blobs">
                        <div class="blob-blue"></div>
                        <div class="blob-purple"></div>
                    </div>
                </v-card>
            </v-col>

            <!-- Summary Cards -->
            <v-col cols="12" md="4">
                <v-card rounded="xl" class="stat-glass-card stat-income">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow mr-4">
                            <TrendingUp :size="32" class="text-success" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis">Total Income</span>
                            <h2 class="text-h4 font-weight-bold text-success">{{
                                formatAmount(analyticsMetrics?.monthly_income
                                    ?? analyticsData.income) }}
                            </h2>
                        </div>
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" md="4">
                <v-card rounded="xl" class="stat-glass-card stat-expense">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow mr-4">
                            <TrendingDown :size="32" class="text-error" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis">Total Expenses</span>
                            <h2 class="text-h4 font-weight-bold text-error">{{
                                formatAmount(analyticsMetrics?.monthly_total ??
                                    analyticsData.expense) }}
                            </h2>
                        </div>
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" md="4">
                <v-card rounded="xl" class="stat-glass-card stat-net">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow mr-4">
                            <Scale :size="32" class="text-primary" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis">Net Cashflow</span>
                            <h2 class="text-h4 font-weight-bold"
                                :class="(analyticsMetrics?.monthly_income ?? 0) >= (analyticsMetrics?.monthly_total ?? 0) ? 'text-primary' : 'text-error'">
                                {{ formatAmount((analyticsMetrics?.monthly_income ?? 0) -
                                    (analyticsMetrics?.monthly_total ??
                                        0)) }}
                            </h2>
                        </div>
                    </div>
                </v-card>
            </v-col>

            <!-- Premium Protected Transactions Insight -->
            <v-col v-if="analyticsData.excludedExpense > 0 || analyticsData.excludedIncome > 0" cols="12">
                <v-card variant="flat" rounded="xl" class="protected-insight-card pa-6 cursor-pointer"
                    @click="showExcludedDetails = !showExcludedDetails">
                    <v-row align="center">
                        <v-col cols="auto">
                            <div class="shield-glow-icon">
                                <ShieldAlert :size="28" class="text-orange" />
                            </div>
                        </v-col>
                        <v-col>
                            <div class="text-h6 font-weight-black mb-1">Protected Transactions Notice</div>
                            <div class="text-body-2 text-medium-emphasis font-weight-medium">
                                We've' hidden <strong>{{ formatAmount(analyticsData.excludedExpense +
                                    analyticsData.excludedIncome) }}</strong> from your primary reports.
                                This includes transfers and items you've marked as "Protected" to keep your intelligence
                                data
                                accurate.
                            </div>
                        </v-col>
                        <v-col cols="auto" class="text-right">
                            <div class="d-flex flex-column align-end gap-2">
                                <v-chip v-if="analyticsData.excludedIncome" color="success" variant="tonal" size="small"
                                    class="font-weight-bold px-3">
                                    +{{ formatAmount(analyticsData.excludedIncome) }} Income Shielded
                                </v-chip>
                                <v-chip v-if="analyticsData.excludedExpense" color="error" variant="tonal" size="small"
                                    class="font-weight-bold px-3">
                                    -{{ formatAmount(analyticsData.excludedExpense) }} Spending Shielded
                                </v-chip>
                            </div>
                        </v-col>
                    </v-row>

                    <v-expand-transition>
                        <div v-if="showExcludedDetails" class="mt-6 pt-6 border-t">
                            <h4 class="text-overline font-weight-black mb-4 letter-spacing-1">Shielded Categories
                                Breakdown</h4>
                            <v-row dense>
                                <v-col v-for="cat in analyticsData.excludedCategories" :key="cat.name" cols="12" sm="6"
                                    md="3">
                                    <div
                                        class="d-flex align-center pa-3 rounded-lg bg-surface-variant bg-opacity-10 border">
                                        <v-avatar size="32" class="mr-3" color="surface-variant" rounded="lg">
                                            <span class="text-caption">{{ cat.icon }}</span>
                                        </v-avatar>
                                        <div class="overflow-hidden">
                                            <div class="text-caption font-weight-bold text-truncate">{{ cat.name }}
                                            </div>
                                            <div class="text-subtitle-2 font-weight-black">{{ formatAmount(cat.value) }}
                                            </div>
                                        </div>
                                    </div>
                                </v-col>
                            </v-row>
                        </div>
                    </v-expand-transition>
                </v-card>
            </v-col>

            <!-- Major Charts Grid -->
            <v-col cols="12" md="6">
                <v-card rounded="xl" class="premium-glass-card h-100 no-hover">
                    <v-card-title class="d-flex align-center px-6 pt-6">
                        <Sparkles :size="20" class="text-primary mr-3" />
                        <span class="text-h6 font-weight-black">Spending Categorization</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="chart-container">
                            <BaseChart type="doughnut" :data="categoryChartData" :height="300" />
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="12" md="6">
                <v-card rounded="xl" class="premium-glass-card h-100 no-hover">
                    <v-card-title class="d-flex align-center px-6 pt-6">
                        <Scale :size="20" class="text-primary mr-3" />
                        <span class="text-h6 font-weight-black">Top Merchants</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="chart-container">
                            <BaseChart type="bar" :data="merchantChartData" :height="300" :options="{
                                indexAxis: 'y',
                                plugins: { legend: { display: false } },
                                scales: {
                                    x: { grid: { display: false, color: 'rgba(0,0,0,0.05)' } },
                                    y: { grid: { display: false } }
                                }
                            }" />
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="12">
                <v-card rounded="xl" class="premium-glass-card no-hover">
                    <v-card-title class="d-flex align-center justify-space-between px-6 pt-6">
                        <div class="d-flex align-center">
                            <TrendingUp :size="20" class="text-primary mr-3" />
                            <span class="text-h6 font-weight-black">Spending Dynamics</span>
                        </div>
                        <div class="d-flex align-center gap-4">
                            <v-btn-toggle v-model="trendView" mandatory density="compact" color="primary"
                                variant="tonal">
                                <v-btn value="daily" class="text-none">Daily</v-btn>
                                <v-btn value="monthly" class="text-none">Monthly</v-btn>
                            </v-btn-toggle>
                            <v-select v-model="selectedTrendCategory"
                                :items="categoryOptions.map(c => ({ title: c.label, value: c.value }))"
                                density="compact" variant="outlined" hide-details class="trend-cat-premium"
                                rounded="pill" menu-icon=""
                                style="background: rgba(var(--v-theme-surface), 0.7); width: 220px;">
                                <template v-slot:prepend-inner>
                                    <v-icon size="small" class="text-primary mr-1">mdi-filter-variant</v-icon>
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary opacity-70" />
                                </template>
                            </v-select>
                        </div>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="large-chart-container">
                            <BaseChart v-if="filteredTrendData.length > 0" type="line" :data="trendChartData"
                                :height="400" />
                            <div v-else class="empty-state d-flex flex-column align-center justify-center h-100">
                                <v-icon size="64" color="medium-emphasis">mdi-chart-bubble-none</v-icon>
                                <p class="mt-4 text-medium-emphasis">No spending data found for these filters</p>
                            </div>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="12" md="8">
                <v-card rounded="xl" class="premium-glass-card h-100 no-hover">
                    <v-card-title class="d-flex align-center px-6 pt-6">
                        <Sparkles :size="20" class="text-primary mr-3" />
                        <span class="text-h6 font-weight-black">Foresight Forecast</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="chart-container relative">
                            <BaseChart v-if="forecastData.length > 0" type="line" :data="forecastChartData"
                                :height="300" />
                            <div v-else class="d-flex items-center justify-center fill-height">Calculative Projection...
                            </div>
                        </div>
                        <v-alert density="compact" variant="tonal" type="info" class="mt-4 text-caption rounded-lg"
                            rounded="lg">
                            Projected based on recurring bills and 30-day burn rate.
                            <template #append>
                                <span class="font-weight-black text-body-2">
                                    Est. Net: {{formatAmount(analyticsData.net +
                                        store.recurringTransactions.reduce((acc, t) => acc + (t.type === 'DEBIT' ? -t.amount
                                            : t.amount), 0))}}
                                </span>
                            </template>
                        </v-alert>
                    </v-card-text>
                </v-card>
            </v-col>

            <v-col cols="12" md="4">
                <v-card rounded="xl" class="premium-glass-card h-100 no-hover">
                    <v-card-title class="d-flex align-center px-6 pt-6">
                        <TrendingUp :size="20" class="text-primary mr-3" />
                        <span class="text-h6 font-weight-black">Historical Arc</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <BudgetHistoryChart v-if="budgetHistory.length > 0" :history="budgetHistory" />
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Heatmap Section -->
            <v-col cols="12">
                <v-card rounded="xl" class="premium-glass-card overflow-hidden no-hover">
                    <v-card-title class="d-flex align-center px-6 pt-6">
                        <Brain :size="20" class="text-primary mr-3" />
                        <span class="text-h6 font-weight-black">Category Temporal Heatmap</span>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="heatmap-scroll premium-scroll">
                            <div class="heatmap-grid">
                                <div class="heatmap-header-row">
                                    <div class="heatmap-label-cell"></div>
                                    <div v-for="h in heatmapData.hours" :key="h" class="hour-label">{{ h }}h</div>
                                </div>
                                <div v-for="cat in heatmapData.categories" :key="cat" class="heatmap-data-row">
                                    <div class="heatmap-label-cell truncate">{{ cat }}</div>
                                    <v-tooltip v-for="h in heatmapData.hours" :key="h" location="top">
                                        <template #activator="{ props }">
                                            <div v-bind="props" class="heatmap-square" :style="{
                                                opacity: heatmapData.grid[cat][h] > 0 ? 0.2 + (heatmapData.grid[cat][h] / heatmapData.max * 0.8) : 0.05,
                                                backgroundColor: store.getCategoryColor(cat)
                                            }"></div>
                                        </template>
                                        <span>{{ cat }} at {{ h }}h: {{ formatAmount(heatmapData.grid[cat][h]) }}</span>
                                    </v-tooltip>
                                </div>
                            </div>
                        </div>
                        <div class="d-flex align-center justify-space-between mt-6 pt-4 border-t-sm">
                            <div class="heatmap-legend d-flex align-center gap-4">
                                <span class="text-caption text-medium-emphasis">Intensity:</span>
                                <div class="heatmap-gradient"></div>
                            </div>
                            <span class="text-caption text-medium-emphasis">Hover over cells for detail</span>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>
        </v-row>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import { financeApi, aiApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import BaseChart from '@/components/BaseChart.vue'
import BudgetHistoryChart from '@/components/BudgetHistoryChart.vue'
import { marked } from 'marked'
import {
    Sparkles, Brain, TrendingUp, TrendingDown, Scale,
    ShieldAlert, CalendarRange, ArrowRight, RefreshCcw, ChevronDown
} from 'lucide-vue-next'

interface Props {
    selectedAccount?: string
}

const props = defineProps<Props>()

const store = useFinanceStore()
const authStore = useAuthStore()
const { formatAmount } = useCurrency()

// Filters local to analytics
const selectedTimeRange = ref('this-month')
const startDate = ref('')
const endDate = ref('')
const selectedTrendCategory = ref('')
const trendView = ref<'daily' | 'monthly'>('daily')

const timeRangeOptions = [
    { label: 'All Time', value: 'all' },
    { label: 'Today', value: 'today' },
    { label: 'This Week', value: 'this-week' },
    { label: 'This Month', value: 'this-month' },
    { label: 'Last Month', value: 'last-month' },
    { label: 'Custom Range', value: 'custom' }
]

// Data for Analytics
const transactions = ref<any[]>([])
const analyticsMetrics = ref<any>(null)
const forecastData = ref<any[]>([])
const budgets = ref<any[]>([])
const budgetHistory = ref<any[]>([])
const aiInsights = ref<string>('')
const generatingAI = ref(false)
const loading = ref(false)
const showExcludedDetails = ref(false)

onMounted(async () => {
    // Initial fetch
    handleTimeRangeChange('this-month')
})

// Watch for global member filter change
watch(() => authStore.selectedMemberId, async () => {
    await fetchAnalyticsData()
})

// Watch for shell-provided account filter
watch(() => props.selectedAccount, () => {
    fetchAnalyticsData()
})

function handleTimeRangeChange(val: string) {
    selectedTimeRange.value = val
    const now = new Date()
    const start = new Date()
    const end = new Date()

    startDate.value = ''
    endDate.value = ''

    if (val === 'today') {
        start.setHours(0, 0, 0, 0)
        end.setHours(23, 59, 59, 999)
        startDate.value = start.toISOString().split('T')[0]
        endDate.value = end.toISOString().split('T')[0]
    } else if (val === 'this-week') {
        const day = now.getDay()
        const diff = now.getDate() - day + (day === 0 ? -6 : 1)
        start.setDate(diff)
        start.setHours(0, 0, 0, 0)
        startDate.value = start.toISOString().split('T')[0]
    } else if (val === 'this-month') {
        start.setDate(1)
        start.setHours(0, 0, 0, 0)
        startDate.value = start.toISOString().split('T')[0]
    } else if (val === 'last-month') {
        start.setMonth(start.getMonth() - 1)
        start.setDate(1)
        start.setHours(0, 0, 0, 0)
        end.setMonth(end.getMonth())
        end.setDate(0)
        end.setHours(23, 59, 59, 999)
        startDate.value = start.toISOString().split('T')[0]
        endDate.value = end.toISOString().split('T')[0]
    }

    fetchAnalyticsData()
}

async function fetchAnalyticsData() {
    loading.value = true
    try {
        const userId = authStore.selectedMemberId || undefined
        const params = {
            start_date: startDate.value,
            end_date: endDate.value,
            account_id: props.selectedAccount || undefined
        }

        const [txnRes, metricsRes, forecastRes, budgetRes, historyRes] = await Promise.all([
            financeApi.getTransactions(params.account_id, 1, 1000, params.start_date || undefined, params.end_date || undefined, undefined, undefined, 'date', 'desc', userId),
            financeApi.getMetrics(params.account_id, params.start_date || undefined, params.end_date || undefined, userId),
            financeApi.getForecast(params.account_id, 30, userId),
            financeApi.getBudgets(undefined, undefined, userId),
            financeApi.getBudgetHistory(6, userId)
        ])
        transactions.value = txnRes.data.items
        analyticsMetrics.value = metricsRes.data
        forecastData.value = forecastRes.data
        budgets.value = budgetRes.data
        budgetHistory.value = historyRes.data
    } catch (e) {
        console.error(e)
    } finally {
        loading.value = false
    }
}

async function generateAIInsights() {
    generatingAI.value = true
    try {
        const timeContext = selectedTimeRange.value === 'custom'
            ? `from ${startDate.value} to ${endDate.value}`
            : `for ${selectedTimeRange.value.replace('-', ' ')}`

        const velocity = budgetHistory.value.length > 0 ? `Spending velocity is currently showing a ${overallBudget.value?.percentage > 80 ? 'HIGH' : 'STABLE'} trend relative to the monthly cycle.` : ''

        const promptData = {
            ...analyticsMetrics.value,
            budgets: budgets.value.map(b => ({
                category: b.category,
                limit: b.amount_limit,
                spent: b.spent,
                percent: b.percentage,
                status: b.percentage > 100 ? 'EXCEEDED' : (b.percentage > 80 ? 'CRITICAL' : 'OK')
            })),
            velocity_context: velocity,
            timeframe_filter: timeContext,
            account_filtered: props.selectedAccount ? "Yes" : "No",
            member_context: authStore.selectedMemberId ? "Filtered by specific member" : "Global view"
        }
        const res = await aiApi.generateSummaryInsights(promptData)
        aiInsights.value = res.data.insights
    } catch (e) {
        console.error(e)
        aiInsights.value = "Failed to generate insights. Ensure AI settings are configured."
    } finally {
        generatingAI.value = false
    }
}

const overallBudget = computed(() => budgets.value.find(b => b.category === 'OVERALL'))

// --- Analytics Computed Logic ---
function formatTypeLabel(type: string) {
    const labels: Record<string, string> = {
        'BANK': 'Bank', 'CREDIT_CARD': 'Card', 'LOAN': 'Loan', 'WALLET': 'Cash', 'INVESTMENT': 'Invest'
    }
    return labels[type] || type
}

const analyticsData = computed(() => {
    const data = transactions.value || []
    let income = 0
    let expense = 0
    let excludedExpense = 0
    let excludedIncome = 0
    const catMap: Record<string, number> = {}
    const excludedCatMap: Record<string, number> = {}
    const dateMap: Record<string, number> = {}
    const merchantMap: Record<string, number> = {}
    const accountMap: Record<string, number> = {}
    const typeMap: Record<string, number> = {}
    let weekendSpend = 0
    let weekdaySpend = 0

    // Fetch credit limit info from store accounts
    let totalLimit = 0
    let totalConsumed = 0
    store.accounts.forEach(acc => {
        if (acc.type === 'CREDIT_CARD' && acc.credit_limit) {
            totalLimit += Number(acc.credit_limit)
            totalConsumed += Number(acc.balance)
        }
    })

    data.forEach(t => {
        const amt = Number(t.amount)
        const isExpense = amt < 0
        const isTransfer = t.is_transfer === true
        const isExcluded = t.exclude_from_reports === true
        const absAmt = Math.abs(amt)

        if (isExcluded || isTransfer) {
            if (isExpense) excludedExpense += absAmt
            else excludedIncome += absAmt

            const cat = t.category || (isTransfer ? 'Transfer' : 'Uncategorized')
            excludedCatMap[cat] = (excludedCatMap[cat] || 0) + absAmt
            return
        }

        if (!isExpense) income += absAmt
        else {
            expense += absAmt
            // Categories
            const cat = t.category || 'Uncategorized'
            catMap[cat] = (catMap[cat] || 0) + absAmt

            // Merchants
            const merchant = t.recipient || 'Unknown'
            merchantMap[merchant] = (merchantMap[merchant] || 0) + absAmt

            // Accounts
            const accName = store.getAccountName(t.account_id)
            accountMap[accName] = (accountMap[accName] || 0) + absAmt

            // Account Type
            const acc = store.accounts.find(a => a.id === t.account_id)
            if (acc) {
                const label = formatTypeLabel(acc.type)
                typeMap[label] = (typeMap[label] || 0) + absAmt
            }

            // Patterns
            if (t.date) {
                const day = new Date(t.date).getDay()
                if (day === 0 || day === 6) weekendSpend += absAmt
                else weekdaySpend += absAmt
            }
        }

        const dateKey = t.date ? t.date.split('T')[0] : 'Unknown'
        if (isExpense) dateMap[dateKey] = (dateMap[dateKey] || 0) + absAmt
    })

    const toSortedArray = (map: Record<string, number>) => {
        return Object.entries(map).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({ name, value }))
    }

    return {
        income,
        expense,
        excludedExpense,
        excludedIncome,
        net: income - expense,
        categories: Object.entries(catMap).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({
            name, value, color: store.getCategoryColor(name), icon: store.getCategoryIcon(name)
        })),
        excludedCategories: Object.entries(excludedCatMap).sort((a, b) => b[1] - a[1]).map(([name, value]) => ({
            name, value, color: store.getCategoryColor(name), icon: store.getCategoryIcon(name)
        })),
        merchants: toSortedArray(merchantMap).slice(0, 5),
        accounts: toSortedArray(accountMap),
        types: toSortedArray(typeMap),
        credit: {
            limit: totalLimit,
            consumed: totalConsumed,
            available: totalLimit - totalConsumed,
            percent: totalLimit > 0 ? (totalConsumed / totalLimit * 100) : 0
        },
        patterns: {
            weekend: weekendSpend,
            weekday: weekdaySpend,
            weekendPercent: expense > 0 ? (weekendSpend / expense * 100) : 0,
            weekdayPercent: expense > 0 ? (weekdaySpend / expense * 100) : 0
        },
        count: data.length
    }
})

// --- Chart Data Preparations ---
const categoryOptions = computed(() => {
    return [{ label: 'All Categories', value: '' }, ...store.categories.map(c => ({ label: c.name, value: c.name }))]
})

const filteredTrendData = computed(() => {
    const txns = transactions.value.filter(t => {
        if (t.is_transfer || t.exclude_from_reports) return false
        if (Number(t.amount) >= 0) return false
        if (selectedTrendCategory.value && t.category !== selectedTrendCategory.value) return false
        return true
    })

    const map: Record<string, number> = {}
    txns.forEach(t => {
        const key = trendView.value === 'daily'
            ? t.date.split('T')[0]
            : t.date.slice(0, 7) // YYYY-MM
        map[key] = (map[key] || 0) + Math.abs(Number(t.amount))
    })

    return Object.entries(map)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([label, value]) => ({ label, value }))
})

const trendChartData = computed(() => ({
    labels: filteredTrendData.value.map(d => trendView.value === 'daily' ? d.label.slice(5) : d.label),
    datasets: [{
        label: selectedTrendCategory.value || 'All Spending',
        data: filteredTrendData.value.map(d => d.value),
        borderColor: selectedTrendCategory.value ? store.getCategoryColor(selectedTrendCategory.value) : '#6366f1',
        backgroundColor: (selectedTrendCategory.value ? store.getCategoryColor(selectedTrendCategory.value) : '#6366f1') + '20',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: selectedTrendCategory.value ? store.getCategoryColor(selectedTrendCategory.value) : '#6366f1'
    }]
}))


const heatmapData = computed(() => {
    const hours = Array.from({ length: 24 }, (_, i) => i)
    const activeCats = analyticsData.value.categories.slice(0, 8).map(c => c.name)

    // category -> hour -> amount
    const grid: Record<string, Record<number, number>> = {}
    activeCats.forEach(cat => {
        grid[cat] = {}
        hours.forEach(h => grid[cat][h] = 0)
    })

    transactions.value.forEach(t => {
        if (Number(t.amount) >= 0 || t.is_transfer) return
        if (!activeCats.includes(t.category)) return

        const date = new Date(t.date)
        const hour = date.getHours()
        if (grid[t.category]) {
            grid[t.category][hour] += Math.abs(Number(t.amount))
        }
    })

    // Find max for scaling
    let max = 0
    Object.values(grid).forEach(hMap => {
        Object.values(hMap).forEach(val => { if (val > max) max = val })
    })

    return { grid, categories: activeCats, hours, max }
})

const merchantChartData = computed(() => ({
    labels: analyticsData.value.merchants.map(m => m.name),
    datasets: [{
        label: 'Spending',
        data: analyticsData.value.merchants.map(m => m.value),
        backgroundColor: '#6366f1',
        borderRadius: 6,
        borderSkipped: false,
    }]
}))

const categoryChartData = computed(() => ({
    labels: analyticsData.value.categories.map(c => c.name),
    datasets: [{
        data: analyticsData.value.categories.map(c => c.value),
        backgroundColor: analyticsData.value.categories.map(c => c.color || '#3B82F6'),
        hoverOffset: 4
    }]
}))

const forecastChartData = computed(() => ({
    labels: forecastData.value.map(d => d.date.split('T')[0].slice(5)),
    datasets: [{
        label: 'Projected Balance',
        data: forecastData.value.map(d => d.balance),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0
    }]
}))
</script>

<style scoped>
/* AI Premium Card */
.premium-ai-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
    position: relative;
    overflow: hidden;
    border: none;
}

.ai-card-inner {
    position: relative;
    z-index: 2;
    padding: 32px;
}

.ai-glow-icon {
    width: 48px;
    height: 48px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 0 20px rgba(79, 70, 229, 0.4);
}

.ai-markdown-container {
    background: rgba(0, 0, 0, 0.2);
    border-radius: 16px;
    padding: 24px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    max-height: 400px;
    overflow-y: auto;
}

.markdown-content {
    color: #e2e8f0;
    line-height: 1.7;
    font-size: 0.95rem;
}

.markdown-content :deep(h4) {
    color: #fff;
    margin: 1.5rem 0 0.5rem 0;
    font-weight: 800;
}

.markdown-content :deep(strong) {
    color: #38bdf8;
    font-weight: 700;
}

.ai-background-blobs .blob-blue,
.ai-background-blobs .blob-purple {
    position: absolute;
    filter: blur(60px);
    opacity: 0.4;
    border-radius: 50%;
}

.blob-blue {
    width: 300px;
    height: 300px;
    background: #3b82f6;
    top: -100px;
    right: -100px;
}

.blob-purple {
    width: 250px;
    height: 250px;
    background: #8b5cf6;
    bottom: -80px;
    left: -50px;
}

.glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.glass-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1) !important;
}

.filter-glass {
    background: rgba(var(--v-theme-surface-variant), 0.3);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

/* Stat Cards */
.stat-glass-card {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.protected-insight-card {
    background: rgba(var(--v-theme-surface), 0.5);
    backdrop-filter: blur(15px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    transition: all 0.3s ease;
}

.protected-insight-card:hover {
    background: rgba(var(--v-theme-surface), 0.7);
    border-color: rgba(var(--v-theme-warning), 0.3);
}

.shield-glow-icon {
    width: 64px;
    height: 64px;
    background: rgba(var(--v-theme-warning), 0.1);
    border-radius: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(var(--v-theme-warning), 0.2);
}

.premium-button-group {
    background: rgba(var(--v-theme-surface), 0.7) !important;
}

.h-32 {
    height: 32px !important;
}

.stat-glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    padding: 8px;
}

.stat-icon-glow {
    padding: 12px;
    border-radius: 16px;
    background: rgba(var(--v-theme-surface-variant), 0.5);
    box-shadow: inset 0 0 20px rgba(0, 0, 0, 0.05);
}

/* Charts */
.chart-container {
    height: 300px;
    width: 100%;
}

.large-chart-container {
    height: 400px;
    width: 100%;
}

/* Heatmap */
.heatmap-scroll {
    overflow-x: auto;
    padding-bottom: 12px;
}

.heatmap-grid {
    min-width: 900px;
}

.heatmap-header-row,
.heatmap-data-row {
    display: grid;
    grid-template-columns: 140px repeat(24, 1fr);
    gap: 4px;
    margin-bottom: 4px;
}

.heatmap-label-cell {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface));
    display: flex;
    align-items: center;
}

.hour-label {
    font-size: 0.65rem;
    color: rgba(var(--v-theme-on-surface), 0.5);
    text-align: center;
}

.heatmap-square {
    height: 28px;
    border-radius: 4px;
    transition: transform 0.2s ease;
}

.heatmap-square:hover {
    transform: scale(1.15);
    z-index: 10;
}

.heatmap-gradient {
    width: 120px;
    height: 8px;
    border-radius: 4px;
    background: linear-gradient(to right, rgba(var(--v-theme-primary), 0.1), rgba(var(--v-theme-primary), 1));
}

.premium-scroll::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

.premium-scroll::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-on-surface), 0.1);
    border-radius: 10px;
}

.trend-cat-premium :deep(.v-field__outline) {
    --v-field-border-opacity: 0.1;
    transition: border-color 0.3s ease;
}

.trend-cat-premium:hover :deep(.v-field__outline) {
    --v-field-border-opacity: 0.4;
    border-color: rgb(var(--v-theme-primary)) !important;
}

.h-32 {
    height: 32px !important;
}
</style>
