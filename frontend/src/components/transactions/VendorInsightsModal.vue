<template>
    <v-dialog v-model="internalValue" max-width="480" scrollable>
        <v-card class="premium-glass-card rounded-xl border-none overflow-hidden" elevation="24">
            <!-- Sleek Header -->
            <v-card-title class="pa-5 pb-3 d-flex align-center justify-space-between bg-surface bg-opacity-70 backdrop-blur">
                <div class="d-flex align-center">
                    <v-avatar color="primary" variant="tonal" class="mr-3" size="44">
                        <v-icon size="24" color="primary" :icon="getVendorMdiIcon(vendorName)"></v-icon>
                    </v-avatar>
                    <div>
                        <div class="text-subtitle-1 font-weight-black d-flex align-center gap-1">
                            {{ vendorName }}
                            <v-icon size="16" color="primary">mdi-check-decagram-outline</v-icon>
                        </div>
                        <div class="text-caption font-weight-bold opacity-60 uppercase letter-spacing-1">Verified Merchant</div>
                    </div>
                </div>
                <v-btn icon="$close" variant="text" size="small" density="comfortable" @click="internalValue = false"></v-btn>
            </v-card-title>

            <v-card-text class="pa-5 pt-2">
                <!-- Loading State -->
                <div v-if="loading" class="text-center py-12">
                    <v-progress-circular indeterminate color="primary" size="40" width="3"></v-progress-circular>
                    <p class="mt-4 text-caption font-weight-bold opacity-50">Analyzing spending patterns...</p>
                </div>

                <!-- Content Area -->
                <div v-else-if="stats" class="vendor-stats-content">
                    <!-- Chart Hero Section - Premium Look with Tooltips -->
                    <v-tooltip location="top" activator="parent" :disabled="!hoverValue">
                        <template v-slot:default>
                            <div class="pa-2 text-center">
                                <div class="text-overline font-weight-black opacity-70 mb-n1">{{ hoverMonth }}</div>
                                <div class="text-subtitle-1 font-weight-black">{{ formatAmount(hoverValue) }}</div>
                            </div>
                        </template>
                    </v-tooltip>

                    <v-card 
                        variant="flat" 
                        rounded="xl" 
                        class="mb-6 pa-5 text-white chart-gradient relative-pos overflow-hidden cursor-crosshair"
                        @mousemove="onChartHover"
                        @mouseleave="hoverValue = 0"
                    >
                        <div class="d-flex align-center justify-space-between mb-4 relative-pos z-10 op-80">
                            <div class="d-flex align-center">
                                <v-icon size="16" icon="TrendingUp" class="mr-2"></v-icon>
                                <span class="text-caption font-weight-black uppercase letter-spacing-1">Spending Dynamics</span>
                            </div>
                            <v-chip size="x-small" color="white" variant="tonal" class="font-weight-black">6 MONTHS</v-chip>
                        </div>
                        
                        <v-sparkline
                            :model-value="chartPoints"
                            :labels="chartLabels"
                            color="white"
                            height="120"
                            padding="32"
                            stroke-linecap="round"
                            smooth
                            auto-draw
                            line-width="2"
                            label-size="5"
                            class="relative-pos z-10"
                        ></v-sparkline>
                        
                        <!-- Decorative background light -->
                        <div class="chart-glow"></div>
                    </v-card>

                    <!-- Key Metrics - Tonal Cards -->
                    <v-row no-gutters class="ga-3 mb-8">
                        <v-col v-for="stat in statCards" :key="stat.label">
                            <v-card variant="tonal" :color="stat.color" class="pa-3 text-center rounded-xl border-opacity-10 h-100">
                                <div class="text-overline font-weight-black opacity-70 mb-1 uppercase letter-spacing-1 line-height-1">
                                    {{ stat.label }}
                                </div>
                                <div class="text-subtitle-1 font-weight-black line-height-1">{{ stat.value }}</div>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- Recent Activity -->
                    <div>
                        <div class="d-flex align-center justify-space-between mb-4 px-1">
                            <div class="d-flex align-center">
                                <v-icon size="16" color="primary" class="mr-2" icon="History"></v-icon>
                                <span class="text-subtitle-2 font-weight-black">Recent History</span>
                            </div>
                            <span class="text-caption font-weight-black opacity-40 uppercase">{{ stats.transaction_count }} Total</span>
                        </div>
                        
                        <v-list class="pa-0 bg-transparent" density="comfortable">
                            <v-list-item 
                                v-for="txn in stats.recent_transactions" 
                                :key="txn.id" 
                                class="px-2 rounded-xl py-3 mb-2 border border-opacity-5 glass-list-item shadow-sm"
                            >
                                <template v-slot:prepend>
                                    <v-avatar size="38" :color="getCategoryDisplay(txn.category).color + '15'" class="mr-3">
                                        <span class="text-subtitle-1">{{ getCategoryDisplay(txn.category).icon }}</span>
                                    </v-avatar>
                                </template>

                                <v-list-item-title class="text-body-2 font-weight-black">{{ txn.description }}</v-list-item-title>
                                <v-list-item-subtitle class="text-caption font-weight-bold opacity-50">
                                    {{ formatDate(txn.date).day }}
                                </v-list-item-subtitle>
                                
                                <template v-slot:append>
                                    <div class="text-body-2 font-weight-black" :class="txn.amount > 0 ? 'text-success' : 'opacity-90'">
                                        {{ txn.amount > 0 ? '+' : '' }}{{ formatAmount(Math.abs(txn.amount)) }}
                                    </div>
                                </template>
                            </v-list-item>
                        </v-list>

                        <!-- Paginator -->
                        <div v-if="totalPages > 1" class="mt-4 d-flex justify-center">
                            <v-pagination
                                v-model="page"
                                :length="totalPages"
                                rounded="circle"
                                density="comfortable"
                                size="small"
                                color="primary"
                                variant="tonal"
                                :total-visible="5"
                                @update:model-value="fetchStats"
                            ></v-pagination>
                        </div>
                    </div>
                </div>

                <!-- Empty State -->
                <div v-else class="text-center py-16 opacity-30">
                    <v-icon size="48" icon="Database"></v-icon>
                    <p class="font-weight-black mt-2">No transaction data available.</p>
                </div>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useTransactionHelpers } from '@/composables/useTransactionHelpers'
