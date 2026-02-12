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
            <v-col cols="12" md="4">
                <v-card class="premium-glass-card h-100 pa-4" rounded="xl">
                    <div class="text-overline text-medium-emphasis font-weight-bold mb-1">Current Value</div>
                    <div class="text-h4 font-weight-black text-content mb-2">
                        {{ formatAmount(portfolioStats.current) }}
                    </div>
                    <v-chip size="small" :color="portfolioStats.pl >= 0 ? 'success' : 'error'" variant="tonal"
                        class="font-weight-bold">
                        {{ portfolioStats.pl >= 0 ? '↑' : '↓' }} {{ Math.abs(portfolioStats.plPercent).toFixed(2) }}%
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
            </div>

            <div class="overflow-x-auto">
                <table class="w-100 premium-table">
                    <thead>
                        <tr>
                            <th class="text-left cursor-pointer" @click="handleSort('scheme_name')">Fund Name</th>
                            <th class="text-right cursor-pointer" @click="handleSort('units')">Units</th>
                            <th class="text-right cursor-pointer" @click="handleSort('average_price')">Avg Price</th>
                            <th class="text-right cursor-pointer" @click="handleSort('last_nav')">NAV</th>
                            <th class="text-right cursor-pointer" @click="handleSort('invested_value')">Invested</th>
                            <th class="text-right cursor-pointer" @click="handleSort('current_value')">Current</th>
                            <th class="text-right px-4" style="width: 120px;">Trend</th>
                            <th class="text-right cursor-pointer" @click="handleSort('profit_loss')">Returns</th>
                            <th class="text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <template v-for="item in sortedPortfolio" :key="item.id">
                            <tr class="hover-bg-surface-variant transition-colors"
                                :class="{ 'bg-active': expandedGroups.has(item.id) }">
                                <td class="py-3 px-4">
                                    <div class="d-flex align-center">
                                        <div class="mr-2" style="width: 4px; height: 32px; border-radius: 4px;"
                                            :style="{ background: getRandomColor(item.scheme_name) }"></div>

                                        <v-btn icon density="compact" variant="text" size="24" v-if="item.has_multiple"
                                            @click.stop="toggleGroup(item.id)" class="mr-2">
                                            <ChevronDown v-if="expandedGroups.has(item.id)" :size="16" />
                                            <ChevronRight v-else :size="16" />
                                        </v-btn>

                                        <div>
                                            <div class="font-weight-bold text-body-2 text-content">{{ item.scheme_name
                                                }}</div>
                                            <div class="d-flex align-center gap-2 mt-1">
                                                <v-chip size="x-small" label class="font-weight-bold">{{
                                                    item.scheme_code }}</v-chip>
                                                <v-chip v-if="item.goal_id" color="success" size="x-small"
                                                    variant="tonal" class="font-weight-bold">
                                                    <Target :size="10" class="mr-1" /> Goal Linked
                                                </v-chip>
                                            </div>
                                        </div>
                                    </div>
                                </td>
                                <td class="text-right font-weight-medium text-caption">{{ item.units.toFixed(3) }}</td>
                                <td class="text-right font-weight-medium text-caption">{{
                                    formatAmount(item.average_price) }}</td>
                                <td class="text-right font-weight-medium text-caption">{{ formatAmount(item.last_nav) }}
                                </td>
                                <td class="text-right font-weight-bold text-body-2 text-medium-emphasis">{{
                                    formatAmount(item.invested_value) }}</td>
                                <td class="text-right font-weight-black text-body-2 text-content">{{
                                    formatAmount(item.current_value) }}</td>
                                <td class="text-right px-4">
                                    <Sparkline v-if="item.sparkline && item.sparkline.length" :data="item.sparkline"
                                        :color="item.profit_loss >= 0 ? '#10b981' : '#ef4444'" :height="30" />
                                </td>
                                <td class="text-right">
                                    <div class="d-flex flex-column align-end">
                                        <span class="font-weight-black text-caption"
                                            :class="item.profit_loss >= 0 ? 'text-success' : 'text-error'">
                                            {{ item.profit_loss >= 0 ? '+' : '' }}{{ formatAmount(item.profit_loss) }}
                                        </span>
                                        <span class="text-[10px] font-weight-bold opacity-70">
                                            {{ ((item.profit_loss / (item.invested_value || 1)) * 100).toFixed(2) }}%
                                        </span>
                                    </div>
                                </td>
                                <td class="text-right px-4">
                                    <div class="d-flex justify-end gap-1">
                                        <v-btn icon variant="text" density="compact" color="primary"
                                            @click="item.has_multiple ? $router.push(`/mutual-funds/${item.scheme_code}?type=aggregate`) : $router.push(`/mutual-funds/${item.id}`)">
                                            <EyeIconMain :size="18" />
                                            <v-tooltip activator="parent" location="top">View Details</v-tooltip>
                                        </v-btn>
                                        <v-btn icon variant="text" density="compact"
                                            :color="item.goal_id ? 'success' : 'secondary'"
                                            @click="selectedHolding = item; showLinkGoalModal = true">
                                            <Target :size="18" />
                                            <v-tooltip activator="parent" location="top">
                                                {{ item.goal_id ? 'Update Goal Link' : 'Link to Goal' }}
                                            </v-tooltip>
                                        </v-btn>
                                    </div>
                                </td>
                            </tr>

                            <!-- Nested Rows -->
                            <template v-if="item.has_multiple && expandedGroups.has(item.id)">
                                <tr v-for="child in item.children" :key="child.id"
                                    class="bg-surface-variant bg-opacity-5">
                                    <td class="pl-12 py-2">
                                        <div
                                            class="d-flex align-center text-caption text-medium-emphasis font-weight-medium">
                                            <div class="mr-2 px-2 py-0.5 border rounded bg-surface">
                                                {{ child.folio_number || 'No Folio' }}
                                            </div>
                                        </div>
                                    </td>
                                    <td class="text-right text-caption text-medium-emphasis">{{ child.units.toFixed(3)
                                        }}</td>
                                    <td class="text-right text-caption text-medium-emphasis">{{
                                        formatAmount(child.average_price) }}</td>
                                    <td class="text-right text-caption text-medium-emphasis">{{
                                        formatAmount(child.last_nav) }}</td>
                                    <td class="text-right text-caption text-medium-emphasis">{{
                                        formatAmount(child.invested_value) }}</td>
                                    <td class="text-right text-caption text-content font-weight-bold">{{
                                        formatAmount(child.current_value) }}</td>
                                    <td class="text-right px-4">
                                        <Sparkline v-if="child.sparkline && child.sparkline.length"
                                            :data="child.sparkline"
                                            :color="child.profit_loss >= 0 ? '#10b981' : '#ef4444'" :height="20" />
                                    </td>
                                    <td class="text-right text-caption"
                                        :class="child.profit_loss >= 0 ? 'text-success' : 'text-error'">
                                        {{ formatAmount(child.profit_loss) }}
                                    </td>
                                    <td class="text-right px-4">
                                        <div class="d-flex justify-end gap-1">
                                            <v-btn icon variant="text" density="compact" color="primary" size="small"
                                                :to="`/mutual-funds/${child.id}`">
                                                <EyeIconMain :size="14" />
                                            </v-btn>
                                            <v-btn icon variant="text" density="compact"
                                                :color="child.goal_id ? 'success' : 'secondary'" size="small"
                                                @click="selectedHolding = child; showLinkGoalModal = true">
                                                <Target :size="14" />
                                                <v-tooltip activator="parent" location="top">
                                                    {{ child.goal_id ? 'Update Goal Link' : 'Link to Goal' }}
                                                </v-tooltip>
                                            </v-btn>
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </template>

                        <tr v-if="portfolio.length === 0 && !isLoading">
                            <td colspan="8" class="text-center py-8 text-medium-emphasis">
                                <div class="text-h6 mb-2">No investments found</div>
                                <div class="text-caption">Use the Search tab to add funds or Import your CAS</div>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </v-card>

        <LinkGoalModal v-if="showLinkGoalModal" v-model="showLinkGoalModal" :holding="selectedHolding"
            @success="fetchPortfolio" />
    </div>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import {
    Sparkles, Eye as EyeIconMain, ChevronDown, ChevronRight, Target, PieChart, TrendingUp
} from 'lucide-vue-next'
import DonutChart from '@/components/DonutChart.vue'
import FundPerformanceChart from './components/FundPerformanceChart.vue'
import Sparkline from '@/components/Sparkline.vue'
import LinkGoalModal from './modals/LinkGoalModal.vue'
import { marked } from 'marked'
import { useCurrency } from '@/composables/useCurrency'

