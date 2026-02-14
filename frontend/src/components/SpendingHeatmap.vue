<template>
    <v-card class="premium-glass-card heatmap-card h-100 overflow-hidden">
        <div class="pa-4 d-flex align-center justify-space-between">
            <div>
                <div class="d-flex align-center gap-2 mb-1">
                    <v-icon color="primary" size="20">mdi-map-marker-radius</v-icon>
                    <h3 class="text-h6 font-weight-black">Spending Heatmap</h3>
                </div>
                <p class="text-caption font-weight-bold opacity-60">Visualizing expenses by location</p>
            </div>

            <div class="intensity-legend-premium pa-2 px-4 rounded-pill d-flex align-center gap-3">
                <span class="text-10 font-weight-black text-uppercase opacity-50">Low</span>
                <div class="gradient-bar-premium"></div>
                <span class="text-10 font-weight-black text-uppercase opacity-50">High</span>
                <v-chip v-if="hasLocationData" size="x-small" color="primary" variant="tonal"
                    class="ml-2 font-weight-black">
                    {{ data.length }} Points
                </v-chip>
            </div>
        </div>

        <div class="map-wrapper border-t border-opacity-5">
            <div id="map" class="heatmap-canvas" ref="mapContainer"></div>

            <v-fade-transition>
                <div v-if="!hasLocationData" class="no-data-overlay d-flex align-center justify-center">
                    <div class="text-center">
                        <div class="text-h1 mb-4">📍</div>
                        <h3 class="text-h6 font-weight-bold mb-1">No Geolocation Data</h3>
                        <p class="text-body-2 opacity-60">Transactions with location coordinates will appear here.</p>
                    </div>
                </div>
            </v-fade-transition>
        </div>
    </v-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import 'leaflet.heat'

interface HeatmapDataPoint {
    latitude: number
    longitude: number
    amount: number
    recipient?: string
}

const props = defineProps<{
    data: HeatmapDataPoint[]
}>()

const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let heatLayer: any = null

const hasLocationData = computed(() => props.data && props.data.length > 0)

const initMap = () => {
    if (!mapContainer.value) return

    // Default center (can be tuned or detected from data)
    const center: L.LatLngExpression = hasLocationData.value
        ? [props.data[0].latitude, props.data[0].longitude]
        : [20.5937, 78.9629] // India center fallback

    map = L.map(mapContainer.value, {
        zoomControl: false,
        attributionControl: false
    }).setView(center, 13)

    // Premium Dark Mode Tiles
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
    }).addTo(map)

    // Add zoom control manually to bottom right
    L.control.zoom({
        position: 'bottomright'
    }).addTo(map)

    updateHeatmap()
}

const updateHeatmap = () => {
    if (!map) return

    if (heatLayer) {
        map.removeLayer(heatLayer)
    }

    if (!hasLocationData.value) return

    // Prepare heatmap data: [lat, lng, intensity]
    const heatPoints = props.data.map(p => {
        // Normalize intensity based on amount
        // Simple log scale or linear scale
        const intensity = Math.min(Math.abs(p.amount) / 1000, 1)
        return [p.latitude, p.longitude, intensity]
    })

    // @ts-ignore - leaflet.heat is not in types
    heatLayer = L.heatLayer(heatPoints as any, {
        radius: 25,
        blur: 15,
        maxZoom: 17,
        gradient: {
            0.4: '#3b82f6', // blue
            0.6: '#10b981', // green
            0.7: '#f59e0b', // amber
            0.8: '#ef4444'  // red
        }
    }).addTo(map)

    // Fit bounds if we have multiple points
    if (props.data.length > 1) {
        const bounds = L.latLngBounds(props.data.map(p => [p.latitude, p.longitude]))
        map.fitBounds(bounds, { padding: [50, 50] })
    }
}

watch(() => props.data, () => {
    updateHeatmap()
}, { deep: true })

onMounted(() => {
    // Small timeout to ensure container has dimensions
    setTimeout(initMap, 100)
})

onUnmounted(() => {
    if (map) {
        map.remove()
        map = null
    }
})
</script>

<style scoped>
.heatmap-card {
    min-height: 600px;
    display: flex;
    flex-direction: column;
}

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    border-radius: 20px !important;
    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.07) !important;
}

.map-wrapper {
    position: relative;
    flex: 1;
    min-height: 500px;
    background: #0f172a;
    /* Fallback for map loading */
}

.heatmap-canvas {
    height: 100%;
    width: 100%;
    z-index: 1;
}

.intensity-legend-premium {
    background: rgba(var(--v-theme-on-surface), 0.05);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.gradient-bar-premium {
    width: 100px;
    height: 6px;
    border-radius: 3px;
    background: linear-gradient(to right, #3b82f6, #10b981, #f59e0b, #ef4444);
}

.no-data-overlay {
    position: absolute;
    inset: 0;
    background: rgba(var(--v-theme-surface), 0.6);
    backdrop-filter: blur(8px);
    z-index: 10;
}

.text-10 {
    font-size: 10px;
}

.opacity-60 {
    opacity: 0.6;
}

.opacity-50 {
    opacity: 0.5;
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

/* Leaflet Overrides */
:deep(.leaflet-container) {
    background: #0f172a !important;
}

:deep(.leaflet-popup-content-wrapper) {
    background: rgba(var(--v-theme-surface), 0.9) !important;
    color: rgb(var(--v-theme-on-surface)) !important;
    backdrop-filter: blur(8px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

:deep(.leaflet-popup-tip) {
    background: rgba(var(--v-theme-surface), 0.9) !important;
}

:deep(.leaflet-control-zoom) {
    border: none !important;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
}

:deep(.leaflet-control-zoom-in),
:deep(.leaflet-control-zoom-out) {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    color: rgb(var(--v-theme-on-surface)) !important;
    border: 1px solid rgba(var(--v-border-color), 0.1) !important;
    backdrop-filter: blur(4px);
}

:deep(.leaflet-control-zoom-in:hover),
:deep(.leaflet-control-zoom-out:hover) {
    background: rgb(var(--v-theme-primary)) !important;
    color: white !important;
}
</style>
