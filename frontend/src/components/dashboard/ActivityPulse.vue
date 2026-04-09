<template>
    <v-card class="m3-card activity-pulse pa-6 h-100" rounded="xl" elevation="1">
        <div class="d-flex justify-space-between align-center mb-6">
            <h2 class="text-h6 font-weight-black d-flex align-center">
                <Zap :size="20" class="text-primary mr-2" />
                Family Pulse
            </h2>
            <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                    <v-chip v-if="isConnected" v-bind="props" size="x-small" color="success" variant="tonal"
                        class="font-weight-black pulse-dot">
                        Real-time
                    </v-chip>
                    <v-chip v-else v-bind="props" size="x-small" color="error" variant="tonal"
                        class="font-weight-black offline-dot">
                        Offline
                    </v-chip>
                </template>
                <span>{{ isConnected ? 'Connected to live feed' : 'Live feed disconnected' }}</span>
            </v-tooltip>
        </div>

        <div v-if="displayItems.length === 0" class="text-center py-10 opacity-40">
            <div class="text-h4 mb-2">📡</div>
            <p class="text-caption font-weight-black">Waiting for milestones...</p>
        </div>

        <div v-else class="pulse-feed">
            <div v-for="item in displayItems" :key="item.id" class="pulse-item mb-4 pb-4 border-b border-dashed">
                <div class="d-flex ga-4 align-start">
                    <v-avatar :color="getCategoryColor(item.category)" variant="tonal" rounded="lg" size="40"
                        class="flex-shrink-0">
                        <span class="text-h6">{{ item.icon || getIcon(item.category) }}</span>
                    </v-avatar>
                    <div class="flex-grow-1 overflow-hidden">
                        <div class="d-flex justify-space-between align-center mb-1">
                            <span class="text-caption font-weight-black opacity-60 uppercase letter-spacing-1">
                                {{ item.category }}
                            </span>
                            <span class="text-tiny font-weight-bold opacity-40">
                                {{ formatTimeAgo(item.created_at) }}
                            </span>
                        </div>
                        <div class="text-subtitle-2 font-weight-black line-height-1-2">
                            {{ item.title }}
                        </div>
                        <div class="text-caption font-weight-medium opacity-70 mt-1 line-clamp-2">
                            {{ item.body }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Zap } from 'lucide-vue-next'
import { useWebSockets } from '@/composables/useWebSockets'
import { useTransactionHelpers } from '@/composables/useTransactionHelpers'

const { notifications, isConnected } = useWebSockets()
const { formatTimeAgo } = useTransactionHelpers({ value: [] } as any, { value: [] } as any, { value: [] } as any)

const displayItems = computed(() => {
    // Show top 5 recent notifications
    return notifications.value.slice(0, 5)
})

function getIcon(category: string) {
    switch (category) {
        case 'EXPENSE': return '💸'
        case 'MILESTONE': return '🎯'
        case 'BUDGET_ALERT': return '⚠️'
        case 'ACCOUNT': return '🏦'
        default: return '📢'
    }
}

function getCategoryColor(category: string) {
    switch (category) {
        case 'EXPENSE': return 'error'
        case 'MILESTONE': return 'success'
        case 'BUDGET_ALERT': return 'warning'
        case 'ACCOUNT': return 'primary'
        default: return 'slate'
    }
}
</script>

<style scoped>
.activity-pulse {
    min-height: 400px;
    display: flex;
    flex-direction: column;
}

.pulse-feed {
    overflow-y: auto;
    padding-right: 4px;
}

.pulse-feed::-webkit-scrollbar {
    width: 4px;
}

.pulse-feed::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 4px;
}

.pulse-item:last-child {
    border-bottom: none !important;
    margin-bottom: 0 !important;
}

.pulse-dot::before {
    content: '';
    width: 6px;
    height: 6px;
    background: currentColor;
    border-radius: 50%;
    margin-right: 6px;
    animation: pulse 2s infinite;
}

.offline-dot::before {
    content: '';
    width: 6px;
    height: 6px;
    background: currentColor;
    border-radius: 50%;
    margin-right: 6px;
    opacity: 0.8;
}

@keyframes pulse {
    0% {
        transform: scale(1);
        opacity: 1;
    }

    50% {
        transform: scale(1.5);
        opacity: 0.5;
    }

    100% {
        transform: scale(1);
        opacity: 1;
    }
}

.line-height-1-2 {
    line-height: 1.2 !important;
}

.text-tiny {
    font-size: 0.65rem;
}

.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
</style>
