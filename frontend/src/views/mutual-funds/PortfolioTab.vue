<template>
    <div>
        <!-- AI Intelligence Card -->
        <v-card class="premium-glass-card mb-6" rounded="xl" elevation="0">
            <v-card-text class="d-flex flex-column flex-md-row justify-space-between align-center px-6 py-6 gap-4">
                <div class="d-flex align-start gap-4" style="max-width: 800px;">
                    <div class="text-h3">✨</div>
                    <div>
                        <h3 class="text-h6 font-weight-black text-content mb-1">Portfolio Intelligence</h3>
                        <div v-if="aiAnalysis" class="markdown-body text-body-2 text-medium-emphasis"
                            v-html="marked(aiAnalysis)"></div>
                        <div v-else-if="isAnalyzing" class="d-flex flex-column gap-2 mt-2" style="width: 300px;">
                            <v-skeleton-loader type="text" width="100%"></v-skeleton-loader>
                            <v-skeleton-loader type="text" width="70%"></v-skeleton-loader>
                        </div>
                        <div v-else class="text-body-2 text-medium-emphasis font-weight-medium">
                            Let AI analyze your asset allocation and sector exposure to suggest optimal rebalancing
                            strategies.
                        </div>
                    </div>
                </div>
                <v-btn variant="tonal" color="primary" rounded="lg" class="px-6 font-weight-bold" :loading="isAnalyzing"
                    @click="generateAIAnalysis">
                    <Sparkles :size="18" class="mr-2" />
                    {{ aiAnalysis ? 'Refresh Analysis' : 'Analyze Portfolio' }}
                </v-btn>
            </v-card-text>
        </v-card>

        <!-- Summary Cards -->
        <v-row class="mb-6">
            <!-- Loading Skeletons for Cards -->
            <template v-if="isLoading">
                <v-col cols="12" md="4" v-for="i in 3" :key="`skel-card-${i}`">
                    <PremiumSkeleton type="stat-card" glass />
                </v-col>
            </template>
            <!-- Actual Cards -->
            <template v-else>
                <v-col cols="12" md="4">
                    <v-card class="premium-glass-card h-100 pa-4" rounded="xl">
                        <div class="text-overline text-medium-emphasis font-weight-bold mb-1">Current Value</div>
                        <div class="text-h4 font-weight-black text-content mb-2">
                            {{ formatAmount(portfolioStats.current) }}
                        </div>
                        <v-chip size="small" :color="portfolioStats.pl >= 0 ? 'success' : 'error'" variant="tonal"
                            class="font-weight-bold">
                            {{ portfolioStats.pl >= 0 ? '↑' : '↓' }} {{ Math.abs(portfolioStats.plPercent).toFixed(2)
                            }}%
                            Returns
                        </v-chip>
                    </v-card>
                </v-col>
                <v-col cols="12" md="4">
                    <v-card class="premium-glass-card h-100 pa-4" rounded="xl">
                        <div class="text-overline text-medium-emphasis font-weight-bold mb-1">Total Invested</div>
                        <div class="text-h4 font-weight-black text-content mb-2">
                            {{ formatAmount(portfolioStats.invested) }}
                        </div>
                        <div class="text-caption text-medium-emphasis font-weight-bold">
                            Across {{ portfolio.length }} Funds
                        </div>
                    </v-card>
                </v-col>
                <v-col cols="12" md="4">
                    <v-card class="premium-glass-card h-100 pa-4" rounded="xl">
                        <div class="text-overline text-medium-emphasis font-weight-bold mb-1">Overall P&L</div>
                        <div class="text-h4 font-weight-black"
                            :class="portfolioStats.pl >= 0 ? 'text-success' : 'text-error'">
                            {{ portfolioStats.pl >= 0 ? '+' : '' }}{{ formatAmount(portfolioStats.pl) }}
                        </div>
                        <div class="text-caption text-medium-emphasis font-weight-bold" v-if="analytics?.xirr != null">
                            XIRR: <span :class="analytics.xirr >= 0 ? 'text-success' : 'text-error'">{{
                                analytics.xirr.toFixed(2) }}%</span>
                        </div>
                    </v-card>
                </v-col>
            </template>
        </v-row>

        <!-- Top Movers -->
        <v-row class="mb-6" v-if="topGainers.length || topLosers.length">
            <v-col cols="12" md="6" v-if="topGainers.length">
                <v-card class="premium-glass-card pa-4 h-100" rounded="xl">
                    <h4 class="text-subtitle-2 font-weight-bold text-success mb-3 d-flex align-center gap-2">
                        <TrendingUp :size="16" /> Top Gainers
                    </h4>
                    <div class="d-flex flex-column gap-3">
                        <div v-for="item in topGainers" :key="item.id"
                            class="d-flex justify-space-between align-center py-2 border-b-dashed">
                            <div class="d-flex flex-column" style="max-width: 70%;">
                                <span class="text-body-2 font-weight-bold text-truncate">{{ item.scheme_name }}</span>
                                <span class="text-caption text-medium-emphasis">{{ item.scheme_code }}</span>
                            </div>
                            <div class="text-right">
                                <div class="text-success font-weight-black text-body-2">+{{
                                    formatAmount(item.profit_loss) }}</div>
                                <div class="text-success text-caption font-weight-bold">
                                    {{ ((item.profit_loss / (item.invested_value || 1)) * 100).toFixed(2) }}%
                                </div>
                            </div>
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" md="6" v-if="topLosers.length">
                <v-card class="premium-glass-card pa-4 h-100" rounded="xl">
                    <h4 class="text-subtitle-2 font-weight-bold text-error mb-3 d-flex align-center gap-2">
                        <TrendingUp :size="16" class="rotate-180" /> Top Losers
                    </h4>
                    <div class="d-flex flex-column gap-3">
                        <div v-for="item in topLosers" :key="item.id"
                            class="d-flex justify-space-between align-center py-2 border-b-dashed">
                            <div class="d-flex flex-column" style="max-width: 70%;">
                                <span class="text-body-2 font-weight-bold text-truncate">{{ item.scheme_name }}</span>
                                <span class="text-caption text-medium-emphasis">{{ item.scheme_code }}</span>
                            </div>
                            <div class="text-right">
                                <div class="text-error font-weight-black text-body-2">{{ formatAmount(item.profit_loss)
                                }}</div>
                                <div class="text-error text-caption font-weight-bold">
                                    {{ ((item.profit_loss / (item.invested_value || 1)) * 100).toFixed(2) }}%
                                </div>
                            </div>
                        </div>
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Charts Section -->
        <v-row class="mb-6">
            <v-col cols="12" md="8">
                <v-card class="premium-glass-card h-100 pa-6" rounded="xl">
                    <div class="d-flex justify-space-between align-center mb-6">
                        <div class="d-flex align-center gap-2">
                            <TrendingUp :size="20" class="text-primary" />
                            <h3 class="text-h6 font-weight-black text-content">Portfolio Growth</h3>
                        </div>
                        <v-chip size="small" variant="tonal" color="primary" class="font-weight-bold">1 Year</v-chip>
                    </div>
                    <div style="height: 350px;">
                        <FundPerformanceChart v-if="lineChartData.length" :data="lineChartData"
                            :benchmark="benchmarkChartData" :height="350" />
                        <div v-else class="d-flex align-center justify-center h-100 text-medium-emphasis">
                            No performance history available
                        </div>
                    </div>
                </v-card>
            </v-col>
            <v-col cols="12" md="4">
                <v-card class="premium-glass-card h-100 pa-6" rounded="xl">
                    <div class="d-flex align-center gap-2 mb-6">
                        <PieChart :size="20" class="text-primary" />
                        <h3 class="text-h6 font-weight-black text-content">Asset Allocation</h3>
                    </div>
                    <div class="d-flex align-center justify-center h-100">
                        <DonutChart v-if="Object.keys(allocationData).length" :data="allocationData" :size="240"
                            legend-position="bottom" />
                        <div v-else class="text-medium-emphasis">No allocation data</div>
                    </div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Holdings Table -->
        <v-card class="premium-glass-card" rounded="xl">
            <div class="px-6 py-4 border-b d-flex justify-space-between align-center">
                <h3 class="text-h6 font-weight-black text-content">All Holdings</h3>
                <v-text-field v-model="search" density="comfortable" variant="outlined" hide-details
                    placeholder="Search funds..." style="max-width: 300px" class="glass-input">
                    <template v-slot:prepend-inner>
                        <Search :size="18" class="text-medium-emphasis mr-2" />
                    </template>
                </v-text-field>
            </div>

            <div v-if="isLoading" class="py-2">
                <div v-for="i in 5" :key="`skel-table-${i}`"
                    class="d-flex align-center px-6 py-4 border-b border-opacity-25 glass-loader-row">
                    <v-skeleton-loader type="avatar" size="32" class="mr-4 skeleton-glass"></v-skeleton-loader>
                    <div class="flex-grow-1 mr-4">
                        <v-skeleton-loader type="text" width="40%" class="mb-1 skeleton-glass"></v-skeleton-loader>
                        <v-skeleton-loader type="text" width="20%" height="12"
                            class="skeleton-glass"></v-skeleton-loader>
                    </div>
                    <v-skeleton-loader type="text" width="60px" class="mr-8 skeleton-glass"></v-skeleton-loader>
                    <v-skeleton-loader type="text" width="100px" class="skeleton-glass"></v-skeleton-loader>
                </div>
            </div>

            <v-data-table v-else :headers="headers" :items="sortedPortfolio" :search="search" hover
                class="premium-table bg-transparent" density="comfortable" item-value="id" v-model:expanded="expanded">
                <!-- Fund Name Column -->
                <template #[`item.scheme_name`]="{ item }">
                    <div class="d-flex align-center py-2">
                        <!-- Color Bar -->
                        <div class="mr-3 flex-shrink-0" style="width: 4px; height: 32px; border-radius: 4px;"
                            :style="{ background: getRandomColor(item.scheme_name) }"></div>

                        <!-- Expand/Collapse Button (or spacer) -->
                        <div class="mr-2 flex-shrink-0"
                            style="width: 24px; height: 24px; display: flex; align-items: center; justify-content: center;">
                            <v-btn v-if="item.has_multiple" icon density="compact" variant="text" size="24"
                                @click.stop="toggleGroup(item.id)">
                                <ChevronDown v-if="expanded.includes(item.id)" :size="16" />
                                <ChevronRight v-else :size="16" />
                            </v-btn>
                        </div>

                        <!-- Name & Details -->
                        <div>
                            <div class="font-weight-bold text-body-2 text-content">{{ item.scheme_name }}</div>
                            <div class="d-flex align-center gap-2 mt-1">
                                <v-chip size="x-small" label class="font-weight-bold">{{ item.scheme_code }}</v-chip>
                                <v-chip v-if="item.goal_id" color="success" size="x-small" variant="tonal"
                                    class="font-weight-bold">
                                    <Target :size="10" class="mr-1" /> Goal Linked
                                </v-chip>
                                <v-chip v-if="item.has_multiple" size="x-small" variant="outlined"
                                    class="text-medium-emphasis">
                                    {{ item.children.length }} Folios
                                </v-chip>
                            </div>
                        </div>
                    </div>
                </template>

                <!-- Numeric Columns -->
                <template #[`item.units`]="{ item }">
                    <span class="text-caption font-weight-medium">{{ item.units.toFixed(3) }}</span>
                </template>
                <template #[`item.average_price`]="{ item }">
                    <span class="text-caption font-weight-medium">{{ formatAmount(item.average_price) }}</span>
                </template>
                <template #[`item.last_nav`]="{ item }">
                    <span class="text-caption font-weight-medium">{{ formatAmount(item.last_nav) }}</span>
                </template>
                <template #[`item.invested_value`]="{ item }">
                    <span class="text-body-2 font-weight-bold text-medium-emphasis">{{ formatAmount(item.invested_value)
                        }}</span>
                </template>
                <template #[`item.current_value`]="{ item }">
                    <span class="text-body-2 font-weight-black text-content">{{ formatAmount(item.current_value)
                    }}</span>
                </template>

                <!-- Trend Column -->
                <template #[`item.trend`]="{ item }">
                    <Sparkline v-if="item.sparkline && item.sparkline.length" :data="item.sparkline"
                        :color="item.profit_loss >= 0 ? '#10b981' : '#ef4444'" :height="30" :width="100" />
                </template>

                <!-- Returns Column -->
                <template #[`item.profit_loss`]="{ item }">
                    <div class="d-flex flex-column align-end">
                        <span class="font-weight-black text-caption"
                            :class="item.profit_loss >= 0 ? 'text-success' : 'text-error'">
                            {{ item.profit_loss >= 0 ? '+' : '' }}{{ formatAmount(item.profit_loss) }}
                        </span>
                        <span class="font-weight-bold opacity-70" style="font-size: 10px">
                            {{ ((item.profit_loss / (item.invested_value || 1)) * 100).toFixed(2) }}%
                        </span>
                    </div>
                </template>

                <!-- Actions Column -->
                <template #[`item.actions`]="{ item }">
                    <div class="d-flex justify-end gap-1">
                        <v-btn icon variant="text" density="compact" color="primary"
                            @click="item.has_multiple ? $router.push(`/mutual-funds/${item.scheme_code}?type=aggregate`) : $router.push(`/mutual-funds/${item.id}`)">
                            <EyeIconMain :size="18" />
                            <v-tooltip activator="parent" location="top">View Details</v-tooltip>
                        </v-btn>
                        <v-btn icon variant="text" density="compact" :color="item.goal_id ? 'success' : 'secondary'"
                            @click="selectedHolding = item; showLinkGoalModal = true">
                            <Target :size="18" />
                            <v-tooltip activator="parent" location="top">
                                {{ item.goal_id ? 'Update Goal Link' : 'Link to Goal' }}
                            </v-tooltip>
                        </v-btn>
                    </div>
                </template>

                <!-- Expanded Row (Children / Folios) -->
                <template v-slot:expanded-row="{ columns, item }">
                    <td :colspan="columns.length" class="pa-0">
                        <v-sheet color="surface-light" class="pa-2 px-4">
                            <div class="d-flex align-center gap-2 mb-2">
                                <span class="text-caption font-weight-bold text-medium-emphasis text-uppercase ls-1"
                                    style="font-size: 0.65rem;">
                                    Folio Breakdown ({{ item.children.length }})
                                </span>
                                <v-divider class="border-opacity-25"></v-divider>
                            </div>

                            <v-row dense>
                                <v-col v-for="child in item.children" :key="child.id" cols="12" md="6" xl="4">
                                    <v-card variant="outlined"
                                        class="bg-surface border-thin border-primary border-opacity-50"
                                        density="compact">
                                        <v-card-text class="pa-2">
                                            <!-- Sub-Header: Folio & Tools -->
                                            <div class="d-flex justify-space-between align-start mb-2">
                                                <v-chip size="x-small" variant="tonal" color="secondary" label
                                                    class="font-weight-bold px-1"
                                                    style="height: 18px; font-size: 0.6rem;">
                                                    {{ child.folio_number || 'No Folio' }}
                                                </v-chip>
                                                <div class="d-flex gap-1" style="margin-top: -2px;">
                                                    <v-btn icon density="compact" variant="text" size="x-small"
                                                        :color="child.goal_id ? 'success' : 'medium-emphasis'"
                                                        @click="selectedHolding = child; showLinkGoalModal = true">
                                                        <Target :size="12" />
                                                    </v-btn>
                                                    <v-btn icon density="compact" variant="text" size="x-small"
                                                        color="primary" :to="`/mutual-funds/${child.id}`">
                                                        <EyeIconMain :size="12" />
                                                    </v-btn>
                                                </div>
                                            </div>

                                            <!-- Key Data Points -->
                                            <v-row dense no-gutters class="mb-2">
                                                <v-col cols="4">
                                                    <div
                                                        class="text-[9px] text-medium-emphasis font-weight-bold text-uppercase">
                                                        Invested</div>
                                                    <div class="text-caption font-weight-bold">{{
                                                        formatAmount(child.invested_value) }}</div>
                                                </v-col>
                                                <v-col cols="4">
                                                    <div
                                                        class="text-[9px] text-medium-emphasis font-weight-bold text-uppercase">
                                                        Current</div>
                                                    <div class="text-caption font-weight-black">{{
                                                        formatAmount(child.current_value) }}</div>
                                                </v-col>
                                                <v-col cols="4" class="text-right">
                                                    <div
                                                        class="text-[9px] text-medium-emphasis font-weight-bold text-uppercase">
                                                        Returns</div>
                                                    <div class="text-caption font-weight-bold"
                                                        :class="child.profit_loss >= 0 ? 'text-success' : 'text-error'">
                                                        {{ child.profit_loss >= 0 ? '+' : '' }}{{
                                                            formatAmount(child.profit_loss) }}
                                                    </div>
                                                </v-col>
                                            </v-row>

                                            <!-- Performance & Units Footer -->
                                            <div
                                                class="d-flex align-end justify-space-between pt-1 border-t border-dashed border-opacity-25">
                                                <div class="d-flex flex-column" style="width: 70px;">
                                                    <span
                                                        class="text-[8px] text-medium-emphasis mb-0.5 font-weight-bold">PERFORMANCE</span>
                                                    <Sparkline v-if="child.sparkline && child.sparkline.length"
                                                        :data="child.sparkline"
                                                        :color="child.profit_loss >= 0 ? '#10b981' : '#ef4444'"
                                                        :height="12" :width="70" stroke-width="3" />
                                                </div>
                                                <div class="text-right">
                                                    <div class="text-[8px] text-medium-emphasis font-weight-bold">UNITS
                                                    </div>
                                                    <div class="text-caption font-weight-medium"
                                                        style="font-size: 0.7rem;">{{ child.units.toFixed(3) }}</div>
                                                </div>
                                            </div>
                                        </v-card-text>
                                    </v-card>
                                </v-col>
                            </v-row>
                        </v-sheet>
                    </td>
                </template>
            </v-data-table>
        </v-card>
        <!-- Modals -->
        <LinkGoalModal v-model="showLinkGoalModal" :holding="selectedHolding" @saved="fetchPortfolio" />
    </div>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useMutualFundStore } from '@/stores/finance/mutualFunds'
