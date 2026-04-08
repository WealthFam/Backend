<script setup lang="ts">
import { ref } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { useRouter, useRoute } from 'vue-router'
import { useTheme } from 'vuetify'
import {
    LayoutDashboard,
    Wallet,
    PieChart,
    Sparkles,
    Coins,
    Settings,
    Bell,
    LogOut,
    User as UserIcon,
    Target,
    Layers,
    Landmark,
    Tags,
    Menu,
    Moon,
    Sun,
    Users,
    ChevronDown,
    Search,
    RefreshCw,
    ShieldCheck,
    Zap
} from 'lucide-vue-next'
import { onUnmounted, computed, watch } from 'vue'
import { useMutualFundStore } from '@/stores/finance/mutualFunds'
import ToastContainer from '@/components/ToastContainer.vue'
import GlobalSearch from '@/components/common/GlobalSearch.vue'
import { useWebSockets } from '@/composables/useWebSockets'

const { notifications, clearNotifications } = useWebSockets()
const unreadCount = computed(() => notifications.value.length)

// Bell Ring Animation State
const isBellRinging = ref(false)
watch(unreadCount, (newVal, oldVal) => {
    if (newVal > oldVal) {
        isBellRinging.value = true
        setTimeout(() => {
            isBellRinging.value = false
        }, 1000)
    }
})

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const theme = useTheme()

// Version info
const appVersion = __APP_VERSION__
const appBuild = __APP_BUILD__

// Navigation State
const drawer = ref(true)
const rail = ref(true)

// Theme Toggle
function toggleTheme() {
    theme.global.name.value = theme.global.current.value.dark ? 'wealthFamTheme' : 'wealthFamDark'
}

// Global Search State
const showSearch = ref(false)

// User Menu State
const selectedAvatar = ref(localStorage.getItem('user_avatar') || 'default')

const AVATARS: Record<string, string> = {
    'default': '👤',
    'male': '👨‍💼',
    'female': '👩‍💼',
    'kid': '🧒'
}

const navItems = [
    { title: 'Dashboard', icon: LayoutDashboard, to: '/' },
    { title: 'Transactions', icon: Wallet, to: '/transactions' },
    { title: 'Budgets', icon: PieChart, to: '/budgets' },
    { title: 'Categories', icon: Tags, to: '/categories' },
    { title: 'Insights', icon: Sparkles, to: '/insights' },
    { title: 'Mutual Funds', icon: Coins, to: '/mutual-funds' },
    { title: 'Financial Goals', icon: Target, to: '/investment-goals' },
    { title: 'Expense Groups', icon: Layers, to: '/expense-groups' },
    { title: 'Loans', icon: Landmark, to: '/loans' },
    { title: 'Vault', icon: ShieldCheck, to: '/vault' },
    { title: 'Settings', icon: Settings, to: '/settings' },
]

function logout() {
    auth.logout()
    router.push('/login')
}



const mfStore = useMutualFundStore()
const isSyncing = computed(() => mfStore.isSyncing)
const syncStatus = computed(() => mfStore.syncStatus)

let syncInterval: any = null

const syncStatusText = computed(() => {
    if (isSyncing.value || syncStatus.value?.status === 'running') return 'Syncing Mutual Fund NAVs...'
    if (syncStatus.value?.status === 'error') return `Last sync failed: ${syncStatus.value.error || syncStatus.value.error_message}`
    return 'Refresh Mutual Fund NAVs'
})


function startPolling() {
    if (syncInterval) return
    mfStore.fetchSyncStatus()
    syncInterval = setInterval(() => mfStore.fetchSyncStatus(), 15000)
}

function stopPolling() {
    if (syncInterval) {
        clearInterval(syncInterval)
        syncInterval = null
    }
}

watch(() => auth.user, (val) => {
    if (val) startPolling()
    else stopPolling()
}, { immediate: true })

onUnmounted(() => {
    stopPolling()
})

// Hyper-Premium Sidebar Interactions
const mouseX = ref(0)
const mouseY = ref(0)
function handleMouseMove(e: MouseEvent) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
    mouseX.value = e.clientX - rect.left
    mouseY.value = e.clientY - rect.top
}
</script>

