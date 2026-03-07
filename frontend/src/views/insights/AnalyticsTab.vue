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
                            <v-text-field v-model="startDate" type="date" hide-details density="comfortable"
                                variant="outlined" flat @change="fetchAnalyticsData"
                                class="date-picker-compact rounded-lg" rounded="lg"
                                style="background: rgba(var(--v-theme-surface-variant), 0.2);" />
                            <ArrowRight :size="16" class="text-medium-emphasis" />
                            <v-text-field v-model="endDate" type="date" hide-details density="comfortable"
                                variant="outlined" flat @change="fetchAnalyticsData"
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
                                    <h3 class="text-h6 font-weight-black text-white">Financial Intelligence</h3>
                                    <p class="text-caption text-blue-lighten-4 opacity-70">AI-driven spending vectors
                                        and
                                        strategy</p>
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
                            <div v-else-if="generatingAI" class="ai-loading-state py-8">
                                <div class="premium-loader mb-4">
                                    <div class="loader-circle"></div>
                                    <Sparkles :size="32" class="loader-icon sparkles-animate" />
                                </div>
                                <div class="text-center">
                                    <p class="text-h6 font-weight-bold text-white mb-1">Synthesizing Strategy</p>
                                    <p class="text-caption text-blue-lighten-4 opacity-70">Correlating patterns from
                                        your
                                        spending vectors...</p>
                                </div>
                            </div>
                            <div v-else-if="aiError" class="ai-error-state text-center py-8 px-6">
                                <div class="error-glow-container mb-6 mx-auto">
                                    <v-icon :color="aiError.includes('Quota') ? 'warning' : 'error'" size="42"
                                        class="error-icon-animate">
                                        {{ aiError.includes('Quota') ? 'mdi-clock-outline' : 'mdi-shield-alert-outline'
                                        }}
                                    </v-icon>
                                </div>
                                <h4 class="text-h5 font-weight-black text-white mb-2">
                                    {{ aiError.includes('Quota') ? 'Quota Limit Reached' : 'Intelligence Paused' }}
                                </h4>
                                <p class="text-body-1 text-blue-lighten-4 opacity-80 mb-6 max-w-md mx-auto">
                                    {{ aiError }}
                                </p>
                                <div class="d-flex justify-center gap-3">
                                    <v-btn variant="flat" color="primary" rounded="xl" @click="generateAIInsights"
                                        class="text-none px-6">
                                        Retry Connection
                                    </v-btn>
                                    <v-btn variant="text" color="white" rounded="xl" to="/settings" class="text-none">
                                        AI Settings
                                    </v-btn>
                                </div>
                            </div>
                            <div v-else class="ai-empty-state text-center py-6">
                                <div class="brain-glow-container mb-4">
                                    <Brain :size="56" class="text-white brain-animate" />
                                </div>
                                <p class="text-h6 font-weight-black text-white mb-1">Analysis Ready</p>
                                <p class="text-body-2 text-blue-lighten-4 opacity-70">Ready to generate smart
                                    optimization tips
                                    based on your spending patterns.</p>
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
                <v-card rounded="xl" class="stat-glass-card stat-income h-100">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow income-glow mr-4">
                            <TrendingUp :size="28" class="text-success" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis letter-spacing-1">Total
                                Income</span>
                            <h2 class="text-h4 font-weight-black text-success mt-n1">{{
                                formatAmount(analyticsData.income || 0) }}
                            </h2>
                        </div>
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" md="4">
                <v-card rounded="xl" class="stat-glass-card stat-expense h-100">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow expense-glow mr-4">
                            <TrendingDown :size="28" class="text-error" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis letter-spacing-1">Total
                                Expenses</span>
                            <h2 class="text-h4 font-weight-black text-error mt-n1">{{
                                formatAmount(analyticsData.expense_total) }}
                            </h2>
                        </div>
                    </div>
                </v-card>
            </v-col>

            <v-col cols="12" md="4">
                <v-card rounded="xl" class="stat-glass-card stat-net h-100">
                    <div class="d-flex align-center pa-4">
                        <div class="stat-icon-glow net-glow mr-4">
                            <Scale :size="28" class="text-primary" />
                        </div>
                        <div>
                            <span class="text-overline font-weight-black text-medium-emphasis letter-spacing-1">Net
                                Savings</span>
                            <h2 class="text-h4 font-weight-black mt-n1"
                                :class="(analyticsData.net || 0) >= 0 ? 'text-primary' : 'text-error'">
                                {{ formatAmount(analyticsData.net || 0) }}
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
                                            <component :is="getCategoryLucideIcon(cat.name)" :size="16"
                                                class="text-primary" />
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
                        <div class="doughnut-chart-container relative-pos">
                            <BaseChart type="doughnut" :data="categoryChartData" :height="450" :options="{
                                cutout: '75%',
                                plugins: {
                                    legend: { display: false },
                                    polylineLabels: { display: true }
                                },
                                layout: {
                                    padding: { left: 160, right: 160, top: 30, bottom: 30 }
                                }
                            }" @chart-click="handleCategoryClick" />
                            <div class="chart-center-label">
                                <div class="text-overline font-weight-black opacity-60">TOTAL SPENT</div>
                                <div class="text-h6 font-weight-black">{{ formatAmount(analyticsData.expense_total) }}
                                </div>
                            </div>
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
                        <div class="analytics-chart-box">
                            <BaseChart type="bar" :data="merchantChartData" :height="450" :options="{
                                indexAxis: 'y',
                                plugins: {
                                    legend: { display: false },
                                    datalabels: {
                                        display: true,
                                        anchor: 'end',
                                        align: 'right',
                                        offset: 4,
                                        color: isDark ? '#ffffff' : '#0f172a',
                                        font: { weight: 'bold', size: 10 },
                                        formatter: (value: number) => formatAmount(value)
                                    }
                                },
                                layout: {
                                    padding: { left: 10, right: 60, top: 0, bottom: 0 }
                                },
                                scales: {
                                    x: {
                                        grid: { display: false },
                                        ticks: { display: false }
                                    },
                                    y: {
                                        grid: { display: false },
                                        ticks: {
                                            display: true,
                                            font: { size: 11, weight: 'bold' },
                                            color: isDark ? '#ffffff' : '#0f172a'
                                        }
                                    }
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
                            <v-btn-toggle v-model="trendView" mandatory density="comfortable" color="primary"
                                variant="tonal">
                                <v-btn value="daily" class="text-none">Daily</v-btn>
                                <v-btn value="monthly" class="text-none">Monthly</v-btn>
                            </v-btn-toggle>
                            <v-autocomplete v-model="selectedTrendCategory" :items="categoryOptions" item-title="title"
                                item-value="value" density="comfortable" variant="outlined" hide-details
                                class="trend-cat-premium" rounded="pill" menu-icon="" placeholder="Search Categories..."
                                style="background: rgba(var(--v-theme-surface), 0.7); width: 280px;">
                                <template v-slot:prepend-inner>
                                    <Filter :size="16" class="text-primary mr-1" />
                                </template>
                                <template v-slot:item="{ props, item }">
                                    <v-list-item v-bind="props" :title="item.raw.title">
                                        <template v-slot:prepend>
                                            <span class="mr-2"
                                                :style="{ paddingLeft: item.raw.isChild ? '16px' : '0' }">
                                                {{ item.raw.icon }}
                                            </span>
                                        </template>
                                        <template v-slot:title>
                                            <span
                                                :class="{ 'text-caption opacity-70': item.raw.isChild, 'font-weight-bold': !item.raw.isChild }">
                                                {{ item.raw.title }}
                                            </span>
                                        </template>
                                    </v-list-item>
                                </template>
                                <template v-slot:append-inner>
                                    <ChevronDown :size="16" class="text-primary opacity-70" />
                                </template>
                            </v-autocomplete>
                        </div>
                    </v-card-title>
                    <v-card-text class="pa-6">
                        <div class="large-chart-container">
                            <BaseChart v-if="filteredTrendData.length > 0" type="line" :data="trendChartData"
                                :height="400" />
                            <div v-else class="empty-state d-flex flex-column align-center justify-center h-100">
                                <BarChart2 :size="64" class="text-medium-emphasis" />
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
                        <div class="analytics-chart-box relative">
                            <BaseChart v-if="forecastData.length > 0" type="line" :data="forecastChartData"
                                :height="300" />
                            <div v-else class="d-flex items-center justify-center fill-height">Calculative Projection...
                            </div>
                        </div>
                        <v-alert density="comfortable" variant="tonal" type="info" class="mt-4 text-caption rounded-lg"
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
                                    <div class="heatmap-label-cell truncate">
                                        <component :is="getCategoryLucideIcon(cat)" :size="14"
                                            class="mr-2 text-primary opacity-70" />
                                        {{ cat }}
                                    </div>
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
import { localDateString } from '@/utils/time'
import { ref, onMounted, computed, watch } from 'vue'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { financeApi, aiApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import BaseChart from '@/components/BaseChart.vue'
import BudgetHistoryChart from '@/components/BudgetHistoryChart.vue'
import { marked } from 'marked'
import { useTheme } from 'vuetify'
import {
    TrendingUp, TrendingDown, Scale,
    CalendarRange, ArrowRight, RefreshCcw, Filter, BarChart2,
    ShieldAlert, Sparkles, Brain, ChevronDown
} from 'lucide-vue-next'
import { getCategoryLucideIcon } from '@/utils/iconMapping'

interface Props {
    selectedAccount?: string
}

const props = defineProps<Props>()

const store = useFinanceStore()
const authStore = useAuthStore()
const settings = useSettingsStore()
const theme = useTheme()
const { formatAmount } = useCurrency()

const isDark = computed(() => theme.global.current.value.dark)

// Filters local to analytics
const selectedTimeRange = ref('this-month')
const startDate = ref('')
const endDate = ref('')
const selectedTrendCategory = ref('')
const trendView = ref<'daily' | 'monthly'>('daily')

// Category Color Palette (if store colors are missing or identical)
const chartPalette = [
    '#3B82F6', // Blue
    '#10B981', // Emerald
    '#F59E0B', // Amber
    '#EF4444', // Red
    '#8B5CF6', // Violet
    '#EC4899', // Pink
    '#06B6D4', // Cyan
    '#F97316', // Orange
    '#6366F1', // Indigo
    '#14B8A6', // Teal
    '#F43F5E', // Rose
    '#84CC16', // Lime
    '#A855F7', // Purple
    '#0EA5E9', // Sky
    '#D946EF', // Fuchsia
    '#FACC15', // Yellow
    '#22C55E', // Green
    '#64748B', // Slate
    '#d97706', // Amber-600
    '#be123c', // Rose-700
    '#4338ca', // Indigo-700
    '#047857', // Emerald-700
    '#a21caf', // Fuchsia-700
    '#b91c1c'  // Red-700
]

function handleCategoryClick(payload: any) {
    if (payload && payload.label) {
        selectedTrendCategory.value = payload.label
        // Scroll to trend chart for better UX
        const trendEl = document.querySelector('.large-chart-container')
        if (trendEl) {
            trendEl.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }
    }
}

const timeRangeOptions = [
    { label: 'All Time', value: 'all' },
    { label: 'Today', value: 'today' },
    { label: 'This Week', value: 'this-week' },
    { label: 'This Month', value: 'this-month' },
    { label: 'Last Month', value: 'last-month' },
    { label: 'Custom Range', value: 'custom' }
]

// Data for Analytics

const analyticsData = ref<any>({
    income: 0,
    expense_total: 0,
    net: 0,
    categories: [],
    merchants: [],
    heatmap: { grid: {}, categories: [], hours: [], max: 0 },
    excludedExpense: 0,
    excludedIncome: 0,
    excludedCategories: [],
    accounts: [],
    types: [],
    credit: { limit: 0, consumed: 0, available: 0, percent: 0 },
    patterns: { weekend: 0, weekday: 0, weekendPercent: 0, weekdayPercent: 0 },
    count: 0
})
const forecastData = ref<any[]>([])
const budgets = ref<any[]>([])
const budgetHistory = ref<any[]>([])
const aiInsights = ref<string>('')
const aiError = ref<string | null>(null)
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
        startDate.value = localDateString(start.getFullYear(), start.getMonth(), start.getDate())
        endDate.value = localDateString(end.getFullYear(), end.getMonth(), end.getDate())
    } else if (val === 'this-week') {
        const day = now.getDay()
        const diff = now.getDate() - day + (day === 0 ? -6 : 1)
        start.setDate(diff)
        start.setHours(0, 0, 0, 0)
        startDate.value = localDateString(start.getFullYear(), start.getMonth(), start.getDate())
    } else if (val === 'this-month') {
        start.setDate(1)
        start.setHours(0, 0, 0, 0)
        startDate.value = localDateString(start.getFullYear(), start.getMonth(), start.getDate())
    } else if (val === 'last-month') {
        start.setMonth(start.getMonth() - 1)
        start.setDate(1)
        start.setHours(0, 0, 0, 0)
        end.setMonth(end.getMonth())
        end.setDate(0)
        end.setHours(23, 59, 59, 999)
        startDate.value = localDateString(start.getFullYear(), start.getMonth(), start.getDate())
        endDate.value = localDateString(end.getFullYear(), end.getMonth(), end.getDate())
    }

    fetchAnalyticsData()
}