import {
    Sparkles, Eye as EyeIconMain, ChevronDown, ChevronRight, Target, PieChart, TrendingUp, Search
} from 'lucide-vue-next'
import DonutChart from '@/components/DonutChart.vue'
import FundPerformanceChart from './components/FundPerformanceChart.vue'
import Sparkline from '@/components/Sparkline.vue'
import LinkGoalModal from './modals/LinkGoalModal.vue'
import PremiumSkeleton from '@/components/common/PremiumSkeleton.vue'
import { marked } from 'marked'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
    active: boolean
}>()

const mfStore = useMutualFundStore()
const authStore = useAuthStore()
const { formatAmount } = useCurrency()

// State - seed from store cache if available
const portfolio = ref<any[]>(mfStore.portfolio || [])
const isLoading = ref(mfStore.portfolio.length === 0)
const analytics = ref<any>(mfStore.analytics)
const aiAnalysis = ref(mfStore.aiAnalysis || '')
const isAnalyzing = ref(false)
const performanceHistory = ref<any[]>([])
const search = ref('')
const expanded = ref<string[]>([])

// Headers
const headers = [
    { title: 'Fund Name', key: 'scheme_name', align: 'start' },
    { title: 'Units', key: 'units', align: 'end' },
    { title: 'Avg Price', key: 'average_price', align: 'end' },
    { title: 'NAV', key: 'last_nav', align: 'end' },
    { title: 'Invested', key: 'invested_value', align: 'end' },
    { title: 'Current', key: 'current_value', align: 'end' },
    { title: 'Trend', key: 'trend', align: 'end', sortable: false },
    { title: 'Returns', key: 'profit_loss', align: 'end' },
    { title: 'Actions', key: 'actions', align: 'end', sortable: false },
] as any[]

