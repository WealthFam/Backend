<template>
  <div class="budget-history-render">
    <div class="chart-box-render">
      <BaseChart type="bar" :data="chartData" :options="chartOptions" :height="300" :key="settings.maskingFactor" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'
import { useCurrency } from '@/composables/useCurrency'
import { useSettingsStore } from '@/stores/settings'

const { formatAmount } = useCurrency()
const settings = useSettingsStore()

const props = defineProps<{
  history: any[]
}>()

const chartData = computed(() => {
  if (!props.history || props.history.length === 0) return { labels: [], datasets: [] }

  const months = props.history.map(h => h.month)

  const limits = props.history.map(h => {
    const overall = h.data.find((d: any) => d.category === 'OVERALL')
    let val = 0
    if (overall) val = Number(overall.limit)
    else val = h.data.reduce((sum: number, d: any) => sum + Number(d.limit), 0)
    return val / (settings.maskingFactor || 1)
  })

  const spent = props.history.map(h => {
    const overall = h.data.find((d: any) => d.category === 'OVERALL')
    let val = 0
    if (overall) val = Number(overall.spent)
    else val = h.data.reduce((sum: number, d: any) => sum + Number(d.spent), 0)
    return val / (settings.maskingFactor || 1)
  })

  return {
    labels: months,
    datasets: [
      {
        label: 'Monthly Limit',
        data: limits,
        backgroundColor: 'rgba(var(--v-theme-surface-variant), 0.3)',
        borderColor: 'rgba(var(--v-theme-surface-variant), 0.5)',
        borderWidth: 1,
        borderRadius: 8,
        barPercentage: 0.9,
        categoryPercentage: 0.8
      },
      {
        label: 'Monthly Spending',
        data: spent,
        backgroundColor: (context: any) => {
          const index = context.dataIndex
          const isOver = spent[index] > limits[index]
          return isOver ? 'rgba(var(--v-theme-error), 0.8)' : 'rgba(var(--v-theme-primary), 0.8)'
        },
        borderRadius: 8,
        barPercentage: 0.6,
        categoryPercentage: 0.8,
        grouped: false,
      }
    ]
  }
})

const chartOptions = computed(() => {
  settings.maskingFactor // Trigger reactivity
  return {
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#94a3b8', font: { size: 11 } }
      },
      y: {
        grid: { color: 'rgba(0,0,0,0.03)' },
        ticks: {
          color: '#94a3b8',
          font: { size: 11 },
          callback: (value: any) => formatAmount(value, 'INR', true, true)
        }
      }
    },
    plugins: {
      legend: { display: false },
      tooltip: {
        mode: 'index',
        intersect: false,
        callbacks: {
          label: (context: any) => {
            let label = context.dataset.label || ''
            if (label) label += ': '
            if (context.parsed.y !== null) {
              label += formatAmount(context.parsed.y, 'INR', false, true)
            }
            return label
          }
        }
      }
    }
  }
})
</script>

<style scoped>
.legend-pills-premium {
  display: flex;
  gap: 1.25rem;
}

.lp-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.7rem;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.lp-box {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

.lp-item.limit .lp-box {
  background: rgba(100, 116, 139, 0.1);
  border: 1px solid rgba(100, 116, 139, 0.3);
}

.lp-item.actual .lp-box {
  background: #6366f1;
}
</style>
