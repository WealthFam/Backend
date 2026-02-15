<template>
    <v-container fluid class="pa-0">
        <!-- Search Header -->
        <div class="d-flex align-center gap-3 mb-6 flex-wrap">
            <v-chip-group v-model="activeFilter" mandatory selected-class="text-primary" class="d-inline-block">
                <v-chip v-for="filter in searchFilters" :key="filter" :value="filter" filter variant="outlined"
                    class="font-weight-bold">
                    {{ filter }}
                </v-chip>
            </v-chip-group>

            <v-spacer class="d-none d-md-block"></v-spacer>

            <v-text-field v-model="searchQuery" placeholder="Search funds or AMFI codes..." density="comfortable"
                variant="outlined" rounded="lg" hide-details style="min-width: 300px; max-width: 100%;"
                bg-color="rgba(var(--v-theme-surface), 0.8)" @keyup.enter="handleSearch">
                <template v-slot:prepend-inner>
                    <Search :size="18" class="text-medium-emphasis" />
                </template>
            </v-text-field>
            <v-btn color="primary" height="40" rounded="lg" class="px-6 font-weight-bold" @click="handleSearch"
                :loading="isSearching">
                Search
            </v-btn>
        </div>

        <!-- Search Results -->
        <div v-if="searchResults.length > 0" class="results-grid">
            <v-card v-for="fund in searchResults" :key="fund.schemeCode"
                class="premium-glass-card hover-lift cursor-pointer pa-5" rounded="xl"
                @click="openFundDetails(fund.schemeCode)">

                <div class="d-flex align-start justify-space-between mb-3">
                    <div class="icon-box" :style="{ background: getRandomColor(fund.schemeName) }">
                        {{ fund.schemeName[0] }}
                    </div>
                    <v-chip size="x-small" variant="outlined" class="font-weight-bold ml-2">Direct • Growth</v-chip>
                </div>

                <div class="text-subtitle-1 font-weight-black text-content line-clamp-2 mb-3" style="min-height: 56px;">
                    {{ fund.schemeName }}
                </div>

                <div class="d-flex justify-space-between align-center mt-2 pt-3 border-t border-opacity-10">
                    <div>
                        <div class="text-caption text-medium-emphasis font-weight-medium">3Y Returns</div>
                        <div class="text-body-1 font-weight-black text-success">+{{ fund.returns3y }}%</div>
                    </div>
                    <v-btn size="small" color="primary" variant="flat" rounded="lg" class="px-4 font-weight-bold"
                        @click.stop="openInvestModal(fund)">
                        Invest
                        <Plus :size="14" class="ml-1" />
                    </v-btn>
                </div>
            </v-card>
        </div>

        <div v-else-if="!isSearching && searchQuery" class="text-center py-12">
            <Search :size="48" class="text-disabled mb-4 mx-auto" style="opacity: 0.2" />
            <div class="text-h6 text-medium-emphasis">No funds found matching "{{ searchQuery }}"</div>
            <p class="text-caption text-disabled">Try checking the spelling or searching by AMFI code</p>
        </div>

        <!-- Market Pulse / Discovery -->
        <div v-else class="mt-4 animate-slide-up">
            <div class="d-flex align-center justify-space-between mb-6">
                <h3 class="text-h6 font-weight-black d-flex align-center">
                    Market Pulse
                    <span class="live-dot ml-2"></span>
                </h3>
            </div>

            <v-row>
                <v-col v-for="idx in marketIndices" :key="idx.name" cols="12" md="4">
                    <v-card class="premium-glass-card pa-5" rounded="xl">
                        <div class="d-flex justify-space-between align-start mb-4">
                            <div>
                                <div class="text-caption font-weight-bold text-medium-emphasis mb-1">{{ idx.name }}
                                </div>
                                <div class="text-h5 font-weight-black text-content">{{ idx.value }}</div>
                            </div>
                            <div class="text-right">
                                <div class="text-body-2 font-weight-black"
                                    :class="idx.isUp ? 'text-success' : 'text-error'">
                                    {{ idx.change }}
                                </div>
                                <div class="text-caption font-weight-bold"
                                    :class="idx.isUp ? 'text-success' : 'text-error'">
                                    {{ idx.percent }}
                                </div>
                            </div>
                        </div>

                        <!-- Mini Sparkline -->
                        <div class="sparkline-container" v-if="idx.sparkline">
                            <svg width="100%" height="40" viewBox="0 0 60 20" preserveAspectRatio="none">
                                <path :d="getSparklinePath(idx.sparkline)" fill="none" stroke-width="2"
                                    :stroke="idx.isUp ? '#10b981' : '#f43f5e'" stroke-linecap="round"
                                    stroke-linejoin="round" />
                                <path :d="getSparklinePath(idx.sparkline) + ' V 20 H 0 Z'"
                                    :fill="idx.isUp ? 'url(#gradUp)' : 'url(#gradDown)'" opacity="0.2" stroke="none" />
                                <defs>
                                    <linearGradient id="gradUp" x1="0" x2="0" y1="0" y2="1">
                                        <stop offset="0%" stop-color="#10b981" />
                                        <stop offset="100%" stop-color="#10b981" stop-opacity="0" />
                                    </linearGradient>
                                    <linearGradient id="gradDown" x1="0" x2="0" y1="0" y2="1">
                                        <stop offset="0%" stop-color="#f43f5e" />
                                        <stop offset="100%" stop-color="#f43f5e" stop-opacity="0" />
                                    </linearGradient>
                                </defs>
                            </svg>
                        </div>
                    </v-card>
                </v-col>
            </v-row>

            <!-- Curated Collections (Placeholder for future) -->
            <div class="mt-8">
                <h3 class="text-h6 font-weight-black mb-4">Curated Collections</h3>
                <v-row>
                    <v-col cols="12" md="3" v-for="title in ['High Growth', 'Tax Savers', 'Top Rated', 'Index Funds']"
                        :key="title">
                        <v-card class="premium-glass-card pa-4 cursor-pointer hover-lift" rounded="xl">
                            <div class="d-flex align-center justify-space-between">
                                <span class="font-weight-bold text-body-2">{{ title }}</span>
                                <ArrowRight :size="16" class="text-medium-emphasis" />
                            </div>
                        </v-card>
                    </v-col>
                </v-row>
            </div>
        </div>

        <!-- Invest Modal -->
        <InvestModal v-model="showInvestModal" :fund="selectedFund" @success="handleSearch" />
    </v-container>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Search, Plus, ArrowRight } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import InvestModal from './modals/InvestModal.vue'