import { useFinanceStore } from '@/stores/finance'
import { useExpenseGroupStore } from '@/stores/expenseGroups'

const props = defineProps<{
    modelValue: boolean
    vendorName: string
}>()

const emit = defineEmits(['update:modelValue'])

const financeStore = useFinanceStore()
const expenseGroupStore = useExpenseGroupStore()

const { formatAmount } = useCurrency()
const { formatDate, getCategoryDisplay } = useTransactionHelpers(
    computed(() => financeStore.accounts),
    computed(() => financeStore.categories),
    computed(() => expenseGroupStore.groups)
)

const internalValue = computed({
    get: () => props.modelValue,
    set: (val) => emit('update:modelValue', val)
})

const stats = ref<any>(null)
const loading = ref(false)
const page = ref(1)
const pageSize = 3

const hoverValue = ref(0)
const hoverMonth = ref('')

const totalPages = computed(() => {
    if (!stats.value?.transaction_count) return 0
    return Math.ceil(stats.value.transaction_count / pageSize)
})

const chartPoints = computed(() => {
    if (!stats.value?.chart_data) return [0, 0, 0, 0, 0, 0]
    return stats.value.chart_data.map((p: any) => p.amount)
})

const chartLabels = computed(() => {
    if (!stats.value?.chart_data) return ['', '', '', '', '', '']
    return stats.value.chart_data.map((p: any) => p.month.split(' ')[0]) // Just the month name
})

const statCards = computed(() => [
    { label: 'Total Spent', value: formatAmount(stats.value?.total_spent || 0), color: 'error' },
    { label: 'Avg Payment', value: formatAmount(stats.value?.average_transaction || 0), color: 'info' },
    { label: 'Visit Count', value: stats.value?.transaction_count || 0, color: 'primary' }
])

async function fetchStats() {
    if (!props.vendorName || !props.modelValue) return
    loading.value = true
    try {
        const skip = (page.value - 1) * pageSize
        const response = await financeApi.getVendorStats(props.vendorName, skip, pageSize)
        // Explicitly slice to be safe, although backend should handle it
        stats.value = {
            ...response.data,
            recent_transactions: response.data.recent_transactions.slice(0, pageSize)
        }
    } catch (error) {
        console.error('[VendorInsights] Failed to fetch stats', error)
        stats.value = null
    } finally {
        loading.value = false
    }
}

function onChartHover(e: MouseEvent) {
    if (!stats.value?.chart_data?.length) return
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    const x = e.clientX - rect.left
    const segmentWidth = rect.width / stats.value.chart_data.length
    const index = Math.floor(x / segmentWidth)
    if (index >= 0 && index < stats.value.chart_data.length) {
        hoverValue.value = stats.value.chart_data[index].amount
        hoverMonth.value = stats.value.chart_data[index].month
    }
}

function resetPagination() {
    page.value = 1
}

function getVendorMdiIcon(name: string) {
    const n = (name || '').toLowerCase()
    if (n.includes('amazon')) return 'Package'
    if (n.includes('swiggy') || n.includes('zomato')) return 'Utensils'
    if (n.includes('uber') || n.includes('ola')) return 'Car'
    if (n.includes('netflix') || n.includes('prime') || n.includes('hotstar')) return 'Tv'
    if (n.includes('google') || n.includes('cloud')) return 'Cloud'
    if (n.includes('mortgage') || n.includes('rent')) return 'Home'
    if (n.includes('apple')) return 'Smartphone'
    if (n.includes('starbucks') || n.includes('coffee')) return 'Coffee'
    return 'Store'
}

watch(() => props.modelValue, (newVal) => {
    if (newVal) {
        resetPagination()
        fetchStats()
    }
})

watch(() => props.vendorName, () => {
    if (props.modelValue) {
        resetPagination()
        fetchStats()
    }
})
</script>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.95) !important;
    backdrop-filter: blur(20px) saturate(160%) !important;
}

.chart-gradient {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-secondary))) !important;
    position: relative;
    box-shadow: 0 8px 24px -8px rgba(var(--v-theme-primary), 0.5) !important;
}

.chart-glow {
    position: absolute;
    top: 50%;
    left: 50%;
    width: 150%;
    height: 150%;
    background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
    transform: translate(-50%, -50%);
    pointer-events: none;
}

.backdrop-blur {
    backdrop-filter: blur(8px);
}

.op-80 {
    opacity: 0.8;
}

.letter-spacing-1 {
    letter-spacing: 1px !important;
}

.line-height-1 {
    line-height: 1 !important;
}

.ga-3 {
    gap: 12px;
}

.gap-1 {
    gap: 4px;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.hover-bg-surface-variant:hover {
    background: rgba(var(--v-theme-surface-variant), 0.1) !important;
}
</style>
