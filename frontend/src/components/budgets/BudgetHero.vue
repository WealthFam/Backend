<script setup lang="ts">
import { computed } from 'vue'
import { Sparkles, Pencil, Plus, Flame } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
  overallBudget: any
}>()

const emit = defineEmits<{
  (e: 'edit', budget: any): void
  (e: 'set-limit'): void
}>()

const { formatAmount } = useCurrency()

/**
 * Spending Velocity Analysis logic encapsulated
 */
const spendingVelocity = computed(() => {
  const d = new Date()
  // This component always assumes the "current" month context for the velocity marker
  // If we wanted to supports past months, we would pass the selectedDate as a prop
  const daysInMonth = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
  const dayOfMonth = d.getDate()
  const monthProgress = (dayOfMonth / daysInMonth) * 100

  if (!props.overallBudget || !props.overallBudget.amount_limit) {
    return { status: 'stable', diff: 0, monthProgress }
  }

  const diff = props.overallBudget.percentage - monthProgress
  let status = 'stable'
  if (diff > 15) status = 'aggressive'
  else if (diff > 5) status = 'warning'

  return { status, diff, monthProgress }
})


function getBudgetHealthClass(percentage: number) {
  if (percentage > 90) return 'health-danger'
  if (percentage > 70) return 'health-warning'
  return 'health-success'
}
</script>

<template>
  <v-card v-if="overallBudget" class="midnight-premium-card overflow-hidden mb-10 no-hover" rounded="xl" elevation="12">
    <!-- Animated Mesh Background -->
    <div class="mesh-blob blob-1"></div>
    <div class="mesh-blob blob-2"></div>

    <div class="pa-8 pa-md-12 relative-pos z-10">
      <v-row align="center">
        <v-col cols="12" md="8">
          <div class="d-flex align-center mb-6">
            <v-chip color="rgba(255,255,255,0.15)" size="small" variant="flat" class="font-weight-black px-4 text-white" border>
              MONTHLY TARGET
            </v-chip>
          </div>

          <div class="d-flex align-baseline ga-3 mb-8">
            <span class="text-h2 font-weight-black text-white letter-spacing-tight">
              {{ formatAmount(overallBudget.spent) }}
            </span>
            <span class="text-h4 text-white opacity-30">/</span>
            <span class="text-h4 font-weight-bold text-white opacity-60">
              {{ overallBudget.amount_limit ? formatAmount(overallBudget.amount_limit) : '∞' }}
            </span>
          </div>

          <div v-if="overallBudget.amount_limit" class="glass-card-hero pa-4 d-flex align-center ga-4 mb-8">
            <v-avatar size="44" :color="spendingVelocity.status === 'aggressive' ? 'error' : (spendingVelocity.status === 'warning' ? 'warning' : 'success')" variant="flat" class="elevation-4">
              <Sparkles :size="20" class="text-white" />
            </v-avatar>
            <div>
              <div class="text-overline font-weight-black text-white opacity-60 line-height-1 mb-1">Status Analysis</div>
              <div class="text-subtitle-1 font-weight-bold text-white">
                <template v-if="spendingVelocity.status === 'aggressive'">
                  Spending is <strong class="text-red-lighten-2">{{ spendingVelocity.diff.toFixed(0) }}% ahead</strong> of the monthly curve.
                </template>
                <template v-else-if="spendingVelocity.status === 'warning'">
                  Slightly above pace. {{ formatAmount(overallBudget.remaining) }} left.
                </template>
                <template v-else-if="spendingVelocity.status === 'stable'">
                  Under control. Spend-aligned with month progress.
                </template>
                <template v-else>
                  Monthly activity snapshot.
                </template>
              </div>
            </div>
          </div>
        </v-col>

        <v-col cols="12" md="4" class="text-md-right">
          <v-btn v-if="overallBudget.budget_id" icon variant="tonal" rounded="xl" size="large" @click="emit('edit', overallBudget)" color="white">
            <Pencil :size="24" />
          </v-btn>
          <v-btn v-else icon variant="tonal" rounded="xl" size="large" @click="emit('set-limit')" color="white">
            <Plus :size="24" />
          </v-btn>
        </v-col>
      </v-row>

      <div v-if="overallBudget.amount_limit" class="mt-8">
        <div class="relative-pos mb-4 progress-container-premium">
          <v-progress-linear 
            :model-value="Math.min(overallBudget.percentage, 100)" 
            height="16" 
            rounded="pill"
            :class="['premium-progress-lg elevation-4', getBudgetHealthClass(overallBudget.percentage)]"
          />

          <!-- 100% Goal Marker -->
          <div class="progress-goal-marker" style="left: 100%"></div>

          <!-- Overspent Overflow -->
          <div v-if="overallBudget.percentage > 100" class="overspent-indicator" style="left: 100%">
            <div class="overflow-pulse"></div>
            <Flame :size="14" class="text-white" />
          </div>
          
          <!-- Today marker -->
          <div class="month-progress-marker d-flex flex-column align-center" :style="{ left: spendingVelocity.monthProgress + '%' }">
            <div class="marker-line-white elevation-4"></div>
            <span class="text-overline font-weight-black mt-2 text-white opacity-60">Today</span>
          </div>
        </div>

        <div class="d-flex justify-space-between align-center px-2">
          <div class="text-h6 font-weight-black text-white">
            {{ overallBudget.percentage?.toFixed(1) }}% <span class="text-subtitle-2 opacity-60">Utilized</span>
          </div>
          <div class="text-h6 font-weight-black text-white">
            {{ overallBudget.remaining < 0 ? '-' : '' }}{{ formatAmount(Math.abs(overallBudget.remaining)) }}
            <span class="text-subtitle-2 opacity-60 ml-1">{{ overallBudget.remaining < 0 ? 'OVERSPENT' : 'REMAINING' }}</span>
          </div>
        </div>
      </div>
    </div>
  </v-card>