<template>
    <v-app>
        <!-- Background Animated Blobs -->
        <div class="layout-blobs">
            <div class="blob b1"></div>
            <div class="blob b2"></div>
            <div class="blob b3"></div>
        </div>

        <!-- Header / App Bar -->
        <v-app-bar flat height="72" class="premium-header" border="b">
            <template v-slot:prepend>
                <v-btn icon variant="text" color="slate-600" @click.stop="rail = !rail" class="d-none d-lg-flex">
                    <Menu :size="20" />
                </v-btn>
                <v-app-bar-nav-icon class="d-lg-none" @click.stop="drawer = !drawer"></v-app-bar-nav-icon>
            </template>

            <router-link to="/" class="brand-link">
                <v-img src="/logo.png" width="36" height="36" class="mr-3 logo-theme-aware" />
                <div class="brand-details d-none d-sm-block">
                    <span class="brand-name">WealthFam</span>
                    <span class="brand-tag">Premium Finance</span>
                </div>
            </router-link>

            <v-spacer></v-spacer>

            <!-- Centered Header Search Trigger -->
            <div class="header-search-container d-none d-md-flex align-center justify-center">
                <v-text-field readonly flat hide-details density="compact" variant="solo-filled" rounded="pill"
                    placeholder="Search for anything..." class="centered-search-field" @click="showSearch = true">
                    <template v-slot:prepend-inner>
                        <Search :size="18" class="text-medium-emphasis mr-1" />
                    </template>
                    <template v-slot:append-inner>
                        <div class="cmd-k-hint-v2">⌘K</div>
                    </template>
                </v-text-field>
            </div>

            <v-spacer></v-spacer>

            <div class="d-flex align-center pr-2">
                <!-- Mobile Search Icon -->
                <v-btn icon color="slate-600" class="d-md-none mr-2" @click="showSearch = true">
                    <Search :size="20" />
                </v-btn>

                <!-- Date Chip (Desktop) -->
                <div class="date-chip-v2 d-none d-md-flex mr-4">
                    <div class="pulse-dot"></div>
                    {{ new Date().toLocaleDateString(undefined, {
                        weekday: 'short', day: 'numeric', month: 'short'
                    }) }}
                </div>

                <!-- Global Member Selection -->
                <v-menu offset="12" transition="scale-transition" v-if="auth.user && auth.user.role !== 'CHILD'">
                    <template v-slot:activator="{ props }">
                        <v-btn v-bind="props" variant="tonal" color="primary" class="text-none font-weight-bold mr-4"
                            height="40" rounded="pill" elevation="0">
                            <template v-slot:prepend>
                                <v-avatar v-if="auth.selectedMemberId" size="24" color="primary-lighten-5" class="mr-1">
                                    <span class="text-caption font-weight-black text-primary"
                                        style="font-size: 0.6rem !important;">{{
                                            auth.selectedMemberName.charAt(0).toUpperCase() }}</span>
                                </v-avatar>
                                <Users v-else :size="16" class="text-primary mr-2" />
                            </template>
                            {{ auth.selectedMemberName }}
                            <ChevronDown :size="14" class="ml-2 opacity-50" />
                        </v-btn>
                    </template>
                    <v-card width="260" rounded="xl" elevation="10" border>
                        <v-list density="compact" nav>
                            <v-list-item @click="auth.selectMember(null)" :active="auth.selectedMemberId === null"
                                color="primary">
                                <template v-slot:prepend>
                                    <Users :size="18" class="mr-3" />
                                </template>
                                <v-list-item-title class="font-weight-bold">All Members</v-list-item-title>
                            </v-list-item>
                            <v-divider class="my-2"></v-divider>
                            <v-list-item v-for="user in auth.familyMembers" :key="user.id"
                                @click="auth.selectMember(user.id)" :active="auth.selectedMemberId === user.id"
                                color="primary">
                                <template v-slot:prepend>
                                    <v-avatar size="28" color="primary-lighten-5" class="mr-3">
                                        <span class="text-caption font-weight-black text-primary">{{ (user.full_name ||
                                            user.email).charAt(0).toUpperCase() }}</span>
                                    </v-avatar>
                                </template>
                                <v-list-item-title class="font-weight-bold">{{ user.full_name ||
                                    user.email.split('@')[0]
                                    }}</v-list-item-title>
                            </v-list-item>
                        </v-list>
                    </v-card>
                </v-menu>

                <!-- Mutual Fund Sync Status -->
                <v-tooltip location="bottom" v-if="auth.user">
                    <template v-slot:activator="{ props }">
                        <v-btn v-bind="props" icon size="40" color="slate-600" class="mr-2" @click="mfStore.triggerSync"
                            :loading="isSyncing">
                            <RefreshCw :size="20" :class="{ 'spin-sync': isSyncing }" />
                        </v-btn>
                    </template>
                    <span>{{ syncStatusText }}</span>
                </v-tooltip>

                <!-- Theme Toggle -->
                <v-btn icon @click="toggleTheme" color="slate-600" class="mr-2" size="40">
                    <component :is="theme.global.current.value.dark ? Sun : Moon" :size="20" />
                </v-btn>

                <!-- Real-time Notifications Bell -->
                <v-menu offset="12" transition="scale-transition">
                    <template v-slot:activator="{ props }">
                        <v-btn v-bind="props" icon color="slate-600" class="mr-2" size="40">
                            <v-badge v-if="unreadCount > 0" :content="unreadCount" color="error" overlap
                                location="top right" offset-x="2" offset-y="2">
                                <Bell :size="20" :class="{ 'bell-ring': isBellRinging }" />
                            </v-badge>
                            <Bell v-else :size="20" :class="{ 'bell-ring': isBellRinging }" />
                        </v-btn>
                    </template>
                    <v-card width="350" rounded="xl" elevation="10" border class="premium-popup">
                        <div class="pa-4 d-flex justify-space-between align-center border-b">
                            <span class="text-subtitle-1 font-weight-black">Notifications</span>
                            <v-btn variant="text" size="x-small" color="primary" class="text-none font-weight-black"
                                @click="clearNotifications">Clear All</v-btn>
                        </div>
                        <v-list v-if="notifications.length > 0" class="pa-2 overflow-y-auto" max-height="400">
                            <v-list-item v-for="note in notifications" :key="note.id" rounded="lg" class="mb-1 pa-3">
                                <template v-slot:prepend>
                                    <v-avatar size="32" color="primary-lighten-5" class="mr-3">
                                        <Zap v-if="note.category === 'MILESTONE'" :size="16" class="text-success" />
                                        <Bell v-else :size="16" class="text-primary" />
                                    </v-avatar>
                                </template>
                                <v-list-item-title class="font-weight-black text-caption">{{ note.title
                                    }}</v-list-item-title>
                                <v-list-item-subtitle class="text-tiny line-height-1-2 opacity-60 mt-1">{{ note.body
                                    }}</v-list-item-subtitle>
                            </v-list-item>
                        </v-list>
                        <div v-else class="pa-10 text-center opacity-40">
                            <Bell :size="32" class="mb-2" />
                            <p class="text-caption font-weight-black">No new alerts</p>
                        </div>
                    </v-card>
                </v-menu>

                <!-- User Profile Menu -->
                <v-menu offset="12" transition="scale-transition" v-if="auth.user">
                    <template v-slot:activator="{ props }">
                        <v-btn v-bind="props" variant="flat" class="profile-btn" rounded="pill" height="44">
                            <v-avatar size="32" class="mr-2 avatar-glow">
                                <span class="avatar-emoji">{{ AVATARS[selectedAvatar] }}</span>
                            </v-avatar>
                            <span class="user-display-name d-none d-sm-inline">{{ auth.user.email.split('@')[0]
                            }}</span>
                        </v-btn>
                    </template>

                    <v-card width="280" class="premium-popup">
                        <v-list class="pa-4">
                            <v-list-item class="mb-4 pa-0">
                                <template v-slot:prepend>
                                    <v-avatar size="56" class="mr-4 avatar-glow">
                                        <span class="text-h5">{{ AVATARS[selectedAvatar] }}</span>
                                    </v-avatar>
                                </template>
                                <v-list-item-title class="text-h6 font-weight-bold">{{ auth.user.email.split('@')[0]
                                    }}</v-list-item-title>
                                <v-list-item-subtitle class="text-primary font-weight-medium">Family
                                    Admin</v-list-item-subtitle>
                            </v-list-item>

                            <v-divider class="mb-4"></v-divider>

                            <v-list-item link to="/settings" rounded="lg" class="mb-1">
                                <template v-slot:prepend>
                                    <UserIcon :size="18" class="mr-4 text-slate-500" />
                                </template>
                                <v-list-item-title>Profile Settings</v-list-item-title>
                            </v-list-item>

                            <v-list-item link @click="logout" rounded="lg" class="text-red-500">
                                <template v-slot:prepend>
                                    <LogOut :size="18" class="mr-4 text-red-500" />
                                </template>
                                <v-list-item-title class="font-weight-bold">Sign Out</v-list-item-title>
                            </v-list-item>
                        </v-list>
                    </v-card>
                </v-menu>
            </div>
        </v-app-bar>

        <!-- Side Navigation -->
        <v-navigation-drawer v-model="drawer" :rail="rail" permanent floating class="aether-drawer" width="280"
            :rail-width="rail ? 88 : 280" @mousemove="handleMouseMove"
            :style="{ '--mouse-x': mouseX + 'px', '--mouse-y': mouseY + 'px' }">
            <v-list nav class="px-0 py-4">
                <template v-for="(item, index) in navItems" :key="item.title">
                    <v-tooltip :text="item.title" location="right" v-if="rail" offset="12">
                        <template v-slot:activator="{ props }">
                            <v-list-item v-bind="props" :to="item.to" :active="route.path === item.to"
                                class="nav-item-aether rail-mode-item mb-1" link
                                :style="{ transitionDelay: `${index * 40}ms` }">
                                <div class="rail-item-content">
                                    <component :is="item.icon" :size="20" class="nav-icon" />
                                    <span class="rail-label-tiny">{{ item.title }}</span>
                                </div>
                            </v-list-item>
                        </template>
                    </v-tooltip>

                    <v-list-item v-else :to="item.to" :active="route.path === item.to" class="nav-item-aether mb-1" link
                        :style="{ transitionDelay: `${index * 40}ms` }">
                        <div class="nav-item-content-horizontal">
                            <component :is="item.icon" :size="20" class="nav-icon mr-4" />
                            <v-list-item-title class="nav-title">{{ item.title }}</v-list-item-title>
                        </div>
                    </v-list-item>
                </template>
            </v-list>

            <template v-slot:append>
                <div class="sidebar-footer border-t pa-6">
                    <div v-if="!rail" class="footer-content">
                        <span class="os-label">WealthFam Core OS</span>
                        <div class="build-info">v{{ appVersion }}-{{ appBuild }}</div>
                    </div>
                    <div v-else class="text-center">
                        <span class="text-primary font-weight-bold">v{{ appVersion.split('.')[0] }}</span>
                    </div>
                </div>
            </template>
        </v-navigation-drawer>

        <!-- Content -->
        <v-main class="layout-main">
            <div class="page-shell">
                <slot></slot>
            </div>
        </v-main>

        <ToastContainer />
        <GlobalSearch v-model="showSearch" />
    </v-app>
