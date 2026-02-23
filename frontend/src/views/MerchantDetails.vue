<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import {
    Store,
    ArrowLeft,
    TrendingUp,
    Calendar,
    CreditCard,
    Receipt,
    Wallet,
    ArrowUpRight,
    ArrowDownRight,
    ChevronRight,
    PieChart,
    Timer
} from 'lucide-vue-next'
import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCurrency } from '@/composables/useCurrency'
import { format, parseISO } from 'date-fns'
import BaseChart from '@/components/BaseChart.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const { formatAmount } = useCurrency()

const merchantName = computed(() => route.params.id as string)
const transactions = ref<any[]>([])
const isLoading = ref(true)
const transactionsCount = computed(() => transactions.value.length)

const totalSpent = computed(() => {
    return transactions.value.reduce((sum, tx) => sum + Math.abs(Number(tx.amount || 0)), 0)
})

const averageTx = computed(() => {
    return transactionsCount.value > 0 ? totalSpent.value / transactionsCount.value : 0
})

const lastTransaction = computed(() => {
    if (transactions.value.length === 0) return null
    return transactions.value[0] // Assuming sorted by date desc
})

async function fetchMerchantData() {
    isLoading.value = true
    try {
        const userId = auth.selectedMemberId || undefined
        const res = await financeApi.getTransactions(
            undefined, // accountId
            1,         // page
            1000,      // limit
            undefined, // startDate
            undefined, // endDate
            merchantName.value, // search
            undefined, // category
            'date',    // sortBy
            'desc',    // sortOrder
            userId     // userId
        )
        if (res.data && res.data.items) {
            transactions.value = res.data.items
        }
    } catch (e) {
        console.error("Failed to fetch merchant data", e)
    } finally {
        isLoading.value = false
    }
}

onMounted(() => {
    fetchMerchantData()
})

watch(merchantName, () => {
    fetchMerchantData()
})

function getTransactionColor(type: string) {
    return type === 'DEBIT' ? 'error' : 'success'
}

function getTransactionIcon(type: string) {
    return type === 'DEBIT' ? ArrowUpRight : ArrowDownRight
}

const categoryBreakdown = computed(() => {
    const cats: Record<string, number> = {}
    transactions.value.forEach(tx => {
        const cat = tx.category || 'Uncategorized'
        // Use absolute value for breakdown to show volume
        cats[cat] = (cats[cat] || 0) + Math.abs(Number(tx.amount))
    })
    return Object.entries(cats).sort((a, b) => b[1] - a[1]).slice(0, 5)
})