// Modals
const showLinkGoalModal = ref(false)
const selectedHolding = ref<any>(null)

// --- Computed ---

const portfolioStats = computed(() => {
    if (!portfolio.value.length) return { invested: 0, current: 0, pl: 0, plPercent: 0 }
    const totalInvested = portfolio.value.reduce((sum, item) => sum + (Number(item.invested_value) || 0), 0)
    const totalCurrent = portfolio.value.reduce((sum, item) => sum + (Number(item.current_value) || 0), 0)
    const totalPL = totalCurrent - totalInvested
    const plPercent = totalInvested ? (totalPL / totalInvested) * 100 : 0
    return {
        invested: totalInvested,
        current: totalCurrent,
        pl: totalPL,
        plPercent
    }
})

const sortedPortfolio = computed(() => {
    // 1. Group items
    const groups: Record<string, any> = {}
    portfolio.value.forEach(item => {
        const code = item.scheme_code
        if (!groups[code]) groups[code] = []
        groups[code].push(item)
    })

    const result: any[] = []
    Object.keys(groups).forEach(code => {
        const items = groups[code]
        if (items.length > 1) {
            const totalInvested = items.reduce((s: number, i: any) => s + Number(i.invested_value), 0)
            const totalCurrent = items.reduce((s: number, i: any) => s + Number(i.current_value), 0)
            const totalUnits = items.reduce((s: number, i: any) => s + Number(i.units), 0)
            const pl = totalCurrent - totalInvested

            result.push({
                id: `group-${code}`,
                scheme_code: code,
                scheme_name: items[0].scheme_name,
                invested_value: totalInvested,
                current_value: totalCurrent,
                profit_loss: pl,
                units: totalUnits,
                average_price: totalInvested / totalUnits,
                last_nav: items[0].last_nav,
                has_multiple: true,
                children: items,
                sparkline: items[0].sparkline, // Use first child's sparkline for group
                goal_id: items.some((i: any) => i.goal_id) ? items[0].goal_id : null
            })
        } else {
            result.push({ ...items[0], has_multiple: false })
        }
    })
    return result
})

