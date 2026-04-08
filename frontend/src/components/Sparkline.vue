<template>
  <div class="sparkline-wrapper d-flex align-end justify-end position-relative"
    :style="{ width: props.width + 'px', height: (props.height + 25) + 'px' }">
    <div class="spark-tooltip px-2 py-1 text-caption font-weight-black rounded shadow-sm text-center"
      v-if="hoveredIndex !== null" :style="{ left: tooltipX + 'px', top: '0px', color: props.color }">
      <div v-if="props.labels && props.labels[hoveredIndex]" class="text-overline opacity-70 mb-n1"
        style="font-size: 0.6rem;">{{ props.labels[hoveredIndex] }}</div>
      <div>{{ formatValue(props.data[hoveredIndex]) }}</div>
    </div>

    <svg class="sparkline-svg" :width="props.width" :height="props.height"
      :viewBox="`0 0 ${props.width} ${props.height}`" preserveAspectRatio="none" @mousemove="onMouseMove"
      @mouseleave="hoveredIndex = null" style="overflow: visible; cursor: crosshair">
      <defs>
        <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="color" stop-opacity="0.35" />
          <stop offset="100%" :stop-color="color" stop-opacity="0" />
        </linearGradient>
      </defs>

      <!-- Area Fill -->
      <path :d="areaPath" :fill="`url(#${gradientId})`" />

      <!-- Background Line -->
      <path :d="linePath" fill="none" :stroke="color" stroke-width="2.5" stroke-linecap="round"
        stroke-linejoin="round" />

      <!-- Hover Cursor Line -->
      <line v-if="hoveredIndex !== null" :x1="getPoint(hoveredIndex).x" y1="0" :x2="getPoint(hoveredIndex).x"
        :y2="height" stroke="rgba(var(--v-theme-on-surface), 0.2)" stroke-width="1.5" stroke-dasharray="4,2" />
      <!-- Hover Point Highlight -->
      <circle v-if="hoveredIndex !== null" :cx="getPoint(hoveredIndex).x" :cy="getPoint(hoveredIndex).y" r="4"
        :fill="color" stroke="rgba(var(--v-theme-surface), 1)" stroke-width="2" />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps({
  data: { type: Array as () => number[], required: true },
  labels: { type: Array as () => string[], default: () => [] },
  color: { type: String, default: '#3b82f6' },
  height: { type: Number, default: 40 },
  width: { type: Number, default: 120 }
})

const { formatAmount } = useCurrency()

const hoveredIndex = ref<number | null>(null)
const tooltipX = ref(0)
const gradientId = `sparkline-gradient-${Math.random().toString(36).substr(2, 9)}`

const min = computed(() => Math.min(...props.data))
const max = computed(() => Math.max(...props.data))

function formatValue(val: number) {
  return formatAmount(val, 'INR', true)
}

function getPoint(index: number) {
  const range = max.value - min.value
  const step = props.width / Math.max(1, props.data.length - 1)
  const x = index * step

  // If array has equal elements (flat trend) plot across the middle
  const y = range === 0 ? props.height / 2 : props.height - ((props.data[index] - min.value) / range) * props.height
  return { x, y }
}

const linePath = computed(() => {
  if (!props.data || props.data.length < 2) return ''
  return props.data.map((_, i) => {
    const p = getPoint(i)
    return (i === 0 ? 'M' : 'L') + ` ${p.x},${p.y}`
  }).join(' ')
})

const areaPath = computed(() => {
  if (!linePath.value) return ''
  return linePath.value + ` L ${props.width},${props.height} L 0,${props.height} Z`
})

function onMouseMove(e: MouseEvent) {
  const svg = e.currentTarget as SVGSVGElement
  const rect = svg.getBoundingClientRect()
  const x = e.clientX - rect.left
  const step = rect.width / Math.max(1, props.data.length - 1)

  // Snap to nearest data index strictly bounded
  const index = Math.round(x / step)
  const safeIndex = Math.max(0, Math.min(props.data.length - 1, index))
  hoveredIndex.value = safeIndex

  // Handle Tooltip Placement (bounding to edge)
  const containerRect = svg.parentElement!.getBoundingClientRect()
  const pointerXInContainer = e.clientX - containerRect.left
  tooltipX.value = Math.max(0, Math.min(props.width - 40, pointerXInContainer - 20))
}
</script>

<style scoped>
.sparkline-wrapper {
  overflow: visible;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.sparkline-svg {
  display: block;
  z-index: 1;
}

.spark-tooltip {
  position: absolute;
  background: rgba(var(--v-theme-surface), 0.95);
  border: 1px solid rgba(var(--v-border-color), 0.15);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(8px);
  z-index: 10;
  pointer-events: none;
  min-width: 40px;
  white-space: nowrap;
  animation: fade-pop 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fade-pop {
  from {
    opacity: 0;
    transform: translateY(4px) scale(0.95);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