</template>

<style scoped>
.layout-blobs {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 0;
    background: rgb(var(--v-theme-background));
    pointer-events: none;
    overflow: hidden;
}

.blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(100px);
    opacity: 0.12;
}

.b1 {
    width: 800px;
    height: 800px;
    background: rgb(var(--v-theme-primary));
    top: -200px;
    left: -100px;
    animation: orbit 30s infinite linear;
}

.b2 {
    width: 700px;
    height: 700px;
    background: rgb(var(--v-theme-secondary));
    bottom: -200px;
    right: 0;
    animation: orbit 25s infinite linear reverse;
}

.b3 {
    width: 500px;
    height: 500px;
    background: rgb(var(--v-theme-accent));
    top: 30%;
    right: 20%;
    animation: orbit 20s infinite linear;
}

@keyframes orbit {
    from {
        transform: rotate(0deg) translateX(100px) rotate(0deg);
    }

    to {
        transform: rotate(360deg) translateX(100px) rotate(-360deg);
    }
}

.premium-header {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
    z-index: 1000 !important;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.08) !important;
    box-shadow: 0 4px 30px rgba(0, 0, 0, 0.03);
}

.brand-link {
    display: flex;
    align-items: center;
    text-decoration: none;
    color: inherit;
    margin-left: 1rem;
    transition: transform 0.3s ease;
}

