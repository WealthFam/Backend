<script setup lang="ts">
import { localDateString } from '@/utils/time'
import { ref, computed, watch } from 'vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import { useAuthStore } from '@/stores/auth'
import BaseChart from '@/components/BaseChart.vue'
import {
    Calendar, TrendingUp, X, Hash
} from 'lucide-vue-next'

const { formatAmount } = useCurrency()
const authStore = useAuthStore()

const props = defineProps<{
    isOpen: boolean
    category: string
    month: number
    year: number
    budget?: any
}>()

const emit = defineEmits(['update:isOpen', 'close'])

// State
const loading = ref(false)
const transactions = ref<any[]>([])
const totalTransactions = ref(0)
const dailySpending = ref<{ day: number, amount: number }[]>([])
const merchantBreakdown = ref<any[]>([])
const serverOptions = ref({
    page: 1,
    itemsPerPage: 5,
    sortBy: 'date',
    sortOrder: 'desc'
})

const headers = [
    { title: 'Date', key: 'date', sortable: true },
    { title: 'Recipient', key: 'recipient', sortable: true },
    { title: 'Description', key: 'description' },
    { title: 'Amount', key: 'amount', align: 'end' as const, sortable: true }
]

// Fetch Data
const fetchData = async () => {
    if (!props.category) return
    loading.value = true
    try {
        const startDate = localDateString(props.year, props.month - 1, 1) + 'T00:00:00'
        const endDate = localDateString(props.year, props.month, 0) + 'T23:59:59'

        // Fetch Transactions
        const res = await financeApi.getTransactions(
            undefined,
            serverOptions.value.page,
            serverOptions.value.itemsPerPage,
            startDate,
            endDate,
            undefined,
            props.category,
            serverOptions.value.sortBy,
            serverOptions.value.sortOrder,
            authStore.selectedMemberId || undefined
        )
        transactions.value = res.data.items
        totalTransactions.value = res.data.total

        // Fetch Trends - Grouped by day
        const trendRes = await financeApi.getTransactions(
            undefined,
            1,
            1000,
            startDate,
            endDate,
            undefined,
            props.category,
            'date',
            'desc',
            authStore.selectedMemberId || undefined
        )

        processTrendData(trendRes.data.items)

        // Fetch Merchant Breakdown
        const merchantRes = await financeApi.getMerchantBreakdown(
            props.category,
            startDate,
            endDate,
            authStore.selectedMemberId || undefined
        )
        merchantBreakdown.value = merchantRes.data

    } catch (err) {
        console.error('Failed to fetch category details:', err)
    } finally {
        loading.value = false
    }
}

const processTrendData = (items: any[]) => {
    const daysInMonth = new Date(props.year, props.month, 0).getDate()
    const dailyMap = new Map()

    items.forEach(t => {
        const d = new Date(t.date).getDate()
        dailyMap.set(d, (dailyMap.get(d) || 0) + Math.abs(t.amount))
    })

    const data = []
    const now = new Date()
    const isCurrentMonth = now.getMonth() + 1 === props.month && now.getFullYear() === props.year
    const limitDay = isCurrentMonth ? now.getDate() : daysInMonth

    for (let i = 1; i <= limitDay; i++) {
        data.push({
            day: i,
            amount: dailyMap.get(i) || 0
        })
    }
    dailySpending.value = data
}

// Chart Configurations
const barChartData = computed(() => ({
    labels: dailySpending.value.map(d => d.day),
    datasets: [{
        label: 'Spending',
        data: dailySpending.value.map(d => d.amount),
        backgroundColor: 'rgba(59, 130, 246, 0.8)',
        borderRadius: 4
    }]
}))

const doughnutChartData = computed(() => {
    // Take top 5 and group others
    const sorted = [...merchantBreakdown.value].sort((a, b) => b.amount - a.amount)
    const top = sorted.slice(0, 5)
    const others = sorted.slice(5).reduce((acc, curr) => acc + curr.amount, 0)

    if (others > 0) {
        top.push({ merchant: 'Others', amount: others })
    }

    return {
        labels: top.map(v => v.merchant),
        datasets: [{
            data: top.map(v => v.amount),
            backgroundColor: [
                '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#64748B'
            ],
            borderWidth: 0
        }]
    }
})

const barOptions = {
    plugins: { legend: { display: false } },
    scales: {
        x: { grid: { display: false } },
        y: { ticks: { callback: (val: any) => '₹' + val } }
    }
}

const doughnutOptions = {
    plugins: {
        legend: {
            position: 'right',
            labels: { boxWidth: 12, padding: 15 }
        }
    },
    cutout: '70%'
}

// Watchers
watch(() => props.isOpen, (val) => {
    if (val) fetchData()
})

watch(serverOptions, () => {
    fetchData()
}, { deep: true })

const close = () => {
    emit('update:isOpen', false)
    emit('close')
}

const formatDate = (dateStr: string) => {
    const d = new Date(dateStr)
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}
</script>

