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
    ChevronDown
} from 'lucide-vue-next'
import ToastContainer from '@/components/ToastContainer.vue'

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
    { title: 'Settings', icon: Settings, to: '/settings' },
]

function logout() {
    auth.logout()
    router.push('/login')
}

// Watch for mobile screen size to handle drawer properly? 
// Vuetify handles mobile with temporary/permanent props.
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
                <v-img src="/logo.png" width="36" height="36" class="mr-3" />
                <div class="brand-details d-none d-sm-block">
                    <span class="brand-name">WealthFam</span>
                    <span class="brand-tag">Premium Finance</span>
                </div>
            </router-link>

            <v-spacer></v-spacer>

            <v-spacer></v-spacer>

            <v-spacer class="d-none d-md-flex"></v-spacer>

            <v-spacer class="d-none d-md-flex"></v-spacer>

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
                    <v-btn v-bind="props" variant="elevated" color="surface" class="text-none font-weight-bold mr-4"
                        height="40" rounded="pill" elevation="1">
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

            <!-- Theme Toggle -->
            <v-btn icon @click="toggleTheme" color="slate-600" class="mr-2">
                <component :is="theme.global.current.value.dark ? Sun : Moon" :size="20" />
            </v-btn>

            <!-- Utility Actions -->
            <v-btn icon color="slate-600" class="mr-2">
                <Bell :size="20" />
            </v-btn>

            <!-- User Profile Menu -->
            <v-menu offset="12" transition="scale-transition" v-if="auth.user">
                <template v-slot:activator="{ props }">
                    <v-btn v-bind="props" variant="flat" class="profile-btn" rounded="pill" height="44">
                        <v-avatar size="32" class="mr-2 avatar-glow">
                            <span class="avatar-emoji">{{ AVATARS[selectedAvatar] }}</span>
                        </v-avatar>
                        <span class="user-display-name d-none d-sm-inline">{{ auth.user.email.split('@')[0] }}</span>
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
        </v-app-bar>

        <!-- Side Navigation -->
        <v-navigation-drawer v-model="drawer" :rail="rail" permanent class="premium-sidebar" width="280" border="0">
            <v-list nav class="mt-4" :class="rail ? 'px-2' : 'px-4'">
                <template v-for="item in navItems" :key="item.title">
                    <v-tooltip :text="item.title" location="right" v-if="rail">
                        <template v-slot:activator="{ props }">
                            <v-list-item v-bind="props" :to="item.to" :active="route.path === item.to" rounded="xl"
                                class="nav-list-item mb-2" color="primary" link>
                                <template v-slot:prepend>
                                    <div class="nav-icon-wrapper">
                                        <component :is="item.icon" :size="22" class="nav-icon"
                                            :class="{ 'active-icon': route.path === item.to }" />
                                    </div>
                                </template>
                            </v-list-item>
                        </template>
                    </v-tooltip>

                    <v-list-item v-else :to="item.to" :active="route.path === item.to" rounded="xl"
                        class="nav-list-item mb-2" color="primary" link>
                        <template v-slot:prepend>
                            <div class="nav-icon-wrapper mr-4">
                                <component :is="item.icon" :size="22" class="nav-icon"
                                    :class="{ 'active-icon': route.path === item.to }" />
                            </div>
                        </template>
                        <v-list-item-title class="nav-title">{{ item.title }}</v-list-item-title>
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
    background: rgb(var(--v-theme-surface)) !important;
    backdrop-filter: blur(16px) saturate(180%);
    -webkit-backdrop-filter: blur(16px) saturate(180%);
    z-index: 1000 !important;
    /* Removed fixed 0.95 opacity to let theme surface shine, or adjust per theme if needed */
}

.brand-link {
    display: flex;
    align-items: center;
    text-decoration: none;
    color: inherit;
    margin-left: 1rem;
}

.brand-name {
    display: block;
    font-size: 1.25rem;
    font-weight: 900;
    color: rgb(var(--v-theme-on-surface));
    /* text-slate-900 */
    letter-spacing: -0.03em;
    line-height: 1;
}

.brand-tag {
    display: block;
    font-size: 0.65rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface), 0.6);
    /* text-slate-600 for better contrast */
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-top: 2px;
}


.profile-btn {
    background: rgb(var(--v-theme-surface)) !important;
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity)) !important;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    transition: all 0.2s;
}

.profile-btn:hover {
    background: #f8fafc !important;
    transform: translateY(-1px);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}

.avatar-glow {
    background: linear-gradient(135deg, #e0e7ff 0%, #ede9fe 100%);
    border: 1px solid white;
    box-shadow: 0 0 15px rgba(79, 70, 229, 0.1);
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
    border: 1px solid rgba(255, 255, 255, 0.5) !important;
    backdrop-filter: blur(10px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1) !important;
}

.premium-sidebar {
    background: rgb(var(--v-theme-surface)) !important;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
}

.nav-list-item {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-list-item:not(.v-list-item--active):hover {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
    transform: translateX(4px);
}

.nav-list-item.v-list-item--active {
    background: rgba(79, 70, 229, 0.12) !important;
    color: #4f46e5 !important;
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.1) !important;
}

:deep(.nav-icon-wrapper) {
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}

.nav-list-item.v-list-item--active :deep(.nav-icon) {
    color: #4f46e5 !important;
}

.nav-list-item.v-list-item--active :deep(.nav-title) {
    color: rgb(var(--v-theme-primary)) !important;
    font-weight: 700 !important;
}

.nav-icon {
    color: rgb(var(--v-theme-on-surface), 0.7);
    /* text-slate-600 */
    transition: all 0.2s;
}

.active-icon {
    color: #4f46e5;
    transform: scale(1.1);
}

.nav-title {
    font-size: 0.9375rem;
    font-weight: 600 !important;
    letter-spacing: -0.01em;
}

.sidebar-footer {
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.os-label {
    display: block;
    font-size: 0.65rem;
    font-weight: 800;
    color: rgb(var(--v-theme-on-surface), 0.5);
    /* text-slate-600 */
    text-transform: uppercase;
    letter-spacing: 0.2em;
}

.build-info {
    font-size: 0.75rem;
    color: #64748b;
    font-weight: 500;
    margin-top: 2px;
}

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


.date-chip-v2 {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: rgb(var(--v-theme-surface), 0.5);
    border-radius: 20px;
    font-size: 0.8rem;
    font-weight: 700;
    color: rgb(var(--v-theme-on-surface), 0.8);
    border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
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
</style>