const topGainers = computed(() => {
    return sortedPortfolio.value
        .filter(i => i.profit_loss > 0)
        .sort((a, b) => b.profit_loss - a.profit_loss)
        .slice(0, 3)
})

const topLosers = computed(() => {
    return sortedPortfolio.value
        .filter(i => i.profit_loss < 0)
        .sort((a, b) => a.profit_loss - b.profit_loss)
        .slice(0, 3)
})

const benchmarkHistory = ref<any[]>([])

// Chart Data
const allocationData = computed(() => {
    const data: Record<string, number> = {}
    portfolio.value.forEach(item => {
        const key = item.category || 'Other'
        data[key] = (data[key] || 0) + (Number(item.current_value) || 0)
    })
    return data
})


const lineChartData = computed(() => {
    if (!performanceHistory.value || !Array.isArray(performanceHistory.value)) return []
    try {
        return performanceHistory.value.map((h: any) => ({
            date: h.date,
            value: Number(h.value) || 0,
            invested: Number(h.invested) || 0
        })).filter(d => !isNaN(d.value) && !isNaN(d.invested) && d.date)
    } catch (e) {
        console.error("Error parsing chart data", e)
        return []
    }
})

const benchmarkChartData = computed(() => {
    if (!benchmarkHistory.value || !Array.isArray(benchmarkHistory.value)) return []
    try {
        return benchmarkHistory.value.map((b: any) => ({
            date: b.date,
            value: Number(b.value) || 0
        }))
    } catch (e) {
        return []
    }
})