const spendingTrendData = computed(() => {
    if (!transactions.value.length) return null

    // Group by month
    const groups: Record<string, number> = {}
    transactions.value.forEach(tx => {
        const month = format(parseISO(tx.date), 'MMM yyyy')
        groups[month] = (groups[month] || 0) + Math.abs(Number(tx.amount))
    })

    const labels = Object.keys(groups).reverse() // Chronological if data is desc
    const data = labels.map(l => groups[l])

    return {
        labels,
        datasets: [{
            label: 'Spending',
            data: data,
            borderColor: 'rgb(var(--v-theme-primary))',
            backgroundColor: 'rgba(var(--v-theme-primary), 0.1)',
            fill: true,
            tension: 0.4
        }]
    }
})
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Background mesh -->
            <div class="mesh-blob blob-1"></div>
            <div class="mesh-blob blob-2"></div>

            <div class="relative-pos z-10">
                <!-- Header -->
                <div class="d-flex align-center mb-8">
                    <v-btn icon variant="tonal" class="mr-4 rounded-xl" @click="router.back()">
                        <ArrowLeft :size="20" />
                    </v-btn>
                    <div>
                        <div class="d-flex align-center gap-2 mb-1">
                            <Store :size="16" class="text-primary" />
                            <span class="text-overline font-weight-black letter-spacing-2 opacity-60">Merchant
                                Profile</span>
                        </div>
                        <h1 class="text-h4 font-weight-black text-content">{{ merchantName }}</h1>
                    </div>
                </div>

                <!-- Stats Grid -->
                <v-row class="mb-6">
                    <v-col cols="12" md="3">
                        <v-card class="premium-card h-100 pa-6">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="stat-icon-box primary">
                                    <Wallet :size="20" />
                                </div>
                                <div class="text-caption font-weight-black opacity-60">TOTAL SPENT</div>
                            </div>
                            <div class="text-h4 font-weight-black mb-1">{{ formatAmount(totalSpent) }}</div>
                            <div class="text-caption font-weight-bold opacity-60">Across {{ transactionsCount }}
                                payments</div>
                        </v-card>
                    </v-col>

                    <v-col cols="12" md="3">
                        <v-card class="premium-card h-100 pa-6">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="stat-icon-box info">
                                    <Timer :size="20" />
                                </div>
                                <div class="text-caption font-weight-black opacity-60">AVG. TRANSACTION</div>
                            </div>
                            <div class="text-h4 font-weight-black mb-1">{{ formatAmount(averageTx) }}</div>
                            <div class="text-caption font-weight-bold opacity-60">Spending velocity</div>
                        </v-card>
                    </v-col>

                    <v-col cols="12" md="3">
                        <v-card class="premium-card h-100 pa-6">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="stat-icon-box success">
                                    <Calendar :size="20" />
                                </div>
                                <div class="text-caption font-weight-black opacity-60">LATEST PAYMENT</div>
                            </div>
                            <div class="text-h5 font-weight-black mb-1" v-if="lastTransaction">
                                {{ format(parseISO(lastTransaction.date), 'MMM dd, yyyy') }}
                            </div>
                            <div class="text-caption font-weight-bold opacity-60" v-else>No history</div>
                        </v-card>
                    </v-col>

                    <v-col cols="12" md="3">
                        <v-card class="premium-card h-100 pa-6">
                            <div class="d-flex align-center justify-space-between mb-4">
                                <div class="stat-icon-box warning">
                                    <PieChart :size="20" />
                                </div>
                                <div class="text-caption font-weight-black opacity-60">PRIMARY CATEGORY</div>
                            </div>
                            <div class="text-h5 font-weight-black mb-1" v-if="categoryBreakdown.length">
                                {{ categoryBreakdown[0][0] }}
                            </div>
                            <div class="text-caption font-weight-bold opacity-60" v-else>Mixed</div>
                        </v-card>
                    </v-col>
                </v-row>

                <!-- Visualization -->
                <v-row v-if="transactions.length > 2">
                    <v-col cols="12">
                        <v-card class="premium-card pa-6 mb-6">
                            <div class="d-flex align-center justify-space-between mb-6">
                                <div class="d-flex align-center gap-3">
                                    <TrendingUp :size="20" class="text-primary" />
                                    <h3 class="text-h6 font-weight-black">Spending Dynamics</h3>
                                </div>
                            </div>
                            <BaseChart v-if="spendingTrendData" type="line" :data="spendingTrendData" :height="220" />
                        </v-card>
                    </v-col>
                </v-row>

                <v-row>
                    <!-- Transactions List -->
                    <v-col cols="12" md="8">
                        <v-card class="premium-card pa-0 overflow-hidden">
                            <div class="pa-6 border-b d-flex align-center justify-space-between">
                                <div class="d-flex align-center gap-3">
                                    <Receipt :size="20" class="text-primary" />
                                    <h3 class="text-h6 font-weight-black">Payment History</h3>
                                </div>
                                <v-btn variant="tonal" size="small" rounded="xl" class="text-primary">
                                    Download Report
                                </v-btn>
                            </div>

                            <div v-if="isLoading" class="pa-12 text-center">
                                <v-progress-circular indeterminate color="primary" />
                            </div>

                            <v-fade-transition v-else>
                                <div>
                                    <div v-for="tx in transactions" :key="tx.id"
                                        class="tx-item d-flex align-center pa-5 border-b hover-effect transition-all cursor-pointer">
                                        <div class="tx-icon-box mr-4" :class="getTransactionColor(tx.type)">
                                            <component :is="getTransactionIcon(tx.type)" :size="18" />
                                        </div>
                                        <div class="flex-grow-1 min-width-0">
                                            <div class="d-flex align-center justify-space-between mb-1">
                                                <span class="text-subtitle-1 font-weight-black text-truncate">{{
                                                    tx.description || merchantName }}</span>
                                                <span class="text-subtitle-1 font-weight-black"
                                                    :class="'text-' + getTransactionColor(tx.type)">
                                                    {{ tx.type === 'DEBIT' ? '-' : '+' }}{{
                                                        formatAmount(Math.abs(tx.amount)) }}
                                                </span>
                                            </div>
                                            <div class="d-flex align-center gap-4 opacity-70">
                                                <div class="d-flex align-center gap-1 text-caption font-weight-bold">
                                                    <Calendar :size="14" />
                                                    {{ format(parseISO(tx.date), 'MMM dd, h:mm a') }}
                                                </div>
                                                <div class="d-flex align-center gap-1 text-caption font-weight-bold">
                                                    <CreditCard :size="14" />
                                                    Acc ...{{ tx.account_id.slice(-4) }}
                                                </div>
                                                <v-chip size="x-small" density="comfortable"
                                                    class="text-uppercase font-weight-black ml-2"
                                                    color="surface-variant">
                                                    {{ tx.category || 'General' }}
                                                </v-chip>
                                            </div>
                                        </div>
                                        <ChevronRight :size="16" class="ml-4 opacity-20" />
                                    </div>

                                    <div v-if="transactions.length === 0" class="pa-16 text-center">
                                        <p class="text-medium-emphasis">No transactions found for this merchant.</p>
                                    </div>
                                </div>
                            </v-fade-transition>
                        </v-card>
                    </v-col>

                    <!-- Insights Sidebar -->
                    <v-col cols="12" md="4">
                        <v-card class="premium-card pa-6 mb-6">
                            <h3 class="text-h6 font-weight-black mb-4">Spending Breakdown</h3>
                            <div v-for="[cat, val] in categoryBreakdown" :key="cat" class="mb-4">
                                <div class="d-flex align-center justify-space-between mb-2">
                                    <span class="text-subtitle-2 font-weight-bold">{{ cat }}</span>
                                    <span class="text-subtitle-2 font-weight-black">{{ formatAmount(val) }}</span>
                                </div>
                                <v-progress-linear :model-value="(val / totalSpent) * 100" color="primary" rounded
                                    height="6" class="bg-surface-variant bg-opacity-10" />
                            </div>
                        </v-card>

                        <v-card class="premium-card primary-insight-card pa-6 text-white overflow-hidden relative-pos">
                            <div class="relative-pos z-10">
                                <TrendingUp :size="32" class="mb-4 opacity-50" />
                                <h3 class="text-h6 font-weight-black mb-2">Merchant Insight</h3>
                                <p class="text-body-2 font-weight-bold opacity-80 mb-0">
                                    You spend most of your funds at **{{ merchantName }}** on **{{
                                        categoryBreakdown.length ? categoryBreakdown[0][0] : 'various items' }}**.
                                    Consolidating these payments could help track loyalty rewards.
                                </p>
                            </div>
                            <div class="mesh-blob white-blob"
                                style="bottom: -50px; right: -20px; width: 150px; height: 150px;"></div>
                        </v-card>
                    </v-col>
                </v-row>
            </div>
        </v-container>
    </MainLayout>