.brand-link:hover {
    transform: scale(1.02);
}

.logo-theme-aware {
    filter: drop-shadow(0 0 2px rgba(var(--v-theme-primary), 0.1));
    mix-blend-mode: multiply;
    /* Removes white background in Light Mode */
}

:where(.v-theme--dark, .v-theme--wealthFamDark) .logo-theme-aware {
    filter: invert(1) brightness(1.2) saturate(1.2);
    mix-blend-mode: screen;
    /* Removes black space (inverted white) in Dark Mode */
}

.brand-name {
    display: block;
    font-size: 1.5rem;
    font-weight: 950;
    color: rgb(var(--v-theme-on-surface));
    letter-spacing: -0.05em;
    line-height: 1;
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, #6366f1 100%);
    background-clip: text;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.brand-tag {
    display: block;
    font-size: 0.6rem;
    font-weight: 800;
    color: rgb(var(--v-theme-on-surface), 0.4);
    text-transform: uppercase;
    letter-spacing: 0.2em;
    margin-top: 1px;
}


.profile-btn {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s;
}

.profile-btn:hover {
    background: #f8fafc !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}

.avatar-glow {
    background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.1) 0%, rgba(var(--v-theme-secondary), 0.1) 100%);
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
    box-shadow: 0 0 15px rgba(var(--v-theme-primary), 0.1);
}

