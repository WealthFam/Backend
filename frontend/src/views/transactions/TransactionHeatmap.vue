<script setup lang="ts">
import SpendingHeatmap from '@/components/SpendingHeatmap.vue'

// Props
defineProps<{
    heatmapData: any[]
    loading: boolean
}>()
</script>

<template>
    <div class="heatmap-view animate-in">
        <div v-if="loading" class="loading-overlay">
            <div class="spinner"></div>
            Loading Map Data...
        </div>
        <SpendingHeatmap :data="heatmapData" />
        <div class="heatmap-footer mt-4">
            <p class="text-xs text-muted">Showing spending density based on transaction geolocation. Only
                transactions with coordinates are displayed.</p>
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
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(4px);
    z-index: 10;
    font-size: 0.875rem;
    color: #6b7280;
    font-weight: 500;
}

.spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid #e5e7eb;
    border-top-color: #4f46e5;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
}

@keyframes spin {
    to {
        transform: rotate(360deg);
    }
}

.heatmap-footer {
    margin-top: 1rem;
}

.mt-4 {
    margin-top: 1rem;
}

.text-xs {
    font-size: 0.75rem;
}

.text-muted {
    color: #6b7280;
}
</style>
