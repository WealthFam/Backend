<script lang="ts">
import { ref } from 'vue'

// Cache to keep results persistent when modal is toggled
const backendResults = ref<any[]>([])
const isSearching = ref(false)

export default {
    name: 'GlobalSearch'
}
</script>

<script setup lang="ts">
import { onMounted, onUnmounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
    Search,
    LayoutDashboard,
    Wallet,
    PieChart,
    Sparkles,
    Coins,
    Target,
    Landmark,
    TrendingUp,
    Plus,
    History,
    ArrowRight,
    CreditCard,
    Command,
    Store
} from 'lucide-vue-next'
import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
    modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue'])

const router = useRouter()
const auth = useAuthStore()
const { formatAmount } = useCurrency()

const searchQuery = ref('')
const selectedIndex = ref(0)
let debounceTimer: any = null

const navItems = [
    { title: 'Dashboard', icon: LayoutDashboard, to: '/' },
    { title: 'Ledger', icon: Wallet, to: '/transactions' },
    { title: 'Budgets', icon: PieChart, to: '/budgets' },
    { title: 'Insights', icon: Sparkles, to: '/insights' },
    { title: 'Funds', icon: Coins, to: '/mutual-funds' },
    { title: 'Goals', icon: Target, to: '/investment-goals' }
]

const quickActions = [
    { title: 'Add Transaction', icon: Plus, to: '/transactions?action=new' },
    { title: 'Import CAS', icon: History, to: '/mutual-funds?tab=import' },
]

async function performSearch() {
    if (!searchQuery.value.trim()) {
        backendResults.value = []
        return
    }

    isSearching.value = true
    try {
        const userId = auth.selectedMemberId || undefined
        const res = await financeApi.globalSearch(searchQuery.value, userId)

        // Map backend results to include icons and formatting
        backendResults.value = (res.data || []).map((item: any) => {
            let icon = Search
            let color = 'primary'
            let to = item.route_params?.to || '/'

            if (item.type === 'account') { icon = CreditCard; color = 'info'; to = `/transactions?accountId=${item.id}`; }
            if (item.type === 'loan') { icon = Landmark; color = 'error'; to = `/loans/${item.id}`; }
            if (item.type === 'goal') { icon = Target; color = 'success'; to = '/investment-goals'; }
            if (item.type === 'fund') { icon = TrendingUp; color = 'primary'; to = `/mutual-funds/${item.code}?type=aggregate`; }
            if (item.type === 'merchant') { icon = Store; color = 'warning'; to = `/merchants/${encodeURIComponent(item.id)}`; }

            return {
                ...item,
                icon,
                color,
                to,
                displayValue: item.value ? formatAmount(Number(item.value)) : null
            }
        })
    } catch (e) {
        console.error("Search failed", e)
    } finally {
        isSearching.value = false
    }
}

watch(searchQuery, (newVal) => {
    selectedIndex.value = 0
    if (debounceTimer) clearTimeout(debounceTimer)

    if (newVal.trim()) {
        debounceTimer = setTimeout(() => {
            performSearch()
        }, 300)
    } else {
        backendResults.value = []
    }
})

watch(() => props.modelValue, (newVal) => {
    if (newVal) {
        searchQuery.value = ''
        selectedIndex.value = 0
    }
})

// Consolidated list for keyboard navigation
const flattenedResults = computed(() => {
    if (!searchQuery.value.trim()) {
        return [...navItems, ...quickActions]
    }
    return backendResults.value
})

function navigateTo(item: any) {
    if (item.to) {
        router.push(item.to)
    }
    emit('update:modelValue', false)
}

function handleKeyDown(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
        e.preventDefault()
        selectedIndex.value = (selectedIndex.value + 1) % flattenedResults.value.length
    } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        selectedIndex.value = (selectedIndex.value - 1 + flattenedResults.value.length) % flattenedResults.value.length
    } else if (e.key === 'Enter') {
        if (flattenedResults.value[selectedIndex.value]) {
            navigateTo(flattenedResults.value[selectedIndex.value])
        }
    } else if (e.key === 'Escape') {
        emit('update:modelValue', false)
    }
}

onMounted(() => {
    window.addEventListener('keydown', handleGlobalKeyDown)
})

onUnmounted(() => {
    window.removeEventListener('keydown', handleGlobalKeyDown)
})

function handleGlobalKeyDown(e: KeyboardEvent) {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        emit('update:modelValue', !props.modelValue)
    }
}
</script>