.avatar-emoji {
    font-size: 1.2rem;
}

.user-display-name {
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface));
    /* text-slate-800 */
    font-size: 0.875rem;
}

.premium-popup {
    border-radius: 1.25rem !important;
    border: 1px solid rgba(var(--v-border-color), 0.2) !important;
    background: rgba(var(--v-theme-surface), 0.9) !important;
    backdrop-filter: blur(10px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1) !important;
}

.layout-main {
    transition: padding-left 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Aether V3 Architecture (Vuetify-Native, Minimal CSS) */
.aether-drawer {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(28px) saturate(190%) !important;
    border-right: 1px solid rgba(var(--v-theme-on-surface), 0.1) !important;
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    position: relative;
    overflow: visible !important;
}

/* Cursor-Reactive Light Sweep Overlay */
.aether-drawer::after {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: radial-gradient(600px circle at var(--mouse-x) var(--mouse-y),
            rgba(var(--v-theme-primary), 0.08),
            transparent 40%);
    z-index: 10;
    opacity: 0;
    transition: opacity 0.5s ease;
}

.aether-drawer:hover::after {
    opacity: 1;
}

.aether-drawer :deep(.v-navigation-drawer__content) {
    scrollbar-width: none;
    -ms-overflow-style: none;
    z-index: 1;
}

.aether-drawer :deep(.v-navigation-drawer__content)::-webkit-scrollbar {
    display: none;
}



.rail-item-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    width: 100%;
}

.rail-label-tiny {
    font-size: 0.45rem;
    font-weight: 950;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    margin-top: 2px;
    opacity: 0.6;
    transition: all 0.3s ease;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-align: center;
}

.nav-title {
    font-size: 0.7rem;
    font-weight: 900;
    text-align: left;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    opacity: 0.8;
}

.nav-item-content-horizontal {
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: flex-start;
    width: 100%;
}

.nav-item-aether {
    transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative;
    border-radius: 0 !important;
    min-height: 52px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    padding: 0 24px !important;
}