// --- Actions ---

async function fetchPortfolio() {
    if (portfolio.value.length === 0) isLoading.value = true
    try {
        const memberId = authStore.selectedMemberId || undefined
        const response = await financeApi.getPortfolio(memberId)
        portfolio.value = response.data || []
        mfStore.portfolio = portfolio.value // Persist
    } catch (err) {
        console.error('Failed to fetch portfolio', err)
    } finally {
        isLoading.value = false
    }
}

async function fetchAnalytics() {
    if (portfolio.value.length === 0) return
    try {
        const memberId = authStore.selectedMemberId || undefined
        const [analyticsRes, perfRes] = await Promise.all([
            financeApi.getAnalytics(memberId),
            financeApi.getPerformanceTimeline('1y', '1w', memberId)
        ])
        analytics.value = analyticsRes.data
        mfStore.analytics = analyticsRes.data // Persist

        const perfData = perfRes.data || {}
        if (perfData.timeline && Array.isArray(perfData.timeline)) {
            performanceHistory.value = perfData.timeline
            benchmarkHistory.value = perfData.benchmark || []
        } else if (Array.isArray(perfData)) {
            performanceHistory.value = perfData
            benchmarkHistory.value = []
        } else {
            performanceHistory.value = []
            benchmarkHistory.value = []
        }
    } catch (e) {
        console.error(e)
        performanceHistory.value = []
        benchmarkHistory.value = []
    }
}

