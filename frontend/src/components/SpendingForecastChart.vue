<template>
    <div class="forecast-chart-wrapper position-relative" :style="{ height: (height + 30) + 'px' }">
        <!-- Overlay Tooltip -->
        <div v-if="hoveredBar !== null" class="chart-tooltip glass-card pa-3"
            :style="{ left: tooltipPos.x + 'px', top: '-60px' }">
            <div class="text-caption font-weight-black mb-1">{{ formatDate(hoveredBar.date) }} <span
                    v-if="hoveredBar.is_forecast" class="text-primary font-weight-bold ml-1">(Forecast)</span></div>
            <div v-for="(val, key) in hoveredBar.stacks" :key="key" class="d-flex align-center gap-2 mb-1">
                <div class="stack-indicator" :style="{ background: getStackColor(String(key)) }"></div>
                <span class="text-tiny font-weight-bold opacity-70">{{ getUserName(String(key)) }}:</span>
                <span class="text-tiny font-weight-black">₹{{ Math.round(val) }}</span>
            </div>
            <v-divider class="my-1"></v-divider>
            <div class="d-flex align-center justify-space-between gap-4">
                <span class="text-tiny font-weight-black">TOTAL</span>
                <span class="text-tiny font-weight-black">₹{{ Math.round(hoveredBar.total) }}</span>
            </div>
        </div>

        <svg :width="width" :height="height" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none"
            @mouseleave="hoveredBar = null" style="overflow: visible;">
            <!-- Grid Lines -->
            <g class="grid-lines">
                <line v-for="i in 5" :key="i" :x1="axisPadding" :y1="(height / 4) * (i - 1)" :x2="width - axisPadding"
                    :y2="(height / 4) * (i - 1)" stroke="rgba(var(--v-border-color), 0.05)" />
            </g>

            <!-- Y-Axis Labels -->
            <g class="y-axis-labels">
                <text v-for="i in 5" :key="i" :x="axisPadding - 10" :y="(height / 4) * (i - 1) + 4" text-anchor="end"
                    class="text-tiny opacity-40 font-weight-black fill-content" style="font-size: 9px;">
                    ₹{{ formatYLabel((maxVal / 4) * (4 - (i - 1))) }}
                </text>
            </g>

            <!-- Bars -->
            <g v-for="(day, idx) in trend" :key="idx" class="bar-group" @mouseenter="onHover(day, idx)">
                <template v-for="(val, key) in sortedStacks(day.stacks)" :key="key">
                    <rect :x="axisPadding + idx * (barWidth + gap)" :y="getY(day, String(key))" :width="barWidth"
                        :height="getHeight(val)" :fill="getStackColor(String(key))" :rx="2"
                        :class="{ 'forecast-bar': day.is_forecast, 'bar-rect': true, 'active-bar': hoveredBar?.date === day.date }"
                        :style="{ opacity: day.is_forecast ? 0.35 : 1 }" />
                </template>

                <!-- Hover interaction area -->
                <rect :x="axisPadding + idx * (barWidth + gap)" y="0" :width="barWidth" :height="height"
                    fill="transparent" style="cursor: pointer;" />
            </g>

            <!-- Today Marker Line -->
            <line v-if="todayIndex !== -1" :x1="axisPadding + (todayIndex + 1) * (barWidth + gap) - (gap / 2)" y1="0"
                :x2="axisPadding + (todayIndex + 1) * (barWidth + gap) - (gap / 2)" :y2="height"
                stroke="rgb(var(--v-theme-primary))" stroke-width="1" stroke-dasharray="4,2" />
        </svg>

        <!-- X-Axis Labels -->
        <div class="x-axis mt-3 opacity-50 font-weight-bold text-tiny position-relative" style="height: 20px;">
            <div v-for="day in filteredLabels" :key="day.date" class="position-absolute"
                :style="{ left: (axisPadding + getLabelX(day.date)) + 'px', transform: 'translateX(-50%)' }">
                {{ day.label }}
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface TrendItem {
    date: string
    is_forecast: boolean
    stacks: Record<string, number>
    total?: number
}

const props = defineProps({
    trend: { type: Array as () => TrendItem[], required: true },
    userNames: { type: Object as () => Record<string, string>, default: () => ({}) },
    height: { type: Number, default: 120 },
    width: { type: Number, default: 1200 }
})

