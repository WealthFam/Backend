<template>
    <v-container fluid class="pa-0">
        <!-- Hero Section -->
        <v-card class="hero-banner mb-8 pa-8" rounded="xl" elevation="0">
            <v-row align="center">
                <v-col cols="12" md="7">
                    <h1 class="text-h3 font-weight-black text-white mb-2 animate-fade-in">Smart Investing</h1>
                    <p class="text-h6 text-white opacity-80 mb-6 font-weight-medium animate-fade-in delay-1">
                        Discover top-performing mutual funds tailored to your goals.
                    </p>

                    <div class="search-container animate-fade-in delay-2">
                        <v-text-field v-model="searchQuery" placeholder="Search funds, AMC, or AMFI codes..."
                            density="comfortable" variant="solo" rounded="xl" hide-details class="modern-search-field"
                            @keyup.enter="handleSearch">
                            <template v-slot:prepend-inner>
                                <Search :size="20" class="text-primary mr-2" />
                            </template>
                            <template v-slot:append-inner>
                                <v-btn color="primary" rounded="xl" height="44" class="px-6 font-weight-bold"
                                    @click="handleSearch" :loading="isSearching">
                                    Search
                                </v-btn>
                            </template>
                        </v-text-field>
                    </div>
                </v-col>
                <v-col cols="12" md="5" class="d-none d-md-block">
                    <div class="hero-stats d-flex justify-center gap-4">
                        <div class="stat-pill">
                            <span class="text-caption">Average Returns</span>
                            <span class="text-h5 font-weight-bold">15.4%</span>
                        </div>
                        <div class="stat-pill accent">
                            <span class="text-caption">Managed AUM</span>
                            <span class="text-h5 font-weight-bold">₹10K Cr+</span>
                        </div>
                    </div>
                </v-col>
            </v-row>
        </v-card>

        <!-- Filters & Trending -->
        <div class="d-flex align-center justify-space-between mb-4 flex-wrap gap-4">
            <h2 class="text-h5 font-weight-black">Explore Markets</h2>
            <v-chip-group v-model="activeFilter" mandatory selected-class="bg-primary text-white"
                class="custom-filters">
                <v-chip v-for="filter in searchFilters" :key="filter" :value="filter" filter variant="tonal"
                    class="font-weight-bold px-4">
                    {{ filter }}
                </v-chip>
            </v-chip-group>
        </div>

        <!-- Trending Section (Only if not searching) -->
        <div v-if="!searchQuery && !isSearching" class="mb-10">
            <div class="d-flex align-center mb-6">
                <div class="section-title">Trending Today</div>
                <v-divider class="ml-4 opacity-10"></v-divider>
            </div>

            <v-slide-group show-arrows class="trending-slider">
                <v-slide-group-item v-for="fund in trendingFunds" :key="fund.schemeCode">
                    <v-card width="280" class="trending-card ma-2 pa-4" rounded="xl" hover
                        @click="openFundDetails(fund.schemeCode)">
                        <div class="d-flex align-center gap-3 mb-4">
                            <div class="trending-icon" :style="{ background: getRandomColor(fund.schemeName) }">
                                {{ fund.schemeName[0] }}
                            </div>
                            <div class="text-truncate flex-grow-1">
                                <div class="text-subtitle-2 font-weight-black text-truncate">{{ fund.schemeName }}</div>
                                <div class="text-caption opacity-60">{{ fund.category }}</div>
                            </div>
                        </div>
                        <div class="d-flex justify-space-between align-end">
                            <div>
                                <div class="text-caption font-weight-bold text-success">+{{ fund.returns3y }}%</div>
                                <div class="text-overline opacity-50">3Y Returns</div>
                            </div>
                            <div class="text-right">
                                <div class="text-subtitle-2 font-weight-bold">₹{{ fund.nav }}</div>
                                <div class="text-overline opacity-50">NAV</div>
                            </div>
                        </div>
                    </v-card>
                </v-slide-group-item>
            </v-slide-group>
        </div>

        <!-- Search Results / Collections -->
        <div v-if="searchResults.length > 0" class="results-grid animate-fade-in">
            <v-card v-for="fund in searchResults" :key="fund.schemeCode" class="premium-fund-card pa-5" rounded="xl"
                @click="openFundDetails(fund.schemeCode)">

                <div class="d-flex justify-space-between align-start mb-4">
                    <div class="icon-glow" :style="{ '--glow-color': getRandomColor(fund.schemeName) }">
                        <span>{{ fund.schemeName[0] }}</span>
                    </div>
                    <div class="d-flex flex-column align-end">
                        <v-chip size="x-small" :color="getRiskColor(fund.risk_level)" variant="flat"
                            class="font-weight-black mb-1">
                            {{ fund.risk_level }} Risk
                        </v-chip>
                        <div class="text-caption opacity-50 font-weight-bold">AUM: {{ fund.aum }}</div>
                    </div>
                </div>

                <div class="text-subtitle-1 font-weight-black line-clamp-2 mb-4 fund-title">
                    {{ fund.schemeName }}
                </div>

                <v-divider class="mb-4 opacity-5"></v-divider>

                <div class="d-flex justify-space-between align-center">
                    <div>
                        <div class="text-h6 font-weight-black text-success d-flex align-center">
                            +{{ fund.returns3y }}%
                            <TrendingUp :size="16" class="ml-1" />
                        </div>
                        <div class="text-caption font-weight-bold opacity-50">3Y Annualized</div>
                    </div>
                    <v-btn size="small" color="primary" variant="flat" rounded="lg" class="invest-btn px-4"
                        @click.stop="openInvestModal(fund)">
                        Invest
                        <Plus :size="14" class="ml-1" />
                    </v-btn>
                </div>
            </v-card>
        </div>

        <div v-else-if="!isSearching && searchQuery" class="text-center py-12 empty-state">
            <v-icon icon="mdi-magnify" size="64" class="text-disabled mb-4" />
            <div class="text-h6 text-medium-emphasis">No funds found matching "{{ searchQuery }}"</div>
            <p class="text-caption text-disabled">Try checking the spelling or searching by category</p>
        </div>

        <!-- Collections & Indices -->
        <v-row v-else class="mt-4 animate-slide-up">
            <v-col cols="12" lg="8">
                <h3 class="text-h6 font-weight-black mb-4">Curated Collections</h3>
                <v-row>
                    <v-col cols="12" sm="6" v-for="collection in curatedCollections" :key="collection.title">
                        <v-card class="collection-card pa-5" rounded="xl"
                            @click="handleCollectionClick(collection.title)">
                            <div class="d-flex align-center gap-4">
                                <v-avatar :color="collection.color + '20'" size="56" rounded="lg">
                                    <v-icon :icon="collection.icon" :color="collection.color" />
                                </v-avatar>
                                <div>
                                    <div class="text-subtitle-1 font-weight-black">{{ collection.title }}</div>
                                    <div class="text-caption opacity-60">{{ collection.subtitle }}</div>
                                </div>
                                <v-spacer></v-spacer>
                                <v-icon icon="mdi-chevron-right" class="opacity-30" />
                            </div>
                        </v-card>
                    </v-col>
                </v-row>
            </v-col>

            <v-col cols="12" lg="4">
                <h3 class="text-h6 font-weight-black mb-4">Market Pulse</h3>
                <div class="d-flex flex-column gap-4">
                    <v-card v-for="idx in marketIndices" :key="idx.name" class="index-mini-card pa-4" rounded="xl">
                        <div class="d-flex justify-space-between align-center">
                            <div>
                                <div class="text-caption font-weight-bold opacity-50">{{ idx.name }}</div>
                                <div class="text-h6 font-weight-black">{{ idx.value }}</div>
                            </div>
                            <div class="text-right">
                                <div :class="idx.isUp ? 'text-success' : 'text-error'" class="font-weight-black">
                                    {{ idx.percent }}
                                </div>
                                <div class="text-caption opacity-50">{{ idx.change }}</div>
                            </div>
                        </div>
                    </v-card>
                </div>
            </v-col>
        </v-row>

        <!-- Invest Modal -->
        <InvestModal v-model="showInvestModal" :fund="selectedFund" @success="handleSearch" />
    </v-container>
