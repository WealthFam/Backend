<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Animated Mesh Background (Consistent with Categories.vue) -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Header (Title left, Tabs & Actions right) -->
                <v-row class="mb-10 align-center">
                    <v-col cols="12" md="6">
                        <h1 class="text-h6 font-weight-black mb-1">Insights</h1>
                        <p class="text-subtitle-2 text-on-surface opacity-70 font-weight-bold d-flex align-center">
                            Strategy and forecasting
                            <v-chip v-if="authStore.selectedMemberId" size="x-small" color="primary" variant="flat"
                                class="ml-3 font-weight-black letter-spacing-1">
                                MEMBER FILTER ACTIVE
                            </v-chip>
                        </p>
                    </v-col>

                    <v-col cols="12" md="6" class="d-flex justify-md-end align-center gap-3">
                        <!-- Account Selector -->
                        <v-select v-if="activeTab === 0" v-model="selectedAccount"
                            :items="[{ title: 'All Accounts', value: '' }, ...accountOptions]"
                            placeholder="All Accounts" density="compact" variant="outlined" hide-details
                            class="trend-cat-premium" rounded="pill" menu-icon=""
                            style="background: rgba(var(--v-theme-surface), 0.7); max-width: 200px;">
                            <template v-slot:prepend-inner>
                                <Wallet :size="16" class="text-primary mr-2" />
                            </template>
                            <template v-slot:append-inner>
                                <ChevronDown :size="16" class="text-primary opacity-70" />
                            </template>
                        </v-select>

                        <!-- Segmented Tab Switcher (Match Categories.vue) -->
                        <div class="glass-card pa-1 border rounded-pill d-flex"
                            style="background: rgba(var(--v-theme-surface), 0.5)">
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-8 letter-spacing-1"
                                :color="activeTab === 0 ? 'primary' : 'transparent'"
                                :class="activeTab !== 0 ? 'text-medium-emphasis' : 'elevation-2'"
                                @click="activeTab = 0">
                                Analytics
                            </v-btn>
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-8 letter-spacing-1"
                                :color="activeTab === 1 ? 'primary' : 'transparent'"
                                :class="activeTab !== 1 ? 'text-medium-emphasis' : 'elevation-2'"
                                @click="activeTab = 1">
                                Recurring
                            </v-btn>
                        </div>

                        <v-btn v-if="activeTab === 1" color="primary" @click="recurringTabRef?.openAddModal()"
                            rounded="pill" height="40" class="text-none font-weight-black px-6 ml-2" elevation="2">
                            <template v-slot:prepend>
                                <Plus :size="18" stroke-width="3" />
                            </template>
                            Add Subscription
                        </v-btn>
                    </v-col>
                </v-row>

                <v-window v-model="activeTab" class="bg-transparent overflow-visible">
                    <!-- ANALYTICS TAB -->
                    <v-window-item :value="0">
                        <AnalyticsTab :selected-account="selectedAccount" />
                    </v-window-item>

                    <!-- RECURRING TAB -->
                    <v-window-item :value="1">
                        <RecurringTab ref="recurringTabRef" />
                    </v-window-item>
                </v-window>
            </div>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { useFinanceStore } from '@/stores/finance'
import { useAuthStore } from '@/stores/auth'
import AnalyticsTab from '@/views/insights/AnalyticsTab.vue'
import RecurringTab from '@/views/insights/RecurringTab.vue'
import { Wallet, Plus, ChevronDown } from 'lucide-vue-next'

const store = useFinanceStore()
const authStore = useAuthStore()

const activeTab = ref(0)
const selectedAccount = ref('')
const recurringTabRef = ref<InstanceType<typeof RecurringTab> | null>(null)

import { onMounted } from 'vue'

onMounted(() => {
    store.fetchAll(authStore.selectedMemberId || undefined)
})

// Requirement 2: Reset account filter and re-fetch data when global member changes
import { watch } from 'vue'
watch(() => authStore.selectedMemberId, () => {
    selectedAccount.value = ''
    store.fetchAll(authStore.selectedMemberId || undefined)
})

const accountOptions = computed(() => {
    // Audit check: ensure store accounts are present
    if (!store.accounts || store.accounts.length === 0) return []

    return store.accounts
        .filter(a => {
            // Requirement 1: Only show verified accounts
            if (!a.is_verified) return false

            // Requirement 2: Respect global user filter
            const selectedMemberId = authStore.selectedMemberId
            if (!selectedMemberId) return true

            // Show accounts owned by selected member OR shared accounts (owner_id is null)
            // owner_id being null usually means shared/tenant-level
            return a.owner_id === selectedMemberId || !a.owner_id
        })
        .map(a => ({ title: a.name, value: a.id }))
})
</script>

<style scoped>
.dashboard-page {
    position: relative;
    min-height: calc(100vh - 64px);
}

.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    border-radius: 50%;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.gap-3 {
    gap: 12px;
}

.account-select-premium :deep(.v-field__outline) {
    --v-field-border-opacity: 0.1;
    transition: border-color 0.3s ease;
}

.account-select-premium:hover :deep(.v-field__outline) {
    --v-field-border-opacity: 0.4;
    border-color: rgb(var(--v-theme-primary)) !important;
}

.glass-card {
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

:deep(.v-window) {
    overflow: visible !important;
}
</style>
