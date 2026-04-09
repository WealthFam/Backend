<template>
    <v-card class="premium-glass-card heatmap-card h-100 overflow-hidden">
        <div class="pa-4 d-flex align-center justify-space-between">
            <div>
                <div class="d-flex align-center gap-2 mb-1">
                    <MapPin :size="20" class="text-primary" />
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
import { MapPin } from 'lucide-vue-next'
// @ts-ignore - plugin compatibility
if (typeof window !== 'undefined') window.L = L
import 'leaflet/dist/leaflet.css'
import 'leaflet.heat'
import { useHeatmapData } from '@/composables/useHeatmapData'

const props = defineProps<{
    startDate: string
    endDate: string
}>()

const { data, fetchHeatmap } = useHeatmapData(() => props.startDate, () => props.endDate)

onMounted(() => {
    fetchHeatmap()
    // Small timeout to ensure container has dimensions
    setTimeout(initMap, 100)
})

const mapContainer = ref<HTMLElement | null>(null)
let map: L.Map | null = null
let heatLayer: any = null
let markerLayer: L.LayerGroup | null = null

const hasLocationData = computed(() => data.value && data.value.length > 0)

const initMap = () => {
    if (!mapContainer.value) return

    // Default center (can be tuned or detected from data)
    const center: L.LatLngExpression = hasLocationData.value
        ? [data.value[0].latitude, data.value[0].longitude]
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

    // Ensure layout is captured correctly - sometimes Leaflet needs a trigger
    setTimeout(() => {
        if (map) {
            map.invalidateSize()
        }
    }, 500)
}

const updateHeatmap = () => {
    if (!map) return

    if (heatLayer) {
        map.removeLayer(heatLayer)
    }

    if (!hasLocationData.value) return

    // Ensure map is correctly sized (especially after layout animations)
    map.invalidateSize()
    const size = map.getSize()

    if (size.x === 0 || size.y === 0) {
        // Retry shortly if layout hasn't settled
        setTimeout(updateHeatmap, 200)
        return
    }

    if (markerLayer) {
        map.removeLayer(markerLayer)
    }
    markerLayer = L.layerGroup().addTo(map)

    // Prepare heatmap data: [lat, lng, intensity]
    const heatPoints = data.value.map(p => {
        // Boost intensity calculation for deeper colors
        // Boost intensity calculation for deeper colors - ensure minimum visibility
        const intensity = Math.max(0.4, Math.min(Math.abs(p.amount) / 500, 1.2))

        // Add marker for each point
        if (markerLayer) {
            const marker = L.circleMarker([p.latitude, p.longitude], {
                radius: 4,
                fillColor: '#ffffff',
                color: '#3b82f6',
                weight: 1,
                opacity: 0.8,
                fillOpacity: 0.6
            })

            const tooltipContent = `
                <div class="pa-2">
                    <div class="text-caption font-weight-bold mb-1">${p.category || 'Expense'}</div>
                    <div class="text-subtitle-2 font-weight-black">₹${Math.abs(p.amount).toLocaleString()}</div>
                    <div class="text-10 opacity-70 mt-1">${p.recipient || p.description || 'Raw Transaction'}</div>
                </div>
            `
            marker.bindPopup(tooltipContent, { closeButton: false })

            // Show data on hover
            marker.on('mouseover', () => {
                marker.openPopup()
            })
            marker.on('mouseout', () => {
                marker.closePopup()
            })

            marker.addTo(markerLayer)
        }

        return [p.latitude, p.longitude, intensity]
    })

    // @ts-ignore - leaflet.heat is not in types
    heatLayer = L.heatLayer(heatPoints as any, {
        radius: 30,
        blur: 15,
        maxZoom: 17,
        minOpacity: 0.5,
        gradient: {
            0.2: '#3b82f6',
            0.4: '#10b981',
            0.6: '#f59e0b',
            0.8: '#ef4444',
            1.0: '#7f1d1d'
        }
    }).addTo(map)

    // Ensure map is visible and focused on the data
    if (data.value.length === 1) {
        map.setView([data.value[0].latitude, data.value[0].longitude], 13)
    } else if (data.value.length > 1) {
        const bounds = L.latLngBounds(data.value.map(p => [p.latitude, p.longitude] as L.LatLngTuple))
        map.fitBounds(bounds, { padding: [50, 50] })
    }
}

watch(data, (newData) => {
    if (newData && newData.length > 0) {
        if (!map) {
            initMap()
        } else {
            updateHeatmap()
        }
    }
}, { deep: true, immediate: true })

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
    background: rgba(var(--v-theme-surface), 1);
    /* Fallback for map loading */
}

.heatmap-canvas {
    height: 100%;
    width: 100%;
    min-height: 500px;
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
    background: linear-gradient(to right, #3b82f6, #10b981, #f59e0b, #ef4444, #7f1d1d);
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
    background: rgba(var(--v-theme-surface), 1) !important;
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
