<script setup lang="ts">
import { ref } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { FileText, Search, Upload } from 'lucide-vue-next'
import PortfolioTab from './mutual-funds/PortfolioTab.vue'
import SearchTab from './mutual-funds/SearchTab.vue'
import ImportTab from './mutual-funds/ImportTab.vue'

// State
const activeTab = ref('portfolio')
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <div class="relative-pos z-10">
                <!-- Premium Header -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="4">
                        <div class="d-flex align-center">
                            <h1 class="text-h6 font-weight-black text-content">Mutual Funds</h1>
                        </div>
                        <p class="text-subtitle-2 text-medium-emphasis font-weight-bold mt-1 opacity-70">
                            Track your portfolio and analyze performance
                        </p>
                    </v-col>

                    <v-col cols="12" md="8" class="d-flex flex-column flex-md-row align-md-center justify-end gap-3">
                        <!-- Navigation Tabs -->
                        <div class="premium-pill-tabs flex-grow-1 flex-md-grow-0 d-flex overflow-x-auto">
                            <v-tabs v-model="activeTab" color="primary" density="compact" hide-slider
                                class="rounded-xl">
                                <v-tab value="portfolio" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <FileText :size="16" />
                                        <span>Portfolio</span>
                                    </div>
                                </v-tab>
                                <v-tab value="search" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Search :size="16" />
                                        <span>Search & Add</span>
                                    </div>
                                </v-tab>
                                <v-tab value="import" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Upload :size="16" />
                                        <span>Import CAS</span>
                                    </div>
                                </v-tab>
                            </v-tabs>
                        </div>
                    </v-col>
                </v-row>

                <!-- CONTENT AREA -->
                <v-window v-model="activeTab" class="overflow-visible">
                    <!-- PORTFOLIO TAB -->
                    <v-window-item value="portfolio" class="overflow-visible">
                        <PortfolioTab :active="activeTab === 'portfolio'" />
                    </v-window-item>

                    <!-- SEARCH TAB -->
                    <v-window-item value="search" class="overflow-visible">
                        <SearchTab />
                    </v-window-item>

                    <!-- IMPORT TAB -->
                    <v-window-item value="import">
                        <ImportTab />
                    </v-window-item>
                </v-window>
            </div>
        </v-container>
    </MainLayout>
</template>

<style scoped>
/* Relies on base.css dashboard-page */

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

/* Premium Tabs */
.premium-pill-tabs {
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(10px);
    padding: 6px;
    border-radius: 24px;
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-tab {
    text-transform: none !important;
    letter-spacing: 0;
    font-weight: 700;
    font-size: 0.9rem;
    color: rgba(var(--v-theme-on-surface), 0.6);
    transition: all 0.3s ease;
    min-width: 120px;
}

.premium-tab.v-tab--selected {
    background: rgb(var(--v-theme-primary));
    color: white !important;
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}
</style>