async function generateAIAnalysis() {
    isAnalyzing.value = true
    try {
        const memberId = authStore.selectedMemberId || undefined
        const res = await financeApi.getPortfolioInsights(memberId)
        aiAnalysis.value = res.data.insights
        mfStore.aiAnalysis = aiAnalysis.value // Persist
    } catch (e) { console.error(e) } finally { isAnalyzing.value = false }
}

function toggleGroup(id: string) {
    const index = expanded.value.indexOf(id)
    if (index !== -1) {
        expanded.value.splice(index, 1)
    } else {
        expanded.value.push(id)
    }
}

function getRandomColor(name: string) {
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    let hash = 0
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
}

// Watchers
watch(() => authStore.selectedMemberId, async () => {
    analytics.value = null
    aiAnalysis.value = ''
    await fetchPortfolio()
    fetchAnalytics()
})

watch(() => props.active, async (isActive) => {
    if (isActive) {
        await fetchPortfolio()
        fetchAnalytics()
    }
}, { immediate: true })

const emit = defineEmits(['update:count'])
watch(portfolio, () => {
    emit('update:count', portfolio.value.length)
})
</script>

<style scoped>
/* Skeleton Loader Config */
.skeleton-glass {
    background: transparent !important;
}

.skeleton-glass :deep(.v-skeleton-loader__bone) {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
    border-radius: 8px;
}

.glass-loader-row {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: .5;
    }
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    box-shadow: none !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-table {
    background: transparent !important;
}

/* Custom Table Styles override */
:deep(.v-data-table) {
    background: transparent !important;
}

:deep(.v-data-table-header__content) {
    font-weight: 800;
    text-transform: uppercase;
    font-size: 0.7rem;
    color: rgba(var(--v-theme-on-surface), 0.5);
}

.hover-bg-surface-variant:hover {
    background-color: rgba(var(--v-theme-on-surface), 0.03);
}

.rotate-180 {
    transform: rotate(180deg);
}

.glass-input :deep(.v-field__outline__start),
.glass-input :deep(.v-field__outline__end) {
    border-color: rgba(var(--v-border-color), 0.2);
}
</style>