const router = useRouter()

// State
const searchQuery = ref('')
const isSearching = ref(false)
const searchResults = ref<any[]>([])
const activeFilter = ref('All')
const searchFilters = ['All', 'Equity', 'Debt', 'Hybrid', 'ELSS', 'Index Funds']
const marketIndices = ref<any[]>([])

// Modals
const showInvestModal = ref(false)
const selectedFund = ref<any>(null)

// Mock Market Data (Replace with API if available)
onMounted(() => {
    // In a real app, this would be an API call
    marketIndices.value = [
        { name: 'NIFTY 50', value: '22,456.30', change: '+123.50', percent: '+0.55%', isUp: true, sparkline: [22300, 22350, 22400, 22380, 22420, 22456] },
        { name: 'SENSEX', value: '74,119.45', change: '+350.10', percent: '+0.48%', isUp: true, sparkline: [73800, 73900, 74000, 73950, 74119] },
        { name: 'NIFTY BANK', value: '47,820.10', change: '-85.40', percent: '-0.18%', isUp: false, sparkline: [47900, 47950, 47850, 47880, 47820] },
    ]
})

function handleSearch() {
    if (!searchQuery.value) return
    isSearching.value = true

    // Simulate API search
    setTimeout(() => {
        // Mock results for now
        searchResults.value = Array.from({ length: 6 }).map((_, i) => ({
            schemeCode: `12345${i}`,
            schemeName: `ICICI Prudential Bluechip Fund ${searchQuery.value} ${i + 1}`,
            category: 'Equity',
            nav: (100 + Math.random() * 50).toFixed(2),
            returns3y: (Math.random() * 20 + 10).toFixed(2)
        }))
        isSearching.value = false
    }, 800)
}

function getSparklinePath(points: number[]): string {
    if (!points || points.length < 2) return ''
    const width = 60
    const height = 20
    const min = Math.min(...points)
    const max = Math.max(...points)
    const range = max - min || 1
    const stepX = width / (points.length - 1)

    return points.map((p, i) => {
        const x = i * stepX
        const y = height - ((p - min) / range) * height
        return `${i === 0 ? 'M' : 'L'} ${x},${y}`
    }).join(' ')
}

function getRandomColor(name: string) {
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    let hash = 0
    for (let i = 0; i < name.length; i++) {
        hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
}

function openFundDetails(schemeCode: string) {
    router.push(`/mutual-funds/${schemeCode}?type=aggregate`)
}

function openInvestModal(fund: any) {
    selectedFund.value = {
        ...fund,
        scheme_code: fund.schemeCode,
        scheme_name: fund.schemeName
    }
    showInvestModal.value = true
}
</script>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
    box-shadow: none !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hover-lift:hover {
    transform: translateY(-4px);
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
    background: rgba(var(--v-theme-surface), 0.85) !important;
    box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.1) !important;
}

.icon-box {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: 900;
    font-size: 1.2rem;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 1.5rem;
}

.live-dot {
    width: 8px;
    height: 8px;
    background-color: rgb(var(--v-theme-success));
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 0 rgba(var(--v-theme-success), 0.4);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% {
        box-shadow: 0 0 0 0 rgba(var(--v-theme-success), 0.7);
    }

    70% {
        box-shadow: 0 0 0 10px rgba(var(--v-theme-success), 0);
    }

    100% {
        box-shadow: 0 0 0 0 rgba(var(--v-theme-success), 0);
    }
}

.animate-slide-up {
    animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