</template>

<style scoped>
.midnight-premium-card {
  background: #0f172a !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
}

.relative-pos {
  position: relative;
}

.z-10 {
  z-index: 10;
}

/* Mesh Background */
.mesh-blob {
  position: absolute;
  filter: blur(80px);
  opacity: 0.15;
  z-index: 1;
  border-radius: 50%;
  animation: blob-float 20s infinite alternate;
}

.blob-1 {
  background: rgba(59, 130, 246, 0.2);
  width: 600px;
  height: 600px;
  top: -200px;
  right: -100px;
}

.blob-2 {
  background: rgba(139, 92, 246, 0.1);
  width: 400px;
  height: 400px;
  bottom: -100px;
  left: -100px;
  animation-delay: -5s;
}

@keyframes blob-float {
  0% { transform: translate(0, 0) scale(1); }
  100% { transform: translate(20px, -20px) scale(1.1); }
}

.glass-card-hero {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
}

.progress-container-premium {
  position: relative;
}

.progress-goal-marker {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: rgba(255, 255, 255, 0.3);
  z-index: 5;
  pointer-events: none;
}

.overspent-indicator {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 28px;
  height: 28px;
  background: #ef4444;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  box-shadow: 0 0 15px rgba(239, 68, 68, 0.6);
}

.overflow-pulse {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  background: inherit;
  animation: ping 1.5s cubic-bezier(0, 0, 0.2, 1) infinite;
  opacity: 0.4;
}

@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}

.month-progress-marker {
  position: absolute;
  top: -10px;
  bottom: -20px;
  z-index: 6;
  pointer-events: none;
}

.marker-line-white {
  width: 2px;
  height: 42px;
  background: white;
  border-radius: 2px;
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
}

.premium-progress-lg :deep(.v-progress-linear__background) {
  opacity: 0.15 !important;
}

:deep(.health-success .v-progress-linear__determinate) {
  background: linear-gradient(90deg, #059669 0%, #10b981 50%, #34d399 100%) !important;
}

:deep(.health-warning .v-progress-linear__determinate) {
  background: linear-gradient(90deg, #d97706 0%, #f59e0b 50%, #fbbf24 100%) !important;
}

:deep(.health-danger .v-progress-linear__determinate) {
  background: linear-gradient(90deg, #991b1b 0%, #ef4444 50%, #f87171 100%) !important;
}

.letter-spacing-tight {
  letter-spacing: -0.05em;
}

.line-height-1 {
  line-height: 1;
}
</style>