// Re-fetch trend when category changes
watch(selectedTrendCategory, () => {
    fetchAnalyticsData()
})

async function fetchAnalyticsData() {
    loading.value = true
    try {
        const userId = authStore.selectedMemberId || undefined
        const params = {
            start_date: startDate.value,
            end_date: endDate.value,
            account_id: props.selectedAccount || undefined
        }

        const [detailedRes, forecastRes, budgetRes, historyRes] = await Promise.all([
            financeApi.getDetailedAnalytics(params.account_id, params.start_date || undefined, params.end_date || undefined, userId, selectedTrendCategory.value || undefined),
            financeApi.getForecast(params.account_id, 30, userId),
            financeApi.getBudgets(undefined, undefined, userId),
            financeApi.getBudgetHistory(6, userId)
        ])
        analyticsData.value = detailedRes.data
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
    aiError.value = null
    try {
        const timeContext = selectedTimeRange.value === 'custom'
            ? `from ${startDate.value} to ${endDate.value}`
            : `for ${selectedTimeRange.value.replace('-', ' ')}`

        const velocity = budgetHistory.value.length > 0 ? `Spending velocity is currently showing a ${overallBudget.value?.percentage > 80 ? 'HIGH' : 'STABLE'} trend relative to the monthly cycle.` : ''

        const promptData = {
            income: analyticsData.value.income,
            expense_total: analyticsData.value.expense_total,
            net: analyticsData.value.net,
            categories: analyticsData.value.categories,
            merchants: analyticsData.value.merchants,
            accounts: analyticsData.value.accounts,
            types: analyticsData.value.types,
            credit: analyticsData.value.credit,
            patterns: analyticsData.value.patterns,
            budgets: budgets.value.map((b: any) => ({
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
        if (res.data && res.data.insights) {
            aiInsights.value = res.data.insights
            aiError.value = null
        } else {
            console.warn("AI Response successful but missing data:", res.data)
            aiError.value = "AI reached (v2) but returned empty analysis. This usually means the model generated no content. Check settings."
        }
    } catch (e: any) {
        console.error("AI Insight Error:", e)
        const rawMsg = e.response?.data?.detail || e.message || ""

        // Final fallback Mapping
        if (rawMsg.includes("Quota") || rawMsg.includes("429") || rawMsg.includes("RESOURCE_EXHAUSTED")) {
            aiError.value = "Your API quota has been reached. Please try again in a few minutes or switch the model in settings."
        } else if (rawMsg.includes("Authentication") || rawMsg.includes("401") || rawMsg.includes("API Key")) {
            aiError.value = "Authentication failed. Please verify your Gemini API key in settings."
        } else if (rawMsg.length > 100) {
            // If message is too long or contains bits of code/json
            aiError.value = "The intelligence service is temporarily unavailable. This usually happens during high demand or config sync."
        } else {
            aiError.value = rawMsg || "Failed to connect to the intelligence service."
        }
    } finally {
        generatingAI.value = false
    }
}

const overallBudget = computed(() => budgets.value.find((b: any) => b.category === 'OVERALL'))


const categoryOptions = computed(() => {
    // Organize categories hierarchically
    const parents = store.categories.filter(c => !c.parent_id)
    const result: any[] = [{ title: 'All Spending', value: '', icon: '📊', isChild: false }]

    parents.sort((a, b) => a.name.localeCompare(b.name)).forEach(p => {
        result.push({ title: p.name, value: p.name, icon: p.icon || '🏷️', isChild: false })
        const children = store.categories.filter(c => c.parent_id === p.id)
        children.sort((a, b) => a.name.localeCompare(b.name)).forEach(c => {
            result.push({ title: c.name, value: c.name, icon: c.icon || '🔹', isChild: true })
        })
    })

    return result
})

const filteredTrendData = computed(() => {
    const trend = analyticsData.value.trend || []
    if (trendView.value === 'monthly') {
        const map: Record<string, number> = {}
        trend.forEach((d: any) => {
            const month = d.date.slice(0, 7)
            map[month] = (map[month] || 0) + d.amount
        })
        return Object.entries(map).sort((a, b) => a[0].localeCompare(b[0]))
            .map(([label, value]) => ({ label, value }))
    }
    return trend.map((d: any) => ({ label: d.date, value: d.amount }))
})

const trendChartData = computed(() => {
    const color = selectedTrendCategory.value ? store.getCategoryColor(selectedTrendCategory.value) : 'rgb(var(--v-theme-primary))'
    // Safely handle alpha for both hex and rgb(var)
    const bgColor = color.startsWith('#') ? color + '20' : color.replace('rgb(', 'rgba(').replace(')', ', 0.1)')

    return {
        labels: filteredTrendData.value.map((d: any) => trendView.value === 'daily' ? d.label.slice(5) : d.label),
        datasets: [{
            label: selectedTrendCategory.value || 'All Spending',
            data: filteredTrendData.value.map((d: any) => d.value / (settings.maskingFactor || 1)),
            borderColor: color,
            backgroundColor: bgColor,
            fill: true,
            tension: 0.4,
            pointRadius: 4,
            pointBackgroundColor: color
        }]
    }
})


const heatmapData = computed(() => {
    return analyticsData.value.heatmap
})

const merchantChartData = computed(() => ({
    labels: analyticsData.value.merchants?.map((m: any) => m.name) || [],
    datasets: [{
        label: 'Spending',
        data: analyticsData.value.merchants?.map((m: any) => m.value / (settings.maskingFactor || 1)) || [],
        backgroundColor: analyticsData.value.merchants?.map((_: any, i: number) => chartPalette[i % chartPalette.length]) || [],
        borderRadius: 6,
        borderSkipped: false,
    }]
}))

const categoryChartData = computed(() => ({
    labels: analyticsData.value.categories?.map((c: any) => c.name) || [],
    datasets: [{
        data: analyticsData.value.categories?.map((c: any) => c.value / (settings.maskingFactor || 1)) || [],
        backgroundColor: analyticsData.value.categories?.map((_: any, i: number) => chartPalette[i % chartPalette.length]) || [],
        hoverOffset: 12,
        borderWidth: 0
    }]
}))

const forecastChartData = computed(() => ({
    labels: forecastData.value.map((d: any) => d.date.split('T')[0].slice(5)),
    datasets: [{
        label: 'Projected Balance',
        data: forecastData.value.map((d: any) => d.balance / (settings.maskingFactor || 1)),
        borderColor: 'rgb(var(--v-theme-success))',
        backgroundColor: 'rgba(var(--v-theme-success), 0.1)',
        fill: true,
        tension: 0.3,
        pointRadius: 0
    }]
}))
</script>

<style scoped>
/* AI Premium Card */
.premium-ai-card {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, rgba(var(--v-theme-primary), 0.7) 100%);
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
    background: rgba(var(--v-theme-primary), 1);
    top: -100px;
    right: -100px;
}

.blob-purple {
    width: 250px;
    height: 250px;
    background: rgba(var(--v-theme-secondary), 1);
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
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 56px;
}

.income-glow {
    background: rgba(var(--v-theme-success), 0.1);
    box-shadow: 0 0 15px rgba(var(--v-theme-success), 0.2);
}

.expense-glow {
    background: rgba(var(--v-theme-error), 0.1);
    box-shadow: 0 0 15px rgba(var(--v-theme-error), 0.2);
}

.net-glow {
    background: rgba(var(--v-theme-primary), 0.1);
    box-shadow: 0 0 15px rgba(var(--v-theme-primary), 0.2);
}

/* Charts */
.analytics-chart-box {
    height: 450px;
    width: 100%;
    position: relative;
}

.doughnut-chart-container {
    height: 450px;
    /* Keeps extra space for polyline labels */
    width: 100%;
}

.relative-pos {
    position: relative;
}

.chart-center-label {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    pointer-events: none;
    z-index: 1;
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

/* Premium AI States */
.ai-loading-state,
.ai-error-state,
.ai-empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 200px;
}

.premium-loader {
    position: relative;
    width: 80px;
    height: 80px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.loader-circle {
    position: absolute;
    width: 100%;
    height: 100%;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: #fff;
    border-radius: 50%;
    animation: spin 1.5s cubic-bezier(0.68, -0.55, 0.265, 1.55) infinite;
}

.loader-icon {
    z-index: 1;
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.5));
}

.sparkles-animate {
    animation: pulse-glow 2s ease-in-out infinite;
}

.brain-animate {
    animation: brain-bounce 3s ease-in-out infinite;
}

.error-glow-icon {
    width: 64px;
    height: 64px;
    background: rgba(239, 68, 68, 0.2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.brain-glow-container {
    padding: 20px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 50%;
    box-shadow: 0 0 30px rgba(255, 255, 255, 0.1);
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

@keyframes pulse-glow {

    0%,
    100% {
        opacity: 0.7;
        transform: scale(0.9);
    }

    50% {
        opacity: 1;
        transform: scale(1.1);
        filter: drop-shadow(0 0 12px #fff);
    }
}

@keyframes brain-bounce {

    0%,
    100% {
        transform: translateY(0);
    }

    50% {
        transform: translateY(-10px);
    }
}

.error-glow-container {
    width: 80px;
    height: 80px;
    background: rgba(var(--v-theme-warning), 0.1);
    border-radius: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 1px solid rgba(var(--v-theme-warning), 0.2);
    box-shadow: 0 0 30px rgba(var(--v-theme-warning), 0.1);
}

.error-icon-animate {
    animation: icon-pulse 2s infinite ease-in-out;
}

@keyframes icon-pulse {

    0%,
    100% {
        transform: scale(1);
        opacity: 0.8;
    }

    50% {
        transform: scale(1.1);
        opacity: 1;
    }
}

.max-w-md {
    max-width: 450px;
}
</style>