<template>
    <v-dialog :model-value="isOpen" @update:model-value="emit('update:isOpen', $event)" max-width="1100" scrollable
        transition="dialog-bottom-transition">
        <v-card class="category-details-card overflow-hidden">
            <!-- Premium Header -->
            <v-toolbar color="primary" class="premium-header px-4" flat height="80">
                <div class="d-flex align-center w-100">
                    <div class="header-icon-container mr-4">
                        <span class="text-h4">{{ budget?.icon || '🏷️' }}</span>
                    </div>
                    <div>
                        <div class="text-overline text-white opacity-70 line-height-1 mb-1">
                            {{ new Date(year, month - 1).toLocaleString('default', { month: 'long', year: 'numeric' })
                            }}
                        </div>
                        <h2 class="text-h4 font-weight-bold text-white mb-0">{{ category }} Breakdown</h2>
                    </div>
                    <v-spacer />
                    <v-btn icon variant="text" color="white" @click="close">
                        <X />
                    </v-btn>
                </div>
            </v-toolbar>

            <v-card-text class="pa-4 custom-scrollbar-hidden">
                <v-row>
                    <!-- Spending Trend -->
                    <v-col cols="12" md="8">
                        <v-card variant="outlined" class="chart-box pa-3 border-dashed rounded-xl">
                            <div class="d-flex align-center mb-3">
                                <div class="icon-box-small bg-blue-light mr-3">
                                    <TrendingUp :size="18" class="text-primary" />
                                </div>
                                <div>
                                    <h3 class="text-subtitle-1 font-weight-bold mb-0">Daily Spending Trend</h3>
                                    <span class="text-caption text-medium-emphasis">How you spent throughout the
                                        month</span>
                                </div>
                            </div>
                            <BaseChart type="bar" :data="barChartData" :options="barOptions" :height="160" />
                        </v-card>
                    </v-col>

                    <!-- Merchant Breakdown -->
                    <v-col cols="12" md="4">
                        <v-card variant="outlined" class="chart-box pa-3 border-dashed rounded-xl">
                            <div class="d-flex align-center mb-3">
                                <div class="icon-box-small bg-purple-light mr-3">
                                    <Hash :size="18" class="text-purple" />
                                </div>
                                <div>
                                    <h3 class="text-subtitle-1 font-weight-bold mb-0">Top Merchants</h3>
                                    <span class="text-caption text-medium-emphasis">Where your money goes</span>
                                </div>
                            </div>
                            <div v-if="merchantBreakdown.length > 0">
                                <BaseChart type="doughnut" :data="doughnutChartData" :options="doughnutOptions"
                                    :height="160" />
                            </div>
                            <div v-else class="d-flex align-center justify-center" style="height: 160px">
                                <span class="text-caption text-medium-emphasis">No merchant data available</span>
                            </div>
                        </v-card>
                    </v-col>

                    <!-- Transaction List -->
                    <v-col cols="12">
                        <div class="d-flex align-center mb-4 mt-2">
                            <div class="icon-box-small bg-green-light mr-3">
                                <Calendar :size="18" class="text-success" />
                            </div>
                            <h3 class="text-h6 font-weight-bold mb-0">Transaction History</h3>
                            <v-spacer />
                            <div class="text-caption text-medium-emphasis">{{ totalTransactions }} transactions found
                            </div>
                        </div>

                        <v-data-table-server v-model:options="serverOptions" :headers="headers" :items="transactions"
                            :items-length="totalTransactions" :loading="loading" density="compact"
                            :items-per-page="serverOptions.itemsPerPage" :items-per-page-options="[5, 10, 15, 20]"
                            class="modern-table translucent-table rounded-xl" hover>
                            <template v-slot:item.date="{ item }">
                                <span class="text-body-2 text-medium-emphasis">{{ formatDate(item.date) }}</span>
                            </template>
                            <template v-slot:item.recipient="{ item }">
                                <span class="font-weight-medium">{{ item.recipient || 'N/A' }}</span>
                            </template>
                            <template v-slot:item.amount="{ item }">
                                <span :class="item.amount > 0 ? 'text-success' : 'font-weight-bold'">
                                    {{ formatAmount(item.amount) }}
                                </span>
                            </template>
                        </v-data-table-server>
                    </v-col>
                </v-row>
            </v-card-text>

            <v-divider />
            <v-card-actions class="pa-4 bg-surface d-flex align-center justify-space-between">
                <v-btn variant="tonal" color="primary" @click="close" class="px-6 font-weight-bold rounded-pill">
                    Close Analysis
                </v-btn>

                <div v-if="budget" class="d-flex align-center ga-4 bg-surface rounded-pill px-4 py-2 border">
                    <div class="d-flex flex-column align-end line-height-1">
                        <span class="text-caption text-medium-emphasis mb-1">Budget Limit</span>
                        <span class="font-weight-bold text-body-2">{{ formatAmount(budget.amount_limit) }}</span>
                    </div>
                    <v-divider vertical class="my-1" />
                    <div class="d-flex flex-column align-end line-height-1">
                        <span class="text-caption text-medium-emphasis mb-1">Spent</span>
                        <span class="font-weight-black text-body-2"
                            :class="budget.spent > budget.amount_limit ? 'text-error' : 'text-primary'">
                            {{ formatAmount(budget.spent) }}
                        </span>
                    </div>
                </div>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.category-details-card {
    border-radius: 24px !important;
}

.premium-header {
    background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%) !important;
}

.header-icon-container {
    background: rgba(255, 255, 255, 0.2);
    padding: 12px;
    border-radius: 16px;
    display: flex;
    align-center: center;
    justify-content: center;
}

.icon-box-small {
    padding: 8px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.bg-blue-light {
    background-color: rgba(59, 130, 246, 0.1);
}

.bg-purple-light {
    background-color: rgba(139, 92, 246, 0.1);
}

.bg-green-light {
    background-color: rgba(16, 185, 129, 0.1);
}

/* Custom Scrollbar Hidden while maintaining scroll */
.custom-scrollbar-hidden {
    scrollbar-width: none;
    /* Firefox */
    -ms-overflow-style: none;
    /* IE and Edge */
}

.custom-scrollbar-hidden::-webkit-scrollbar {
    display: none;
    /* Chrome, Safari, Opera */
}

.chart-box {
    transition: all 0.2s ease;
    background: rgba(var(--v-theme-surface), 0.5);
}

.translucent-table {
    background: transparent !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
}

.line-height-1 {
    line-height: 1;
}
</style>