</template>
<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { Search, Plus, TrendingUp } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import InvestModal from './modals/InvestModal.vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const notification = useNotificationStore()

// State
const searchQuery = ref('')
const isSearching = ref(false)
const searchResults = ref<any[]>([])
const trendingFunds = ref<any[]>([])
const activeFilter = ref('All')
const searchFilters = ['All', 'Equity', 'Debt', 'Hybrid', 'ELSS', 'Index Funds']
const marketIndices = ref<any[]>([])

// Curated Collections Data
const curatedCollections = [
    { title: 'High Growth', subtitle: 'Aggressive equity for long term', icon: 'mdi-chart-line-variant', color: '#3b82f6' },
    { title: 'Tax Savers', subtitle: 'ELSS funds for 80C benefits', icon: 'mdi-shield-check', color: '#10b981' },
    { title: 'Top Rated', subtitle: 'Highest rated overall by experts', icon: 'mdi-star', color: '#f59e0b' },
    { title: 'Index Funds', subtitle: 'Low cost market trackers', icon: 'mdi-target', color: '#8b5cf6' },
]

// Modals
const showInvestModal = ref(false)
const selectedFund = ref<any>(null)

onMounted(async () => {
    // Mock Market Data
    marketIndices.value = [
        { name: 'NIFTY 50', value: '22,456.30', change: '+123.50', percent: '+0.55%', isUp: true },
        { name: 'SENSEX', value: '74,119.45', change: '+350.10', percent: '+0.48%', isUp: true },
        { name: 'NIFTY BANK', value: '47,820.10', change: '-85.40', percent: '-0.18%', isUp: false },
    ]

    // Initial Search (Default Recommendations)
    await handleSearch()

    // Derived Trending from search results (initially)
    trendingFunds.value = searchResults.value.filter(f => f.trending).slice(0, 6)
    if (trendingFunds.value.length === 0) trendingFunds.value = searchResults.value.slice(0, 4)
})