// Note: Ensure useCurrency is available or copy formatAmount logic

const props = defineProps<{
    active: boolean
}>()

const authStore = useAuthStore()
const { formatAmount } = useCurrency()

// State
const portfolio = ref<any[]>([])
const isLoading = ref(true)
const analytics = ref<any>(null)
const aiAnalysis = ref('')
const isAnalyzing = ref(false)
const performanceHistory = ref<any[]>([])

// Sorting
const sortKey = ref('current_value')
const sortDesc = ref(true)

// Grouping
const expandedGroups = ref(new Set<string>())

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
                goal_id: items.some((i: any) => i.goal_id) ? items[0].goal_id : null // Simplified goal check
            })
        } else {
            result.push({ ...items[0], has_multiple: false })
        }
    })

    // 2. Sort
    return result.sort((a, b) => {
        let valA = a[sortKey.value]
        let valB = b[sortKey.value]
        if (typeof valA === 'string') {
            valA = valA.toLowerCase()
            valB = valB.toLowerCase()
        }
        if (valA < valB) return sortDesc.value ? 1 : -1
        if (valA > valB) return sortDesc.value ? -1 : 1
        return 0
    })
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
    isLoading.value = true
    try {
        const memberId = authStore.selectedMemberId || undefined
        const response = await financeApi.getPortfolio(memberId)
        portfolio.value = response.data || []
        // Emit count to parent if needed
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

        // Handle structured response { timeline: [], benchmark: [], ... }
        const perfData = perfRes.data || {}
        if (perfData.timeline && Array.isArray(perfData.timeline)) {
            performanceHistory.value = perfData.timeline
            benchmarkHistory.value = perfData.benchmark || []
        } else if (Array.isArray(perfData)) {
            // Fallback for legacy generic array response
            performanceHistory.value = perfData
            benchmarkHistory.value = []
        } else {
            performanceHistory.value = []
            benchmarkHistory.value = []
        }
    } catch (e) {
        console.error(e)
        // Fallback or empty state
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
    } catch (e) { console.error(e) } finally { isAnalyzing.value = false }
}

