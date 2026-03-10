<template>
  <div class="chart-container" :style="{ height: height + 'px' }">
    <component :is="chartComponent" :data="chartData" :options="chartOptions" :key="settings.maskingFactor" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
import { useCurrency } from '@/composables/useCurrency'
import { useSettingsStore } from '@/stores/settings'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Filler
} from 'chart.js'
import ChartDataLabels from 'chartjs-plugin-datalabels'
import { Bar, Line, Doughnut } from 'vue-chartjs'

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Filler,
  ChartDataLabels
)

const props = defineProps<{
  type: 'bar' | 'line' | 'doughnut'
  data: any
  options?: any
  height?: number
}>()

const emit = defineEmits(['chart-click'])

const vTheme = useTheme()
const isDark = computed(() => vTheme.global.current.value.dark)
const { formatAmount } = useCurrency()
const settings = useSettingsStore()

/**
 * Custom Polyline Plugin for Doughnut Charts
 */
const polylineLabelsPlugin = {
  id: 'polylineLabels',
  afterDraw(chart: any) {
    if (chart.config.type !== 'doughnut') return
    const options = chart.options.plugins?.polylineLabels
    if (!options || options.display === false) return

    const { ctx } = chart
    ctx.save()

    chart.data.datasets.forEach((dataset: any, i: number) => {
      const meta = chart.getDatasetMeta(i)
      meta.data.forEach((element: any, index: number) => {
        const { x, y, startAngle, endAngle, outerRadius } = element
        const midAngle = startAngle + (endAngle - startAngle) / 2

        const startX = x + Math.cos(midAngle) * outerRadius
        const startY = y + Math.sin(midAngle) * outerRadius
        const elbowX = x + Math.cos(midAngle) * (outerRadius + 15)
        const elbowY = y + Math.sin(midAngle) * (outerRadius + 15)

        const isRight = Math.cos(midAngle) > 0
        const endX = elbowX + (isRight ? 20 : -20)
        const endY = elbowY

        ctx.beginPath()
        ctx.moveTo(startX, startY)
        ctx.lineTo(elbowX, elbowY)
        ctx.lineTo(endX, endY)
        ctx.strokeStyle = dataset.backgroundColor[index] || 'rgba(var(--v-border-color), 0.5)'
        ctx.lineWidth = 2
        ctx.stroke()

        const value = dataset.data[index]
        const label = chart.data.labels[index]
        const total = dataset.data.reduce((a: number, b: number) => a + b, 0)
        const percent = ((value / total) * 100).toFixed(0) + '%'

        ctx.font = 'bold 12px Inter, sans-serif'
        // Accessing isDark from the theme instance available in the closure
        ctx.fillStyle = vTheme.global.current.value.dark ? '#ffffff' : '#0f172a'
        ctx.textAlign = isRight ? 'left' : 'right'
        ctx.textBaseline = 'middle'

        const labelText = `${label}: ${percent} (${formatAmount(value)})`
        ctx.fillText(labelText, endX + (isRight ? 12 : -12), endY)
      })
    })
    ctx.restore()
  }
}

// Check if plugin is already registered to avoid duplicates
if (!ChartJS.registry.plugins.get('polylineLabels')) {
  ChartJS.register(polylineLabelsPlugin)
}

const chartComponent = computed(() => {
  if (props.type === 'bar') return Bar
  if (props.type === 'line') return Line
  if (props.type === 'doughnut') return Doughnut
  return Bar
})