watch(activeFilter, () => {
    handleSearch()
})

function handleCollectionClick(title: string) {
    if (title === 'Tax Savers') activeFilter.value = 'ELSS'
    else if (title === 'Index Funds') activeFilter.value = 'Index Funds'
    else if (title === 'High Growth') activeFilter.value = 'Equity'
    else if (title === 'Top Rated') {
        activeFilter.value = 'All'
        searchQuery.value = ''
    }
    handleSearch()
}

async function handleSearch() {
    isSearching.value = true
    // results-grid transition will handle the visual swap
    try {
        const category = activeFilter.value === 'All' ? undefined : activeFilter.value
        const response = await financeApi.searchFunds(searchQuery.value || '', category)
        const data = response.data.data || response.data || []

        searchResults.value = data.map((fund: any) => ({
            schemeCode: fund.scheme_code || fund.schemeCode,
            schemeName: fund.scheme_name || fund.schemeName,
            category: fund.category || 'Mutual Fund',
            nav: fund.nav ? Number(fund.nav).toFixed(2) : 'N/A',
            returns3y: fund.returns_3y ? Number(fund.returns_3y).toFixed(2) : 'N/A',
            risk_level: fund.risk_level || 'Moderate',
            aum: fund.aum || 'N/A',
            trending: fund.trending || false,
            rating: fund.rating || 4,
            ...fund
        }))

        if (searchResults.value.length === 0 && searchQuery.value) {
            notification.info(`No funds found for "${searchQuery.value}"`)
        }
    } catch (error) {
        console.error('Search failed:', error)
        notification.error('Failed to search funds. Please try again.')
    } finally {
        isSearching.value = false
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

function getRiskColor(risk: string) {
    switch (risk?.toLowerCase()) {
        case 'low': return 'success'
        case 'moderate': return 'info'
        case 'high': return 'warning'
        case 'very high': return 'error'
        default: return 'primary'
    }
}

function openFundDetails(schemeCode: string) {
    router.push(`/mutual-funds/explore/${schemeCode}`)
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
/* Hero Banner */
.hero-banner {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    position: relative;
    overflow: hidden;
}

.hero-banner::before {
    content: '';
    position: absolute;
    top: -20%;
    right: -10%;
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(var(--v-theme-primary), 0.15) 0%, transparent 70%);
    border-radius: 50%;
}

.modern-search-field :deep(.v-field) {
    background: white !important;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1) !important;
    border: none !important;
}

.stat-pill {
    background: rgba(255, 255, 255, 0.05);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 1rem 1.5rem;
    border-radius: 20px;
    color: white;
    display: flex;
    flex-direction: column;
}

.stat-pill.accent {
    background: rgba(var(--v-theme-primary), 0.1);
    border-color: rgba(var(--v-theme-primary), 0.2);
}

/* Section Titles */
.section-title {
    font-size: 1.25rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: rgba(var(--v-theme-on-background), 0.4);
}

/* Trending Slider */
.trending-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(15px);
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.trending-card:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 12px 30px -10px rgba(0, 0, 0, 0.1) !important;
    border-color: rgba(var(--v-theme-primary), 0.2) !important;
}

.trending-icon {
    width: 32px;
    height: 32px;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
}

/* Fund Cards */
.results-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
    gap: 1.5rem;
}

.premium-fund-card {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    transition: all 0.3s ease;
    cursor: pointer;
}

.premium-fund-card:hover {
    transform: translateY(-5px);
    background: rgba(var(--v-theme-surface), 1) !important;
    box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.15) !important;
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.icon-glow {
    width: 48px;
    height: 48px;
    background: var(--glow-color);
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-size: 1.5rem;
    font-weight: 900;
    box-shadow: 0 4px 15px -2px var(--glow-color);
    opacity: 0.9;
}

.fund-title {
    color: rgb(var(--v-theme-on-surface));
    min-height: 56px;
    line-height: 1.4;
}

/* Collection Cards */
.collection-card {
    border: 1px solid rgba(var(--v-border-color), 0.05) !important;
    transition: all 0.2s ease;
    cursor: pointer;
}

.collection-card:hover {
    background: rgba(var(--v-theme-primary), 0.03) !important;
    border-color: rgba(var(--v-theme-primary), 0.2) !important;
    transform: translateX(4px);
}

.index-mini-card {
    border: 1px solid rgba(var(--v-border-color), 0.05) !important;
    background: rgba(var(--v-theme-surface), 0.5) !important;
}

/* Animations */
.animate-fade-in {
    animation: fadeIn 0.8s ease forwards;
}

.delay-1 {
    animation-delay: 0.1s;
}

.delay-2 {
    animation-delay: 0.2s;
}

@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-slide-up {
    animation: slideUp 0.6s cubic-bezier(0.23, 1, 0.32, 1) forwards;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(30px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