function toggleGroup(id: string) {
    if (expandedGroups.value.has(id)) expandedGroups.value.delete(id)
    else expandedGroups.value.add(id)
}

function handleSort(key: string) {
    if (sortKey.value === key) sortDesc.value = !sortDesc.value
    else {
        sortKey.value = key
        sortDesc.value = true
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
    if (isActive && !portfolio.value.length) {
        await fetchPortfolio()
        fetchAnalytics()
    }
}, { immediate: true })



// Expose portfolio count to parent? 
// We can use a store or emit event, but for now parent can duplicate fetch or we keep it simple.
// Actually, parent header shows count. Maybe standard pattern is store.
// Let's assume parent just passes props or we emit.
const emit = defineEmits(['update:count'])
watch(portfolio, () => {
    emit('update:count', portfolio.value.length)
})
</script>

<style scoped>
/* Scoped styles mainly for table since glass card is global/utility usually, 
   but duplicating here to ensure self-contained */

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    box-shadow: none !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-table {
    border-collapse: collapse;
    width: 100%;
}

.premium-table th {
    padding: 12px 16px;
    font-size: 0.75rem;
    font-weight: 700;
    text-transform: uppercase;
    color: rgba(var(--v-theme-on-surface), 0.5);
    border-bottom: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-table td {
    padding: 12px 16px;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.hover-bg-surface-variant:hover {
    background-color: rgba(var(--v-theme-on-surface), 0.03);
}

.border-b-dashed {
    border-bottom: 1px dashed rgba(var(--v-border-color), 0.15);
}

.border-b-dashed:last-child {
    border-bottom: none;
}

.rotate-180 {
    transform: rotate(180deg);
}
</style>