const defaultOptions = computed(() => {
    // Access maskingFactor to trigger reactivity when it changes
    settings.maskingFactor;
    return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      datalabels: { display: false }, // Disable by default for all charts
      legend: {
        display: props.type === 'doughnut',
        position: 'bottom' as const,
        labels: {
          usePointStyle: true,
          padding: 20,
          color: isDark.value ? 'rgba(255, 255, 255, 0.7)' : 'rgba(15, 23, 42, 0.7)',
          font: { size: 11, weight: 'bold' }
        }
      },
      tooltip: {
        backgroundColor: isDark.value ? 'rgba(15, 23, 42, 0.95)' : 'rgba(255, 255, 255, 0.95)',
        padding: 12,
        cornerRadius: 12,
        titleFont: { size: 14, weight: 'bold' },
        bodyColor: isDark.value ? '#ffffff' : '#0f172a',
        titleColor: isDark.value ? '#ffffff' : '#0f172a',
        borderColor: 'rgba(var(--v-border-color), 0.1)',
        borderWidth: 1,
        callbacks: {
          label: (context: any) => {
            let label = context.dataset.label || ''
            if (label) label += ': '
            if (context.parsed.y !== null && context.parsed.y !== undefined) {
              label += formatAmount(context.parsed.y, 'INR', false, true)
            } else if (context.parsed !== null) {
              label += formatAmount(context.parsed, 'INR', false, true)
            }
            return label
          }
        }
      }
    },
    scales: props.type !== 'doughnut' ? {
      y: {
        beginAtZero: true,
        grid: {
          display: true,
          drawBorder: false,
          color: isDark.value ? 'rgba(254,254,254,0.05)' : 'rgba(0, 0, 0, 0.05)'
        },
        ticks: {
          color: isDark.value ? 'rgba(255, 255, 255, 0.7)' : 'rgba(15, 23, 42, 0.7)',
          font: { size: 11, weight: 'bold' },
          callback: function (this: any, value: any) {
            if (typeof value === 'number') {
              // Pass true to formatAmount for compact formatting and skipMasking=true
              return formatAmount(value, 'INR', true, true)
            }
            return value
          }
        }
      },
      x: {
        grid: {
          display: false
        },
        ticks: {
          font: { size: 11, weight: 'bold' },
          color: isDark.value ? 'rgba(255, 255, 255, 0.7)' : 'rgba(15, 23, 42, 0.7)'
        }
      }
    } : {}
  }
})

const computedChartData = computed(() => {
  if (!props.data) return props.data

  // Non-destructive deep clone to preserve functions (scriptable properties)
  const clone = (obj: any): any => {
    if (obj === null || typeof obj !== 'object') return obj
    if (typeof obj === 'function') return obj // Preserve functions
    if (Array.isArray(obj)) return obj.map(clone)

    const clonedObj: any = {}
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        clonedObj[key] = clone(obj[key])
      }
    }
    return clonedObj
  }

  const d = clone(props.data)

  if (d.datasets) {
    d.datasets.forEach((dataset: any) => {
      const color = dataset.borderColor || 'rgb(var(--v-theme-primary))'
      const resolvedColor = typeof color === 'string' ? resolveColor(color) : color

      dataset.borderColor = resolvedColor

      // Handle Gradient for Line Charts
      if (props.type === 'line' && dataset.fill) {
        // We use a scriptable background color to create the gradient
        if (typeof dataset.borderColor === 'string') {
          dataset.backgroundColor = (context: any) => {
            const chart = context.chart
            const { ctx, chartArea } = chart
            if (!chartArea) return null

            const gradient = ctx.createLinearGradient(0, chartArea.top, 0, chartArea.bottom)
            // Resolve the primary color
            let baseColor = resolveColor(dataset.borderColor)

            // Ensure we have a valid RGB string for the gradient
            if (baseColor.startsWith('#')) baseColor = hexToRgb(baseColor)
            else if (baseColor.startsWith('rgb')) {
              baseColor = baseColor.replace('rgb(', '').replace(')', '').replace('rgba(', '').split(',').slice(0, 3).join(',').trim()
            } else {
              // Fallback to primary theme color if resolution fails
              // We'll use a safe hardcoded fallback to prevent black
              baseColor = '59, 130, 246' // blue-500
            }

            gradient.addColorStop(0, `rgba(${baseColor}, 0.45)`) // Richer top opacity
            gradient.addColorStop(0.7, `rgba(${baseColor}, 0.1)`)
            gradient.addColorStop(1, `rgba(${baseColor}, 0)`)
            return gradient
          }
        }
      }
      if (typeof dataset.backgroundColor === 'function') {
        const originalBg = dataset.backgroundColor
        dataset.backgroundColor = (ctx: any) => {
          const res = originalBg(ctx)
          return typeof res === 'string' ? resolveColor(res) : res
        }
      } else if (typeof dataset.backgroundColor === 'string' && (dataset.backgroundColor.includes('var(') || dataset.backgroundColor.includes('rgb('))) {
        dataset.backgroundColor = resolveColor(dataset.backgroundColor)
      } else if (Array.isArray(dataset.backgroundColor)) {
        dataset.backgroundColor = dataset.backgroundColor.map((c: any) =>
          (typeof c === 'string' && (c.includes('var(') || c.includes('rgb('))) ? resolveColor(c) : c
        )
      }

      if (typeof dataset.pointBackgroundColor === 'function') {
        const originalPbg = dataset.pointBackgroundColor
        dataset.pointBackgroundColor = (ctx: any) => {
          const res = originalPbg(ctx)
          return typeof res === 'string' ? resolveColor(res) : res
        }
      } else if (typeof dataset.pointBackgroundColor === 'string' && (dataset.pointBackgroundColor.includes('var(') || dataset.pointBackgroundColor.includes('rgb('))) {
        dataset.pointBackgroundColor = resolveColor(dataset.pointBackgroundColor)
      }

      if (typeof dataset.borderColor === 'function') {
        const originalBc = dataset.borderColor
        dataset.borderColor = (ctx: any) => {
          const res = originalBc(ctx)
          return typeof res === 'string' ? resolveColor(res) : res
        }
      }
    })
  }
  return d
})

