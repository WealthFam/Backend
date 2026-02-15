<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <!-- Header -->
                <v-row class="mb-10 align-center">
                    <v-col cols="12" md="6">
                        <h1 class="text-h6 font-weight-black mb-1">Categories</h1>
                        <p class="text-subtitle-2 text-on-surface opacity-70 font-weight-bold">
                            Manage your spending categories and classification rules
                        </p>
                    </v-col>

                    <v-col cols="12" md="6" class="d-flex justify-md-end align-center">
                        <!-- Redesigned Tab Switcher (Segmented Control) -->
                        <div class="glass-card pa-1 border rounded-pill d-flex"
                            style="background: rgba(var(--v-theme-surface), 0.5)">
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-8 letter-spacing-1"
                                :color="activeTab === 'categories' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'categories' ? 'text-disabled' : ''"
                                @click="activeTab = 'categories'">
                                Categories
                            </v-btn>
                            <v-btn variant="flat" rounded="pill" height="40"
                                class="text-none font-weight-black px-8 letter-spacing-1"
                                :color="activeTab === 'rules' ? 'primary' : 'transparent'"
                                :class="activeTab !== 'rules' ? 'text-disabled' : ''" @click="activeTab = 'rules'">
                                Rules
                            </v-btn>
                        </div>
                    </v-col>
                </v-row>

                <v-window v-model="activeTab" class="bg-transparent overflow-visible">
                    <v-window-item value="categories">
                        <CategoriesTab />
                    </v-window-item>
                    <v-window-item value="rules">
                        <RulesTab />
                    </v-window-item>
                </v-window>
            </div>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import CategoriesTab from '@/views/categories/CategoriesTab.vue'
import RulesTab from '@/views/categories/RulesTab.vue'

const activeTab = ref('categories')
</script>

<style scoped>
/* Vuetify handles the layout, minimal custom CSS needed */
</style>
