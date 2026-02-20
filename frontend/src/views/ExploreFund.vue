<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import FundPerformanceChart from './mutual-funds/components/FundPerformanceChart.vue'
import InvestModal from './mutual-funds/modals/InvestModal.vue'
import { ChevronLeft, TrendingUp, Shield, BarChart2, Star, Target, Globe, Briefcase } from 'lucide-vue-next'

const route = useRoute()
const router = useRouter()
const notify = useNotificationStore()

const schemeCode = route.params.id as string
const fund = ref<any>(null)
const isLoading = ref(true)

// Modal
const showInvestModal = ref(false)

async function fetchFundInfo() {
    isLoading.value = true
    try {
        const res = await financeApi.getSchemeInfo(schemeCode)
        fund.value = res.data
    } catch (e) {
        console.error("Failed to fetch fund info:", e)
        notify.error("Failed to load fund details")
        router.back()
    } finally {
        isLoading.value = false
    }
}

onMounted(() => {
    fetchFundInfo()
})

const chartData = computed(() => {
    return (fund.value?.nav_history || []).map((point: any) => ({
        date: point.date,
        value: point.value,
        invested: null // No investments in explore mode
    }))
})

function getRiskColor(risk: string) {
    switch (risk?.toLowerCase()) {
        case 'low': return 'success'
        case 'moderate': return 'info'
        case 'high': return 'warning'
        case 'very high': return 'error'
        default: return 'primary'
    }
}
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container">
            <!-- Mesh Background -->
            <div class="mesh-blob blob-1"></div>
            <div class="mesh-blob blob-2"></div>

            <div class="relative-pos z-10" v-if="!isLoading && fund">
                <!-- Header -->
                <div class="d-flex flex-column flex-md-row justify-space-between align-md-center gap-4 mb-8">
                    <div class="d-flex align-center gap-4">
                        <v-btn icon variant="tonal" rounded="lg" color="primary" @click="router.back()">
                            <ChevronLeft :size="24" />
                        </v-btn>
                        <div>
                            <h1 class="text-h4 font-weight-black text-content line-clamp-1 mb-1">{{ fund.scheme_name }}
                            </h1>
                            <div class="d-flex align-center gap-3 flex-wrap">
                                <v-chip size="x-small" label color="primary" variant="tonal"
                                    class="font-weight-black text-uppercase">
                                    {{ fund.category || 'Mutual Fund' }}
                                </v-chip>
                                <div v-if="fund.fund_house"
                                    class="d-flex align-center gap-1 text-caption font-weight-bold text-medium-emphasis">
                                    <Briefcase :size="14" class="opacity-60" />
                                    <span>{{ fund.fund_house }}</span>
                                </div>
                                <div
                                    class="d-flex align-center gap-1 text-caption font-weight-bold text-medium-emphasis">
                                    <Globe :size="14" class="opacity-60" />
                                    <span>{{ fund.scheme_code }}</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <v-btn color="primary" rounded="xl" size="x-large"
                        class="font-weight-black px-10 shadow-lg action-btn" @click="showInvestModal = true">
                        Invest Now
                    </v-btn>
                </div>

                <v-row>
                    <!-- Left Column: Chart -->
                    <v-col cols="12" lg="8">
                        <v-card class="premium-glass-card pa-6 mb-6" rounded="xl">
                            <div class="d-flex align-center justify-space-between mb-6">
                                <h3 class="text-h6 font-weight-black text-content d-flex align-center gap-2">
                                    <TrendingUp :size="24" class="text-primary" /> NAV Historical Performance (1Y)
                                </h3>
                                <div class="text-h5 font-weight-black text-primary">
                                    ₹{{ fund.last_nav.toFixed(2) }} <span
                                        class="text-caption text-medium-emphasis font-weight-bold">Current</span>
                                </div>
                            </div>

                            <!-- Chart Area -->
                            <div style="height: 400px;">
                                <FundPerformanceChart v-if="chartData.length" :data="chartData" :markers="[]"
                                    :benchmark="[]" />
                                <div v-else
                                    class="d-flex align-center justify-center h-100 text-medium-emphasis font-weight-bold">
                                    No history available
                                </div>
                            </div>
                        </v-card>
                    </v-col>

                    <!-- Right Column: Key Metrics -->
                    <v-col cols="12" lg="4">
                        <h3 class="text-h6 font-weight-black mb-4">Fund Overview</h3>

                        <v-row>
                            <v-col cols="6">
                                <v-card class="metric-card pa-4" rounded="xl">
                                    <Shield :size="20" :class="`text-${getRiskColor(fund.risk_level)} mb-2`" />
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Risk
                                        Profile</div>
                                    <div
                                        :class="`text-subtitle-1 font-weight-black text-${getRiskColor(fund.risk_level)}`">
                                        {{ fund.risk_level }}</div>
                                </v-card>
                            </v-col>
                            <v-col cols="6">
                                <v-card class="metric-card pa-4" rounded="xl">
                                    <BarChart2 :size="20" class="text-primary mb-2" />
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Fund
                                        Size (AUM)</div>
                                    <div class="text-subtitle-1 font-weight-black text-content">{{ fund.aum }}</div>
                                </v-card>
                            </v-col>
                            <v-col cols="6">
                                <v-card class="metric-card pa-4" rounded="xl">
                                    <TrendingUp :size="20" class="text-success mb-2" />
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">3Y
                                        Returns (Ann.)</div>
                                    <div class="text-subtitle-1 font-weight-black text-success">{{ fund.returns_3y > 0 ?
                                        '+' : '' }}{{ fund.returns_3y }}%</div>
                                </v-card>
                            </v-col>
                            <v-col cols="6">
                                <v-card class="metric-card pa-4" rounded="xl">
                                    <Star :size="20" class="text-warning mb-2" />
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">
                                        Rating</div>
                                    <div class="d-flex align-center gap-1">
                                        <span class="text-subtitle-1 font-weight-black text-content">{{ fund.rating
                                            }}</span>
                                        <div class="d-flex">
                                            <Star v-for="i in 5" :key="i" :size="12"
                                                :class="i <= fund.rating ? 'text-warning' : 'text-medium-emphasis opacity-20'"
                                                fill="currentColor" />
                                        </div>
                                    </div>
                                </v-card>
                            </v-col>
                        </v-row>

                        <v-card class="premium-glass-card pa-6 mt-6" rounded="xl">
                            <div class="d-flex align-center gap-4 mb-4">
                                <v-avatar color="primary" variant="tonal" size="48" rounded="lg">
                                    <Target :size="24" />
                                </v-avatar>
                                <div>
                                    <div class="text-subtitle-1 font-weight-black">Ready to invest?</div>
                                    <div class="text-caption text-medium-emphasis font-weight-medium">Start building
                                        your wealth today.</div>
                                </div>
                            </div>
                            <v-btn block color="primary" size="large" rounded="xl" class="font-weight-black mt-2"
                                @click="showInvestModal = true">
                                Start Investing
                            </v-btn>
                        </v-card>
                    </v-col>
                </v-row>
            </div>

            <div v-if="isLoading" class="d-flex align-center justify-center h-screen-50">
                <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            </div>
        </v-container>

        <!-- Invest Modal -->
        <InvestModal v-model="showInvestModal" :fund="fund" @success="router.push('/mutual-funds')" />
    </MainLayout>
</template>

<style scoped>
.page-container {
    min-height: calc(100vh - 64px);
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.mesh-blob {
    position: absolute;
    filter: blur(100px);
    opacity: 0.15;
    border-radius: 50%;
    z-index: 0;
    pointer-events: none;
}

.blob-1 {
    background: rgb(var(--v-theme-primary));
    width: 600px;
    height: 600px;
    top: -150px;
    right: -150px;
}

.blob-2 {
    background: rgb(var(--v-theme-secondary));
    width: 500px;
    height: 500px;
    bottom: -100px;
    left: -100px;
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
    box-shadow: none !important;
}

.metric-card {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05) !important;
    transition: transform 0.2s ease;
}

.metric-card:hover {
    transform: translateY(-2px);
    border-color: rgba(var(--v-theme-primary), 0.2) !important;
}

.action-btn {
    transition: transform 0.2s ease;
}

.action-btn:hover {
    transform: scale(1.02);
}
</style>
