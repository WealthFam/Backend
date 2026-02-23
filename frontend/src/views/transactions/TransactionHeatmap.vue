<script setup lang="ts">
import SpendingHeatmap from '@/components/SpendingHeatmap.vue'

// Props - SpendingHeatmap now self-fetches, just pass date range
defineProps<{
    startDate: string
    endDate: string
    loading?: boolean
}>()
</script>

<template>
    <div class="heatmap-view animate-in">
        <div v-if="loading" class="loading-overlay d-flex flex-column align-center justify-center">
            <v-progress-circular indeterminate color="primary" size="48" class="mb-4"></v-progress-circular>
            <p class="text-subtitle-2 font-weight-black opacity-70">Loading Map Data...</p>
        </div>
        <SpendingHeatmap :start-date="startDate" :end-date="endDate" />
        <div class="heatmap-footer mt-4">
            <p class="text-caption text-on-surface opacity-60 font-weight-bold">
                Showing spending density based on transaction geolocation. Only
                transactions with coordinates are displayed.
            </p>
        </div>
    </div>
</template>

<style scoped>
.heatmap-view {
    position: relative;
    min-height: 400px;
}

.animate-in {
    animation: fadeIn 0.3s ease-out;
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

.loading-overlay {
    position: absolute;
    inset: 0;
    background: rgba(var(--v-theme-surface), 0.8);
    backdrop-filter: blur(8px);
    z-index: 10;
}

.heatmap-footer {
    margin-top: 1rem;
}
</style>