function resolveColor(colorStr: string): string {
  if (!colorStr.includes('var(')) return colorStr

  // Try to extract variable name for direct theme lookup first
  const match = colorStr.match(/--v-theme-([a-z0-9-]+)/)
  if (match && match[1]) {
    // Convert kebab-case to camelCase (e.g., surface-variant to surfaceVariant)
    const key = match[1].replace(/-([a-z])/g, (g) => g[1].toUpperCase())
    const themeColor = (vTheme.global.current.value.colors as any)[key]
    if (themeColor) {
      if (colorStr.includes('rgba(')) {
        const parts = colorStr.split(',')
        const alpha = parts[parts.length - 1].replace(')', '').trim() || '1'
        return `rgba(${hexToRgb(themeColor)}, ${alpha})`
      }
      return themeColor
    }
  }

  // Fallback to DOM resolution for complex strings
  try {
    const temp = document.createElement('div')
    temp.style.color = colorStr
    document.body.appendChild(temp)
    const resolved = window.getComputedStyle(temp).color
    document.body.removeChild(temp)
    return resolved || colorStr
  } catch (e) {
    return colorStr
  }
}

function hexToRgb(hex: string): string {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `${r}, ${g}, ${b}`
}

const chartData = computed(() => computedChartData.value)
const chartOptions = computed(() => {
  // Deep merge strategy for options to preserve nested plugin defaults
  const merge = (target: any, source: any): any => {
    if (source === null || typeof source !== 'object' || Array.isArray(source) || typeof source === 'function') {
      return source
    }
    const output = { ...target }
    for (const key in source) {
      if (source[key] instanceof Object && key in target && !Array.isArray(source[key]) && typeof source[key] !== 'function') {
        output[key] = merge(target[key], source[key])
      } else {
        output[key] = source[key]
      }
    }
    return output
  }

  const base = merge(defaultOptions.value, props.options || {})

  // Inject click handler if not already present
  if (!base.onClick) {
    base.onClick = (_event: any, elements: any[]) => {
      if (elements && elements.length > 0) {
        const index = elements[0].index
        const label = chartData.value.labels[index]
        const value = chartData.value.datasets[0].data[index]
        emit('chart-click', { index, label, value })
      }
    }
  }

  return base
})
const height = computed(() => props.height || 300)

</script>

<style scoped>
.chart-container {
  width: 100%;
  position: relative;
}
</style>
