<template>
  <v-card class="m3-card wealth-compass pa-6 overflow-hidden h-100 d-flex flex-column" rounded="xl" elevation="1">
    <div class="d-flex justify-space-between align-center mb-6">
      <h2 class="text-h6 font-weight-black d-flex align-center">
        <Compass :size="20" class="text-primary mr-2" />
        Wealth Compass
      </h2>
      <v-chip size="x-small" color="primary" variant="flat" class="font-weight-black">
        Live Outlook
      </v-chip>
    </div>

    <v-row class="flex-grow-1 align-center">
      <!-- Savings Rate -->
      <v-col cols="6" sm="3">
        <div class="compass-stat-item text-center">
          <v-progress-circular :model-value="savingsRate" :size="70" :width="8" color="success"
            class="mb-3 compass-progress">
            <span class="text-caption font-weight-black">{{ savingsRate }}%</span>
          </v-progress-circular>
          <div class="text-overline font-weight-black opacity-60">Savings Rate</div>
        </div>
      </v-col>

      <!-- Investment Growth -->
      <v-col cols="6" sm="3">
        <div class="compass-stat-item text-center">
          <v-progress-circular :model-value="minMax(investmentGrowth, 0, 100)" :size="70" :width="8" color="primary"
            class="mb-3 compass-progress">
            <span class="text-caption font-weight-black">{{ investmentGrowth }}%</span>
          </v-progress-circular>
          <div class="text-overline font-weight-black opacity-60">Portfolio</div>
        </div>
      </v-col>

      <!-- Debt Utility -->
      <v-col cols="6" sm="3">
        <div class="compass-stat-item text-center">
          <v-progress-circular :model-value="100 - creditUtilization" :size="70" :width="8" color="warning"
            class="mb-3 compass-progress">
            <span class="text-caption font-weight-black">{{ (100 - creditUtilization).toFixed(0) }}%</span>
          </v-progress-circular>
          <div class="text-overline font-weight-black opacity-60">Credit Health</div>
        </div>
      </v-col>

      <!-- Budget Discipline -->
      <v-col cols="6" sm="3">
        <div class="compass-stat-item text-center">
          <v-progress-circular :model-value="budgetEfficiency" :size="70" :width="8" color="info"
            class="mb-3 compass-progress">
            <span class="text-caption font-weight-black">{{ budgetEfficiency }}%</span>
          </v-progress-circular>
          <div class="text-overline font-weight-black opacity-60">Budgeting</div>
        </div>
      </v-col>
    </v-row>

    <!-- Subtle Background Elements -->
    <div class="compass-bg-icon">
      <Compass :size="180" />
    </div>
  </v-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Compass } from 'lucide-vue-next'

const props = defineProps<{
  metrics: any
  portfolio: any
}>()

const savingsRate = computed(() => {
  const spending = props.metrics?.monthly_spending || 0
  const income = props.metrics?.total_income || 0 // Assuming income is available or implied
  if (income <= 0) return 0
  const rate = ((income - spending) / income) * 100
  return Math.max(0, Math.round(rate))
})

const investmentGrowth = computed(() => {
  return Math.round(props.portfolio?.xirr || 0)
})

const creditUtilization = computed(() => {
  const limit = props.metrics?.breakdown?.total_credit_limit || 0
  const debt = props.metrics?.breakdown?.credit_debt || 0
  if (limit <= 0) return 0
  return (debt / limit) * 100
})

const budgetEfficiency = computed(() => {
  const percentage = props.metrics?.budget_health?.percentage || 0
  if (percentage === 0) return 100
  return Math.max(0, 100 - Math.round(percentage))
})

function minMax(val: number, min: number, max: number) {
  return Math.min(Math.max(val, min), max)
}
</script>

<style scoped>
.wealth-compass {
  position: relative;
  z-index: 1;
}

.compass-stat-item {
  position: relative;
  z-index: 2;
}

.compass-progress :deep(.v-progress-circular__underlay) {
  opacity: 0.1 !important;
}

.compass-bg-icon {
  position: absolute;
  top: 50%;
  right: -20px;
  transform: translateY(-50%) rotate(15deg);
  opacity: 0.03;
  color: rgb(var(--v-theme-primary));
  z-index: 0;
  pointer-events: none;
}
</style>
