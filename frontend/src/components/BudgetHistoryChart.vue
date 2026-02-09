<template>
  <div class="budget-history-render">
    <div class="chart-box-render">
      <BaseChart type="bar" :data="chartData" :options="chartOptions" :height="300" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import BaseChart from './BaseChart.vue'

const props = defineProps<{
  history: any[]
}>()

const chartData = computed(() => {
  if (!props.history || props.history.length === 0) return { labels: [], datasets: [] }

  const months = props.history.map(h => h.month)

  const limits = props.history.map(h => {
    const overall = h.data.find((d: any) => d.category === 'OVERALL')
    if (overall) return Number(overall.limit)
    return h.data.reduce((sum: number, d: any) => sum + Number(d.limit), 0)
  })

  const spent = props.history.map(h => {
    const overall = h.data.find((d: any) => d.category === 'OVERALL')
    if (overall) return Number(overall.spent)
    return h.data.reduce((sum: number, d: any) => sum + Number(d.spent), 0)
  })

  return {
    labels: months,
    datasets: [
      {
        label: 'Monthly Limit',
        data: limits,
        backgroundColor: 'rgba(100, 116, 139, 0.1)',
        borderColor: 'rgba(100, 116, 139, 0.2)',
        borderWidth: 1,
        borderRadius: 6,
        barPercentage: 0.8,
        categoryPercentage: 0.8
      },
      {
        label: 'Monthly Spending',
        data: spent,
        backgroundColor: (context: any) => {
          const index = context.dataIndex
          const isOver = spent[index] > limits[index]
          return isOver ? 'rgba(239, 68, 68, 0.7)' : 'rgba(99, 102, 241, 0.7)'
        },
        borderRadius: 6,
        barPercentage: 0.5,
        categoryPercentage: 0.8,
        // Overlay actual spending bar
        grouped: false,
      }
    ]
  }
})

const chartOptions = {
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
        callback: (value: any) => '₹' + value.toLocaleString()
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
            label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' }).format(context.parsed.y)
          }
          return label
        }
      }
    }
  }
}
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
