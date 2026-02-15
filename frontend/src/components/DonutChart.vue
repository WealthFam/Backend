<template>
    <div class="donut-chart-container" :class="`legend-${legendPosition}`">
        <svg :width="size" :height="size" viewBox="0 0 100 100">
            <!-- Background circle -->
            <circle cx="50" cy="50" :r="radius" fill="none" stroke="rgba(var(--v-border-color), 0.1)"
                :stroke-width="strokeWidth" />

            <!-- Data segments -->
            <circle v-for="(segment, index) in segments" :key="index" cx="50" cy="50" :r="radius" fill="none"
                :stroke="segment.color" :stroke-width="strokeWidth"
                :stroke-dasharray="`${segment.length} ${circumference}`" :stroke-dashoffset="segment.offset"
                transform="rotate(-90 50 50)" class="donut-segment" />

            <!-- Center text -->
            <text x="50" y="45" text-anchor="middle" class="center-value">
                {{ largestValue }}%
            </text>
            <text x="50" y="55" text-anchor="middle" class="center-label">
                {{ largestCategory }}
            </text>
        </svg>

        <!-- Legend -->
        <div class="legend">
            <div v-for="segment in segments" :key="segment.label" class="legend-item">
                <span class="legend-dot" :style="{ background: segment.color }"></span>
                <span class="legend-label">{{ formatLabel(segment.label) }}</span>
                <span class="legend-value">{{ segment.value.toFixed(1) }}%</span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
    data: Record<string, number>
    size?: number
    legendPosition?: 'bottom' | 'right'
}>(), {
    size: 160,
    legendPosition: 'bottom'
})

const size = props.size
const strokeWidth = 12
const radius = (100 - strokeWidth) / 2

const circumference = 2 * Math.PI * radius

// Generate a color based on the key name
const getColor = (key: string) => {
    const k = key.toLowerCase()

    // Explicit matches for broad asset classes (primary chart)
    const primaryColors: Record<string, string> = {
        'equity': '#3b82f6',
        'debt': '#10b981',
        'hybrid': '#8b5cf6',
        'other': '#6b7280'
    }

    // Check for exact match for main allocation chart
    if (primaryColors[k]) return primaryColors[k]

    // For specific sub-categories, strip the common prefixes to find the "real" category
    const cleanKey = k.replace(/^(equity|debt|hybrid)\s+scheme\s*-\s*/, '')

    const subCategoryColors: Record<string, string> = {
        'liquid': '#0891b2',      // Cyan
        'corporate bond': '#065f46', // Dark Green
        'elss': '#db2777',        // Pink
        'dividend yield': '#f59e0b', // Amber
        'large cap': '#1d4ed8',   // Royal Blue
        'mid cap': '#059669',     // Emerald
        'small cap': '#b91c1c',   // Red
        'flexi cap': '#7c3aed',   // Violet
        'index': '#4f46e5'        // Indigo
    }

    for (const [type, color] of Object.entries(subCategoryColors)) {
        if (cleanKey.includes(type)) return color
    }

    // Fallback: Use Golden Ratio for high-contrast HSL generation
    let hash = 0
    for (let i = 0; i < key.length; i++) {
        hash = key.charCodeAt(i) + ((hash << 5) - hash)
    }

    const goldenRatio = 0.618033988749895
    let h = (Math.abs(hash) * goldenRatio) % 1
    return `hsl(${h * 360}, 65%, 45%)`
}

const formatLabel = (key: string) => {
    if (!key) return 'N/A'
    return key.charAt(0).toUpperCase() + key.slice(1)
}

// Calculate segments
const segments = computed(() => {
    let offset = 0
    const result: any[] = []

    // Sort by value descending for better appearance
    const sortedEntries = Object.entries(props.data)
        .filter(([_, value]) => value > 0)
        .sort((a, b) => b[1] - a[1])

    const total = sortedEntries.reduce((sum, [_, value]) => sum + value, 0)

    sortedEntries.forEach(([key, value]) => {
        const percentage = (value / total) * 100
        const length = (percentage / 100) * circumference
        result.push({
            color: getColor(key),
            length,
            offset: -offset,
            value: percentage,
            label: key
        })
        offset += length
    })

    return result
})

// Find largest category for center display
const largestCategory = computed(() => {
    if (segments.value.length === 0) return 'N/A'
    const label = formatLabel(segments.value[0].label)
    // Truncate if too long
    return label.length > 12 ? label.substring(0, 10) + '...' : label
})

const largestValue = computed(() => {
    if (segments.value.length === 0) return 0
    return segments.value[0].value.toFixed(1)
})
</script>

<style scoped>
.donut-chart-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 1rem;
}

.donut-chart-container.legend-right {
    flex-direction: row;
    align-items: center;
    /* Center chart and legend vertically */
    justify-content: center;
    gap: 1.5rem;
}

.donut-segment {
    transition: opacity 0.2s;
}

.donut-segment:hover {
    opacity: 0.8;
}

.center-value {
    font-size: 14px;
    font-weight: 800;
    fill: rgb(var(--v-theme-on-surface));
}

.center-label {
    font-size: 7px;
    font-weight: 700;
    fill: rgba(var(--v-theme-on-surface), 0.6);
    text-transform: uppercase;
}

.legend {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    width: 100%;
}

.legend-right .legend {
    width: auto;
    min-width: 140px;
    /* Ensure enough space for text */
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
}

.legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
}

.legend-label {
    flex: 1;
    color: rgba(var(--v-theme-on-surface), 0.7);
    font-weight: 700;
    white-space: nowrap;
    /* Prevent wrapping in side legend */
}

.legend-value {
    color: rgb(var(--v-theme-on-surface));
    font-weight: 800;
}
</style>