<template>
    <v-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" width="680"
        content-class="search-dialog" @keydown="handleKeyDown">
        <v-card class="search-modal-card" elevation="24">
            <!-- Search Header -->
            <div class="search-header pa-5 d-flex align-center">
                <Search :size="20" class="text-primary mr-4 opacity-70" />
                <input v-model="searchQuery" type="text" class="search-input text-h6 font-weight-bold"
                    placeholder="Search accounts, loans, funds..." autofocus @input="selectedIndex = 0">

                <div class="d-flex align-center gap-3">
                    <v-progress-circular v-if="isSearching" indeterminate size="18" width="2" color="primary" />
                    <div
                        class="shortcut-hint d-none d-sm-flex align-center px-2 py-1 rounded bg-surface-variant bg-opacity-10 text-tiny font-weight-black">
                        ESC
                    </div>
                </div>
            </div>

            <v-divider class="opacity-10"></v-divider>

            <!-- Results / Quick Access Area -->
            <div class="results-area" style="max-height: 480px; overflow-y: auto;">

                <!-- Empty State: Quick Access & Actions -->
                <div v-if="!searchQuery.trim()" class="pa-6 pb-8">
                    <div class="mb-6">
                        <div class="text-overline font-weight-black text-primary mb-4 opacity-60 letter-spacing-2">Quick
                            Access</div>
                        <div class="quick-nav-row d-flex flex-wrap items-center gap-2">
                            <div v-for="(item, idx) in navItems" :key="item.title" @click="navigateTo(item)"
                                @mouseenter="selectedIndex = idx"
                                class="quick-access-chip d-flex align-center px-4 py-2 border rounded-pill transition-all cursor-pointer"
                                :class="{ 'chip-selected': selectedIndex === idx }">
                                <component :is="item.icon" :size="16" class="mr-2 opacity-70" />
                                <span class="text-subtitle-2 font-weight-bold">{{ item.title }}</span>
                            </div>
                        </div>
                    </div>

                    <div>
                        <div class="text-overline font-weight-black text-primary mb-4 opacity-60 letter-spacing-2">Quick
                            Actions</div>
                        <div class="quick-nav-row d-flex flex-wrap items-center gap-2">
                            <div v-for="(item, idx) in quickActions" :key="item.title" @click="navigateTo(item)"
                                @mouseenter="selectedIndex = navItems.length + idx"
                                class="quick-access-chip d-flex align-center px-4 py-2 border rounded-pill transition-all cursor-pointer action-chip"
                                :class="{ 'chip-selected': selectedIndex === navItems.length + idx }">
                                <component :is="item.icon" :size="16" class="mr-2 opacity-70" />
                                <span class="text-subtitle-2 font-weight-bold">{{ item.title }}</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Search Results -->
                <div v-else class="py-2">
                    <div v-if="backendResults.length === 0 && !isSearching" class="pa-12 text-center">
                        <div class="text-h1 mb-4">🔍</div>
                        <h3 class="text-h6 font-weight-black mb-1">No results for "{{ searchQuery }}"</h3>
                        <p class="text-body-2 text-medium-emphasis">Try searching for Bank name, Fund scheme, or Loan ID
                        </p>
                    </div>

                    <div v-else>
                        <transition-group name="list">
                            <div v-for="(item, idx) in backendResults" :key="item.id || item.code || item.title"
                                @click="navigateTo(item)" @mouseenter="selectedIndex = idx"
                                class="search-item d-flex align-center mx-3 pa-3 rounded-xl mb-1 transition-all cursor-pointer"
                                :class="{ 'item-selected': selectedIndex === idx }">

                                <div class="item-icon-box mr-4" :class="item.color || 'primary'">
                                    <component :is="item.icon" :size="18" />
                                </div>

                                <div class="flex-grow-1 min-width-0">
                                    <div class="d-flex align-center justify-space-between mb-0.5">
                                        <span class="text-subtitle-1 font-weight-black text-truncate">{{ item.title
                                        }}</span>
                                        <span v-if="item.displayValue"
                                            class="text-subtitle-2 font-weight-bold text-primary ml-4">
                                            {{ item.displayValue }}
                                        </span>
                                    </div>
                                    <div
                                        class="text-caption font-weight-bold text-medium-emphasis opacity-60 text-truncate text-uppercase">
                                        {{ item.subtitle }}
                                    </div>
                                </div>

                                <div class="go-icon ml-4 opacity-0 transition-all"
                                    :class="{ 'opacity-100': selectedIndex === idx }">
                                    <ArrowRight :size="16" class="text-primary" />
                                </div>
                            </div>
                        </transition-group>
                    </div>
                </div>
            </div>

            <!-- Enhanced Footer -->
            <div class="search-footer-wrapper">
                <v-divider class="opacity-10"></v-divider>
                <div class="search-footer pa-4 px-6 d-flex align-center justify-space-between">
                    <div class="d-flex align-center gap-6">
                        <div class="d-flex align-center gap-2 text-tiny font-weight-black opacity-40">
                            <div class="key-box">↑</div>
                            <div class="key-box">↓</div>
                            <span>Navigate</span>
                        </div>
                        <div class="d-flex align-center gap-2 text-tiny font-weight-black opacity-40">
                            <div class="key-box px-2">ENTER</div>
                            <span>Select</span>
                        </div>
                    </div>

                    <div class="d-flex align-center gap-2 text-primary opacity-80">
                        <Command :size="14" />
                        <span class="text-tiny font-weight-black letter-spacing-1">GLOBAL SEARCH V2</span>
                    </div>
                </div>
            </div>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.search-dialog :deep(.v-overlay__content) {
    margin-top: 10vh !important;
}

