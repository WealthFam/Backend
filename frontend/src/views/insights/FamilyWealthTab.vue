<template>
    <div class="family-wealth-content pb-10">
        <v-row v-if="loading" class="mt-4">
            <v-col cols="12">
                <v-skeleton-loader type="card, article" rounded="xl" class="premium-glass-card" />
            </v-col>
        </v-row>

        <template v-else-if="wealthData">
            <!-- Total Wealth Hero (Ultra Premium) -->
            <v-row class="mt-4">
                <v-col cols="12">
                    <v-card class="wealth-hero-card pa-10 overflow-hidden" rounded="xl" elevation="24">
                        <div class="relative-pos z-10">
                            <v-row align="center">
                                <v-col cols="12" md="8">
                                    <div class="d-flex align-center mb-4">
                                        <div class="premium-badge mr-4">
                                            <ShieldCheck :size="16" class="text-primary" />
                                            <span class="ml-2 font-weight-black letter-spacing-1">FAMILY
                                                CONSOLIDATED</span>
                                        </div>
                                    </div>
                                    <h2
                                        class="text-overline font-weight-black text-white opacity-60 mb-1 letter-spacing-2">
                                        Total Family Net Worth</h2>
                                    <h1 class="text-h1 font-weight-black text-white mb-8 tracking-tighter">
                                        {{ formatAmount(wealthData.total_net_worth) }}
                                    </h1>

                                    <div class="d-flex flex-wrap gap-4 mt-2">
                                        <div class="glass-stat-chip">
                                            <TrendingUp :size="18" class="text-success-lighten-2 mr-2" />
                                            <span class="font-weight-bold">{{ formatAmount(wealthData.total_assets) }}
                                                Assets</span>
                                        </div>
                                        <div class="glass-stat-chip">
                                            <TrendingDown :size="18" class="text-red-lighten-2 mr-2" />
                                            <span class="font-weight-bold">{{ formatAmount(wealthData.total_liabilities)
                                            }} Liabilities</span>
                                        </div>
                                    </div>
                                </v-col>

                                <v-col cols="12" md="4" class="d-none d-md-flex justify-end">
                                    <div class="family-avatar-stack">
                                        <v-avatar v-for="(m, i) in wealthData.members.slice(0, 4)" :key="m.user_id"
                                            :size="64" class="stacked-avatar border-lg"
                                            :style="{ zIndex: 10 - i, transform: `translateX(${i * -15}px)` }">
                                            <div class="avatar-gradient-fill h-100 w-100 d-flex align-center justify-center font-weight-black text-h5 text-white"
                                                :style="{ background: i % 2 === 0 ? 'linear-gradient(135deg, #3B82F6 0%, #2563EB 100%)' : 'linear-gradient(135deg, #10B981 0%, #059669 100%)' }">
                                                {{ m.name.charAt(0).toUpperCase() }}
                                            </div>
                                        </v-avatar>
                                    </div>
                                </v-col>
                            </v-row>
                        </div>

                        <!-- Animated Aura Background -->
                        <div class="aura-container">
                            <div class="aura aura-1"></div>
                            <div class="aura aura-2"></div>
                            <div class="aura aura-3"></div>
                        </div>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Interactive Charts Row -->
            <v-row class="mt-8">
                <v-col cols="12" md="7">
                    <v-card rounded="xl" class="premium-glass-card h-100 no-hover border-premium">
                        <v-card-title class="pa-6 d-flex align-center">
                            <div class="icon-orb mr-4">
                                <BarChart3 :size="20" class="text-primary" />
                            </div>
                            <div>
                                <div class="text-h6 font-weight-black">Wealth Composition</div>
                                <div class="text-caption font-weight-bold opacity-60">Asset vs Liability by Member</div>
                            </div>
                        </v-card-title>
                        <v-card-text class="pa-6">
                            <div class="chart-container" style="height: 350px;">
                                <BaseChart type="bar" :data="compositionChartData" :options="stackedChartOptions"
                                    :height="350" />
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>

                <v-col cols="12" md="5">
                    <v-card rounded="xl" class="premium-glass-card h-100 no-hover border-premium overflow-hidden">
                        <v-card-title class="pa-6 d-flex align-center">
                            <div class="icon-orb mr-4">
                                <PieChart :size="20" class="text-primary" />
                            </div>
                            <div>
                                <div class="text-h6 font-weight-black">Equity Distribution</div>
                                <div class="text-caption font-weight-bold opacity-60">Percentage of net family wealth
                                </div>
                            </div>
                        </v-card-title>
                        <v-card-text class="pa-6 d-flex align-center justify-center">
                            <div class="chart-container-inner relative-pos w-100">
                                <BaseChart type="doughnut" :data="distributionChartData" :height="300"
                                    :options="{ cutout: '75%', plugins: { legend: { display: false } } }" />
                                <div class="chart-center-label">
                                    <div class="text-overline font-weight-black opacity-60">TOTAL</div>
                                    <div class="text-h6 font-weight-black">{{ formatAmount(wealthData.total_net_worth)
                                    }}</div>
                                </div>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Member Profile Grid -->
            <div class="mt-12 mb-4">
                <h3 class="text-h6 font-weight-black d-flex align-center">
                    <Users :size="20" class="mr-3 text-primary" />
                    Family Member Insights
                </h3>
            </div>

            <v-row>
                <v-col v-for="(member, i) in wealthData.members" :key="member.user_id" cols="12" sm="6" lg="3">
                    <v-card rounded="xl" class="member-profile-card h-100 border-premium">
                        <div class="pa-6">
                            <v-avatar :color="chartPalette[i % chartPalette.length]" size="56"
                                class="mb-4 elevation-8 profile-avatar">
                                <span class="text-h5 text-white font-weight-black">{{
                                    member.name.charAt(0).toUpperCase() }}</span>
                            </v-avatar>

                            <div class="text-h6 font-weight-black mb-1">{{ member.name }}</div>
                            <v-chip size="x-small" class="font-weight-black mb-6 px-3"
                                :color="member.role === 'OWNER' ? 'primary' : 'secondary'" variant="tonal">
                                {{ member.role }}
                            </v-chip>

                            <v-divider class="mb-6 opacity-10"></v-divider>

                            <div class="d-flex justify-space-between align-center mb-2">
                                <span class="text-caption font-weight-bold opacity-60">NET WORTH</span>
                                <span class="text-body-2 font-weight-black">{{ formatAmount(member.net_worth) }}</span>
                            </div>
                            <div class="member-progress mb-6">
                                <v-progress-linear :model-value="(member.net_worth / wealthData.total_assets) * 100"
                                    :color="chartPalette[i % chartPalette.length]" height="8" rounded="pill">
                                </v-progress-linear>
                            </div>

                            <div class="grid-stats">
                                <div class="stat-box">
                                    <div class="text-overline opacity-50 font-weight-black">Accounts</div>
                                    <div class="text-body-1 font-weight-black">{{ member.account_count }}</div>
                                </div>
                                <div class="stat-box text-right">
                                    <div class="text-overline opacity-50 font-weight-black">Equity</div>
                                    <div class="text-body-1 font-weight-black">{{ ((member.net_worth /
                                        wealthData.total_assets) * 100).toFixed(1) }}%</div>
                                </div>
                            </div>
                        </div>
                    </v-card>
                </v-col>

                <!-- Shared Wealth Card -->
                <v-col v-if="wealthData.shared.account_count > 0" cols="12" sm="6" lg="3">
                    <v-card rounded="xl" class="member-profile-card h-100 border-premium shared-theme">
                        <div class="pa-6">
                            <v-avatar color="surface-variant" size="56" class="mb-4 elevation-8 profile-avatar">
                                <Users :size="28" class="text-white" />
                            </v-avatar>

                            <div class="text-h6 font-weight-black mb-1">Shared Wealth</div>
                            <v-chip size="x-small" class="font-weight-black mb-6 px-3" color="white" variant="outlined">
                                COLLECTIVE
                            </v-chip>

                            <v-divider class="mb-6 opacity-20"></v-divider>

                            <div class="d-flex justify-space-between align-center mb-2">
                                <span class="text-caption font-weight-bold opacity-60">NET WORTH</span>
                                <span class="text-body-2 font-weight-black">{{ formatAmount(wealthData.shared.net_worth)
                                }}</span>
                            </div>
                            <div class="member-progress mb-6">
                                <v-progress-linear
                                    :model-value="(wealthData.shared.net_worth / wealthData.total_assets) * 100"
                                    color="white" height="8" rounded="pill">
                                </v-progress-linear>
                            </div>

                            <div class="grid-stats">
                                <div class="stat-box">
                                    <div class="text-overline opacity-50 font-weight-black">Accounts</div>
                                    <div class="text-body-1 font-weight-black">{{ wealthData.shared.account_count }}
                                    </div>
                                </div>
                                <div class="stat-box text-right">
                                    <div class="text-overline opacity-50 font-weight-black">Equity</div>
                                    <div class="text-body-1 font-weight-black">{{ ((wealthData.shared.net_worth /
                                        wealthData.total_assets) * 100).toFixed(1) }}%</div>
                                </div>
                            </div>
                        </div>
                    </v-card>
                </v-col>
            </v-row>
        </template>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useCurrency } from '@/composables/useCurrency'
