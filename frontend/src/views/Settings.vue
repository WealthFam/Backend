<script setup lang="ts">
import { ref } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import {
    Settings as SettingsIcon,

    CreditCard,
    Mail,
    Users,
    Bot,
    Smartphone,
    FileText
} from 'lucide-vue-next'

// Child Components
import GeneralSettings from './settings/GeneralSettings.vue'
import AccountsSettings from './settings/AccountsSettings.vue'
import EmailSettings from './settings/EmailSettings.vue'
import FamilySettings from './settings/FamilySettings.vue'
import AISettings from './settings/AISettings.vue'
import DevicesSettings from './settings/DevicesSettings.vue'
import ParserSettings from './settings/ParserSettings.vue'

const activeTab = ref('general')
</script>

<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"></div>
            <div class="mesh-blob blob-2"></div>
            <div class="mesh-blob blob-3"></div>

            <div class="relative-pos z-10">
                <!-- Premium Header -->
                <v-row class="mb-6 align-center">
                    <v-col cols="12" md="4">
                        <div class="d-flex align-center">
                            <h1 class="text-h6 font-weight-black text-content">Settings</h1>
                        </div>
                        <p class="text-subtitle-2 text-medium-emphasis font-weight-bold mt-1 opacity-70">
                            Manage your preferences and configurations
                        </p>
                    </v-col>

                    <v-col cols="12" md="8" class="d-flex flex-column flex-md-row align-md-center justify-end gap-3">
                        <!-- Navigation Tabs -->
                        <div class="premium-pill-tabs flex-grow-1 flex-md-grow-0 d-flex overflow-x-auto">
                            <v-tabs v-model="activeTab" color="primary" density="compact" hide-slider show-arrows
                                class="rounded-xl">
                                <v-tab value="general" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <SettingsIcon :size="16" />
                                        <span>General</span>
                                    </div>
                                </v-tab>
                                <v-tab value="accounts" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <CreditCard :size="16" />
                                        <span>Accounts</span>
                                    </div>
                                </v-tab>
                                <v-tab value="tenants" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Users :size="16" />
                                        <span>Family</span>
                                    </div>
                                </v-tab>
                                <v-tab value="emails" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Mail :size="16" />
                                        <span>Emails</span>
                                    </div>
                                </v-tab>
                                <v-tab value="ai" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Bot :size="16" />
                                        <span>AI Integration</span>
                                    </div>
                                </v-tab>
                                <v-tab value="devices" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <Smartphone :size="16" />
                                        <span>Devices</span>
                                    </div>
                                </v-tab>
                                <v-tab value="parser" class="premium-tab" rounded="xl">
                                    <div class="d-flex align-center gap-2">
                                        <FileText :size="16" />
                                        <span>Parser Engine</span>
                                    </div>
                                </v-tab>
                            </v-tabs>
                        </div>
                    </v-col>
                </v-row>

                <!-- CONTENT AREA -->
                <v-window v-model="activeTab" class="overflow-visible">
                    <v-window-item value="general">
                        <GeneralSettings />
                    </v-window-item>

                    <v-window-item value="accounts">
                        <AccountsSettings />
                    </v-window-item>

                    <v-window-item value="tenants">
                        <FamilySettings />
                    </v-window-item>

                    <v-window-item value="emails">
                        <EmailSettings />
                    </v-window-item>

                    <v-window-item value="ai">
                        <AISettings />
                    </v-window-item>

                    <v-window-item value="devices">
                        <DevicesSettings />
                    </v-window-item>

                    <v-window-item value="parser">
                        <ParserSettings />
                    </v-window-item>
                </v-window>
            </div>
        </v-container>
    </MainLayout>
</template>

<style scoped>
.settings-page {
    position: relative;
    min-height: calc(100vh - 64px);
}

.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    border-radius: 50%;
    z-index: 0;
    animation: blob-float 10s infinite alternate cubic-bezier(0.4, 0, 0.2, 1);
}

.blob-1 {
    background: rgb(var(--v-theme-primary));
    width: 600px;
    height: 600px;
    top: -200px;
    right: -100px;
}

.blob-2 {
    background: rgb(var(--v-theme-secondary));
    width: 400px;
    height: 400px;
    bottom: -100px;
    left: -100px;
    animation-delay: -5s;
}

.blob-3 {
    background: rgb(var(--v-theme-success));
    width: 300px;
    height: 300px;
    top: 40%;
    left: 30%;
    animation-delay: -8s;
}

@keyframes blob-float {
    0% {
        transform: translate(0, 0) scale(1);
    }

    100% {
        transform: translate(20px, -20px) scale(1.1);
    }
}

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