</template>

<style scoped>
.page-container {
    position: relative;
    min-height: calc(100vh - 64px);
    overflow: hidden;
}

.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.1;
    border-radius: 50%;
    z-index: 0;
}

.blob-1 {
    background: rgb(var(--v-theme-primary));
    width: 600px;
    height: 600px;
    top: -200px;
    right: -100px;
}

.blob-2 {
    background: rgb(var(--v-theme-info));
    width: 400px;
    height: 400px;
    bottom: -100px;
    left: -100px;
}

.white-blob {
    background: white;
    opacity: 0.1;
    filter: blur(40px);
}

.premium-card {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(var(--v-border-color), 0.08) !important;
    border-radius: 24px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.primary-insight-card {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)), rgb(var(--v-theme-secondary))) !important;
    border: none !important;
}

.stat-icon-box {
    width: 44px;
    height: 44px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.stat-icon-box.primary {
    color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.1);
}

.stat-icon-box.info {
    color: rgb(var(--v-theme-info));
    background: rgba(var(--v-theme-info), 0.1);
}

.stat-icon-box.success {
    color: rgb(var(--v-theme-success));
    background: rgba(var(--v-theme-success), 0.1);
}

.stat-icon-box.warning {
    color: rgb(var(--v-theme-warning));
    background: rgba(var(--v-theme-warning), 0.1);
}

.tx-item {
    transition: all 0.2s;
}

.hover-effect:hover {
    background: rgba(var(--v-theme-on-surface), 0.02);
    padding-left: 24px !important;
}

.tx-icon-box {
    width: 38px;
    height: 38px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.tx-icon-box.error {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
}

.tx-icon-box.success {
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
}

.border-b {
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05);
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
}

.gap-6 {
    gap: 24px;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.letter-spacing-2 {
    letter-spacing: 2px !important;
}
</style>