import BaseChart from '@/components/BaseChart.vue'
import { Users, PieChart, ShieldCheck, TrendingUp, TrendingDown, BarChart3 } from 'lucide-vue-next'

const { formatAmount } = useCurrency()

const wealthData = ref<any>(null)
const loading = ref(true)

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
    '#14B8A6'  // Teal
]

onMounted(async () => {
    loading.value = true
    try {
        const res = await financeApi.getFamilyWealth()
        wealthData.value = res.data
    } catch (e) {
        console.error("Failed to fetch family wealth data", e)
    } finally {
        loading.value = false
    }
})

const distributionChartData = computed(() => {
    if (!wealthData.value) return null

    const labels = [...wealthData.value.members.map((m: any) => m.name)]
    const data = [...wealthData.value.members.map((m: any) => Math.max(0, m.net_worth))]

    if (wealthData.value.shared.net_worth > 0) {
        labels.push('Shared')
        data.push(wealthData.value.shared.net_worth)
    }

    return {
        labels,
        datasets: [{
            data,
            backgroundColor: chartPalette.slice(0, labels.length),
            hoverOffset: 15,
            borderWidth: 0,
            borderRadius: 8
        }]
    }
})

const compositionChartData = computed(() => {
    if (!wealthData.value) return null

    const labels = [...wealthData.value.members.map((m: any) => m.name)]
    if (wealthData.value.shared.account_count > 0) labels.push('Shared')

    const assetsData = [...wealthData.value.members.map((m: any) => m.assets)]
    if (wealthData.value.shared.account_count > 0) assetsData.push(wealthData.value.shared.assets)

    const liabilitiesData = [...wealthData.value.members.map((m: any) => m.liabilities)]
    if (wealthData.value.shared.account_count > 0) liabilitiesData.push(wealthData.value.shared.liabilities)

    return {
        labels,
        datasets: [
            {
                label: 'Assets',
                data: assetsData,
                backgroundColor: '#10B981',
                borderRadius: 8
            },
            {
                label: 'Liabilities',
                data: liabilitiesData,
                backgroundColor: '#EF4444',
                borderRadius: 8
            }
        ]
    }
})

const stackedChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: { display: true, position: 'bottom' }
    },
    scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, grid: { color: 'rgba(var(--v-border-color), 0.05)' } }
    }
}
</script>

<style scoped>
/* Ultra Premium Wealth Hero */
.wealth-hero-card {
    background: linear-gradient(135deg, #020617 0%, #1e1b4b 100%);
    position: relative;
    border: 1px solid rgba(255, 255, 255, 0.05) !important;
}

.premium-badge {
    display: inline-flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 6px 16px;
    border-radius: 100px;
    color: #94a3b8;
    font-size: 0.7rem;
}

.glass-stat-chip {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 12px 20px;
    border-radius: 100px;
    color: white;
    font-size: 0.9rem;
}

.family-avatar-stack {
    display: flex;
    align-items: center;
}

.stacked-avatar {
    border: 4px solid #020617 !important;
    transition: transform 0.3s ease;
    cursor: pointer;
}

.stacked-avatar:hover {
    transform: translateY(-5px) !important;
}

/* Animated Aura */
.aura-container {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    pointer-events: none;
    overflow: hidden;
}

.aura {
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.15;
}

.aura-1 {
    width: 600px;
    height: 600px;
    background: #3B82F6;
    top: -200px;
    right: -100px;
    animation: pulse 10s infinite alternate;
}

.aura-2 {
    width: 400px;
    height: 400px;
    background: #10B981;
    bottom: -100px;
    left: -50px;
    animation: pulse 15s infinite alternate-reverse;
}

.aura-3 {
    width: 300px;
    height: 300px;
    background: #8B5CF6;
    top: 20%;
    left: 40%;
    animation: drift 20s infinite linear;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 0.1;
    }

    100% {
        transform: scale(1.2);
        opacity: 0.2;
    }
}

@keyframes drift {
    0% {
        transform: translate(0, 0);
    }

    50% {
        transform: translate(100px, 50px);
    }

    100% {
        transform: translate(0, 0);
    }
}

/* General Layout & Cards */
.border-premium {
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(20px);
}

.icon-orb {
    width: 40px;
    height: 40px;
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.chart-center-label {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    pointer-events: none;
}

/* Member Profile Cards */
.member-profile-card {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: default;
    background: rgba(var(--v-theme-surface), 0.5) !important;
}

.member-profile-card:hover {
    transform: translateY(-8px);
    box-shadow: 0 20px 40px -10px rgba(0, 0, 0, 0.1) !important;
    background: rgba(var(--v-theme-surface), 0.8) !important;
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.profile-avatar {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
    transition: transform 0.4s ease;
}

.member-profile-card:hover .profile-avatar {
    transform: scale(1.1) rotate(5deg);
}

.grid-stats {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.stat-box {
    padding: 12px;
    background: rgba(var(--v-theme-on-surface), 0.03);
    border-radius: 12px;
}

/* Shared Theme */
.shared-theme {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    color: white !important;
}

.shared-theme .stat-box {
    background: rgba(255, 255, 255, 0.05);
}

.shared-theme .text-overline,
.shared-theme .text-caption {
    color: rgba(255, 255, 255, 0.6) !important;
}

.shared-theme:hover {
    background: linear-gradient(135deg, #2a3347 0%, #161e2e 100%) !important;
    border-color: rgba(255, 255, 255, 0.2) !important;
}
</style>