/* Ensure rail mode stays centered */
.rail-mode-item {
    padding: 0 !important;
    min-height: 64px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

.nav-item-aether.v-list-item--active .nav-title {
    opacity: 1;
    color: rgb(var(--v-theme-primary));
}

/* Hover State */
.nav-item-aether:not(.v-list-item--active):hover {
    background: rgba(var(--v-theme-primary), 0.1) !important;
    transform: translateX(4px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.nav-item-aether:hover :deep(.nav-icon) {
    color: rgb(var(--v-theme-primary)) !important;
    transform: scale(1.1);
}

/* Infinite Edge Selection (Active State) */
.nav-item-aether.v-list-item--active {
    background: transparent !important;
}

.nav-item-aether.v-list-item--active::before {
    content: '';
    position: absolute;
    inset: 0;
    /* Flush with edges */
    background: linear-gradient(90deg,
            rgba(var(--v-theme-primary), 0.3) 0%,
            rgba(var(--v-theme-primary), 0.1) 100%);
    border-left: 4px solid rgb(var(--v-theme-primary));
    /* Bold accent bar */
    box-shadow: inset 20px 0 30px -15px rgba(var(--v-theme-primary), 0.15);
    z-index: 0;
    animation: aetherPulse 4s infinite alternate cubic-bezier(0.45, 0.05, 0.55, 0.95);
}

@keyframes aetherPulse {
    0% {
        opacity: 0.8;
        filter: brightness(1);
    }

    100% {
        opacity: 1;
        filter: brightness(1.25);
    }
}

/* Reset rail active inset for Infinite Edge */
.rail-mode-item.v-list-item--active::before {
    inset: 0;
}

.nav-item-aether.v-list-item--active :deep(.nav-icon) {
    color: rgb(var(--v-theme-primary)) !important;
    filter: drop-shadow(0 0 5px rgba(var(--v-theme-primary), 0.4));
}

.nav-item-aether.v-list-item--active :deep(.nav-title) {
    color: rgb(var(--v-theme-primary)) !important;
    font-weight: 800 !important;
}

.nav-icon {
    color: rgb(var(--v-theme-on-surface), 0.6);
    transition: all 0.3s ease;
}

.nav-title {
    font-size: 0.875rem;
    font-weight: 600;
}

.sidebar-footer {
    border-top: 1px solid rgba(var(--v-theme-on-surface), 0.05) !important;
    opacity: 0.5;
}

/* Main Layout Overrides */
.layout-main {
    z-index: 1;
    background: transparent !important;
}

.page-shell {
    padding: 2rem;
    max-width: 1600px;
    margin: 0 auto;
}

@media (max-width: 600px) {
    .page-shell {
        padding: 1rem;
    }
}


.os-label {
    font-size: 0.65rem;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: rgb(var(--v-theme-on-surface), 0.3);
}

.build-info {
    font-size: 0.6rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface), 0.2);
    letter-spacing: 0.05em;
}

.date-chip-v2 {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 14px;
    background: rgba(var(--v-theme-primary), 0.05);
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 800;
    color: rgb(var(--v-theme-primary));
    border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.pulse-dot {
    width: 6px;
    height: 6px;
    background: #22c55e;
    border-radius: 50%;
    box-shadow: 0 0 0 rgba(34, 197, 94, 0.4);
    animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
    0% {
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
    }

    70% {
        box-shadow: 0 0 0 6px rgba(34, 197, 94, 0);
    }

    100% {
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0);
    }
}

.header-search-container {
    flex: 1;
    max-width: 480px;
    margin: 0 24px;
}

.centered-search-field :deep(.v-field) {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    cursor: pointer !important;
    font-weight: 600;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.centered-search-field :deep(.v-field):hover {
    background: rgba(var(--v-theme-on-surface), 0.08) !important;
    border-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.centered-search-field :deep(input) {
    cursor: pointer !important;
}

.cmd-k-hint-v2 {
    font-size: 0.75rem;
    font-weight: 800;
    padding: 2px 8px;
    background: rgba(var(--v-theme-on-surface), 0.1);
    color: rgb(var(--v-theme-on-surface), 0.6);
    border-radius: 6px;
    letter-spacing: 0.05em;
}

.last-sync-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: rgb(var(--v-theme-on-surface), 0.6);
    white-space: nowrap;
}

.spin-sync {
    animation: fa-spin 2s infinite linear;
}

@keyframes fa-spin {
    0% {
        transform: rotate(0deg);
    }

    100% {
        transform: rotate(360deg);
    }
}

.sync-btn {
    transition: transform 0.2s;
}

.sync-btn:active {
    transform: scale(0.9);
}

@keyframes bell-ring {

    0%,
    100% {
        transform: rotate(0deg);
    }

    10%,
    30%,
    50%,
    70%,
    90% {
        transform: rotate(15deg);
    }

    20%,
    40%,
    60%,
    80% {
        transform: rotate(-15deg);
    }
}

.bell-ring {
    animation: bell-ring 0.6s ease-in-out;
    transform-origin: top center;
    color: var(--v-theme-error) !important;
}
</style>
