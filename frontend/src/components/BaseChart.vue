<template>
  <div class="chart-container" :style="{ height: height + 'px' }">
    <component :is="chartComponent" :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTheme } from 'vuetify'
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
  Filler
)

const props = defineProps<{
  type: 'bar' | 'line' | 'doughnut'
  data: any
  options?: any
  height?: number
}>()

const vTheme = useTheme()
const isDark = computed(() => vTheme.global.current.value.dark)

const chartComponent = computed(() => {
  if (props.type === 'bar') return Bar
  if (props.type === 'line') return Line
  if (props.type === 'doughnut') return Doughnut
  return Bar
})

const defaultOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
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
      borderWidth: 1
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
        color: isDark.value ? 'rgba(255, 255, 255, 0.5)' : 'rgba(15, 23, 42, 0.5)',
        font: { size: 10, weight: 'bold' },
        callback: (value: any) => '₹' + value.toLocaleString()
      }
    },
    x: {
      grid: {
        display: false
      },
      ticks: {
        font: { size: 10, weight: 'bold' },
        color: isDark.value ? 'rgba(255, 255, 255, 0.5)' : 'rgba(15, 23, 42, 0.5)'
      }
    }
  } : {}
}))

const chartData = computed(() => props.data)
const chartOptions = computed(() => ({ ...defaultOptions.value, ...props.options }))
const height = computed(() => props.height || 300)

</script>

<style scoped>
.chart-container {
  width: 100%;
  position: relative;
}
</style>