const axisPadding = 60
const chartInnerWidth = computed(() => props.width - (axisPadding * 2))
const barWidth = computed(() => (chartInnerWidth.value / (props.trend.length || 1)) * 0.7)
const gap = computed(() => (chartInnerWidth.value / (props.trend.length || 1)) * 0.3)
const maxVal = computed(() => {
    const totals = (props.trend || []).map(d => Object.values(d.stacks || {}).reduce((a: number, b: unknown) => {
        const val = Number(b)
        return a + (isNaN(val) ? 0 : val)
    }, 0))
    const peak = Math.max(...totals, 100)
    return isNaN(peak) ? 100 : peak
})

const hoveredBar = ref<any>(null)
const tooltipPos = ref({ x: 0, y: 0 })

const todayIndex = computed(() => {
    const todayStr = new Date().toISOString().split('T')[0]
    return props.trend.findIndex(d => d.date === todayStr)
})

const filteredLabels = computed(() => {
    return props.trend.filter((_, i) => i % 5 === 0).map(d => ({
        date: d.date,
        label: d.date.split('-')[2]
    }))
})

function getLabelX(dateStr: string) {
    const idx = props.trend.findIndex(d => d.date === dateStr)
    if (idx === -1) return 0
    return idx * (barWidth.value + gap.value) + (barWidth.value / 2)
}

function formatYLabel(val: number) {
    if (val >= 1000) return (val / 1000).toFixed(1) + 'k'
    return Math.round(val).toString()
}

function sortedStacks(stacks: Record<string, number | string>) {
    if (!stacks) return {}
    return Object.fromEntries(Object.entries(stacks).sort())
}

function getY(day: any, key: string) {
    const stacks = sortedStacks(day.stacks)
    let offset = 0
    const keys = Object.keys(stacks)
    const targetIdx = keys.indexOf(key)

    for (let i = 0; i < targetIdx; i++) {
        const sVal = Number(stacks[keys[i]])
        offset += isNaN(sVal) ? 0 : sVal
    }

    const val = Number(stacks[key]) || 0
    const totalVal = offset + val
    const safeMax = maxVal.value || 100
    return props.height - (totalVal / safeMax) * props.height
}

function getHeight(val: number | string) {
    const v = Number(val) || 0
    const safeMax = maxVal.value || 100
    return (v / safeMax) * props.height
}

function getStackColor(key: string) {
    if (key === 'Predicted') return 'rgb(var(--v-theme-primary))'
    if (key === 'Upcoming Bills') return 'rgb(var(--v-theme-secondary))'
    if (key === 'None' || key === 'Shared/Other') return '#94a3b8'

    // Deterministic color based on user ID
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
    const hash = key.split('').reduce((a, b) => a + b.charCodeAt(0), 0)
    return colors[hash % colors.length]
}

function getUserName(key: string) {
    return props.userNames[key] || key
}

function formatDate(dateStr: string) {
    const d = new Date(dateStr)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

function onHover(day: any, idx: number) {
    const total = Object.values(day.stacks || {}).reduce((a: number, b: unknown) => {
        const val = Number(b)
        return a + (isNaN(val) ? 0 : val)
    }, 0)
    hoveredBar.value = { ...day, total }

    // Calculate tooltip X
    const x = axisPadding + idx * (barWidth.value + gap.value)
    tooltipPos.value = { x: Math.min(props.width - 150, Math.max(0, x - 75)), y: 0 }
}
</script>

<style scoped>
.forecast-chart-wrapper {
    user-select: none;
}

.bar-rect {
    transition: all 0.2s ease;
}

.active-bar {
    filter: brightness(1.2);
    stroke: rgba(var(--v-theme-on-surface), 0.2);
    stroke-width: 1;
}

.forecast-bar {
    /* Foggy effect */
    stroke-dasharray: 2, 2;
}

.chart-tooltip {
    position: absolute;
    z-index: 100;
    min-width: 180px;
    pointer-events: none;
    background: rgba(var(--v-theme-surface), 0.95);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(var(--v-border-color), 0.2);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.stack-indicator {
    width: 8px;
    height: 8px;
    border-radius: 2px;
}

.text-tiny {
    font-size: 0.65rem;
    letter-spacing: 0.02em;
}

.gap-2 {
    gap: 8px;
}

.gap-4 {
    gap: 16px;
}
</style>