.search-modal-card {
    background: rgba(var(--v-theme-surface), 0.9) !important;
    backdrop-filter: blur(24px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    border-radius: 24px !important;
    overflow: hidden;
}

.search-input {
    flex: 1;
    background: transparent;
    border: none;
    outline: none;
    color: rgb(var(--v-theme-on-surface));
    caret-color: rgb(var(--v-theme-primary));
}

.search-input::placeholder {
    color: rgba(var(--v-theme-on-surface), 0.3);
}

.results-area::-webkit-scrollbar {
    width: 4px;
}

.results-area::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 4px;
}

/* Quick Access Chips */
.quick-access-chip {
    background: rgba(var(--v-theme-on-surface), 0.03);
    border-color: rgba(var(--v-border-color), 0.05) !important;
    color: rgba(var(--v-theme-on-surface), 0.7);
}

.chip-selected {
    background: rgba(var(--v-theme-primary), 0.1) !important;
    border-color: rgba(var(--v-theme-primary), 0.2) !important;
    color: rgb(var(--v-theme-primary)) !important;
    transform: translateY(-1px);
}

.action-chip {
    border-style: dashed !important;
}

/* Search Items */
.search-item {
    border: 1px solid transparent;
}

.item-selected {
    background: rgba(var(--v-theme-on-surface), 0.04) !important;
    border-color: rgba(var(--v-border-color), 0.05) !important;
}

.item-icon-box {
    width: 40px;
    height: 40px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--v-theme-on-surface), 0.05);
    color: rgba(var(--v-theme-on-surface), 0.6);
    transition: all 0.3s;
}

.item-icon-box.primary {
    color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.08);
}

.item-icon-box.success {
    color: #10b981;
    background: rgba(16, 185, 129, 0.08);
}

.item-icon-box.error {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.08);
}

.item-icon-box.info {
    color: #0ea5e9;
    background: rgba(14, 165, 233, 0.08);
}

.item-selected .item-icon-box.primary {
    background: rgb(var(--v-theme-primary));
    color: white;
}

.item-selected .item-icon-box.success {
    background: #10b981;
    color: white;
}

.item-selected .item-icon-box.error {
    background: #ef4444;
    color: white;
}

.item-selected .item-icon-box.info {
    background: #0ea5e9;
    color: white;
}

/* Footer */
.search-footer-wrapper {
    background: rgba(var(--v-theme-on-surface), 0.02);
}

.key-box {
    background: rgba(var(--v-theme-on-surface), 0.05);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 4px;
    min-width: 18px;
    text-align: center;
    line-height: 18px;
    padding: 0 4px;
}

.letter-spacing-1 {
    letter-spacing: 1px !important;
}

.letter-spacing-2 {
    letter-spacing: 2px !important;
}

.opacity-0 {
    opacity: 0;
}

.opacity-100 {
    opacity: 1;
}

.transition-all {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Transitions */
.list-enter-active,
.list-leave-active {
    transition: all 0.3s ease;
}

.list-enter-from,
.list-leave-to {
    opacity: 0;
    transform: translateX(10px);
}
</style>
