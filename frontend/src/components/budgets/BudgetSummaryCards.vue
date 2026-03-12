<script setup lang="ts">
import { TrendingUp, TrendingDown, Wallet, Ban, Flame, ArrowRight } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

defineProps<{
  totalIncome: number
  totalSpent: number
  overallBudget: any
  alertGroups: any[]
}>()

const emit = defineEmits<{
  (e: 'edit', budget: any): void
  (e: 'open-details', category: string, budget: any): void
}>()

const { formatAmount } = useCurrency()
</script>

<template>
  <div>
    <!-- Summary Grid -->
    <v-row class="mb-10">
      <v-col cols="12" sm="6" lg="3">
        <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
          <div class="d-flex justify-space-between align-center mb-6">
            <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Income In</span>
            <v-avatar color="success-lighten-5" rounded="lg" size="48">
              <TrendingUp class="text-success" :size="24" />
            </v-avatar>
          </div>
          <div class="text-h4 font-weight-black text-success">{{ formatAmount(totalIncome) }}</div>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" lg="3">
        <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
          <div class="d-flex justify-space-between align-center mb-6">
            <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Total Outflow</span>
            <v-avatar color="rose-lighten-5" rounded="lg" size="48">
              <TrendingDown class="text-error" :size="24" />
            </v-avatar>
          </div>
          <div class="text-h4 font-weight-black text-error">{{ formatAmount(totalSpent) }}</div>
        </v-card>
      </v-col>

      <v-col cols="12" sm="6" lg="3">
        <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
          <div class="d-flex justify-space-between align-center mb-6">
            <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Net Balance</span>
            <v-avatar color="indigo-lighten-5" rounded="lg" size="48">
              <Wallet class="text-indigo" :size="24" />
            </v-avatar>
          </div>
          <div class="text-h4 font-weight-black" :class="(totalIncome - totalSpent) < 0 ? 'text-error' : 'text-indigo-darken-1'">
            {{ formatAmount(totalIncome - totalSpent) }}
          </div>
        </v-card>
      </v-col>

      <v-col v-if="overallBudget?.total_excluded || overallBudget?.excluded_income" cols="12" sm="6" lg="3">
        <v-card class="premium-glass-card pa-6 h-100" rounded="xl">
          <div class="d-flex justify-space-between align-center mb-4">
            <span class="text-overline font-weight-black opacity-60 letter-spacing-1">Excluded Items</span>
            <v-avatar color="slate-lighten-5" rounded="lg" size="48">
              <Ban class="text-slate-400" :size="24" />
            </v-avatar>
          </div>
          <div class="d-flex flex-column ga-2 mt-2">
            <div v-if="overallBudget.total_excluded > 0" class="text-subtitle-2 font-weight-black opacity-60 d-flex justify-space-between align-center">
              <span>Outflow</span>
              <span class="text-subtitle-1">{{ formatAmount(overallBudget.total_excluded) }}</span>
            </div>
            <div v-if="overallBudget.excluded_income > 0" class="text-subtitle-2 font-weight-black text-success d-flex justify-space-between align-center">
              <span>Inflow</span>
              <span class="text-subtitle-1">+{{ formatAmount(overallBudget.excluded_income) }}</span>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <!-- Budget Alerts (Dynamic) -->
    <v-expand-transition>
      <div v-if="alertGroups.length > 0" class="mb-8">
        <div class="d-flex align-center ga-3 mb-4">
          <v-avatar color="warning" variant="tonal" size="40">
            <Flame class="text-warning" :size="20" />
          </v-avatar>
          <div>
            <h3 class="text-subtitle-1 font-weight-black line-height-1 mb-0">Budget Alerts</h3>
            <p class="text-caption font-weight-bold opacity-60">Attention needed</p>
          </div>
        </div>
        <v-row>
          <v-col v-for="group in alertGroups" :key="`alert-${group.parent.category}`" cols="12" sm="6" md="4" lg="3">
            <v-card :color="group.parent.percentage > 100 ? 'error' : 'warning'" variant="tonal" class="pa-3 rounded-xl border-opacity-50 h-100 cursor-pointer hover-scale" @click="emit('edit', group.parent)">
              <div class="d-flex align-center justify-space-between">
                <div class="d-flex align-center ga-3">
                  <v-avatar size="36" :color="group.parent.percentage > 100 ? 'error' : 'warning'" variant="flat" rounded="lg">
                    <span class="text-h6">{{ group.parent.icon }}</span>
                  </v-avatar>
                  <div class="overflow-hidden">
                    <div class="text-subtitle-2 font-weight-black text-truncate">{{ group.parent.category }}</div>
                    <div class="text-caption font-weight-bold" :class="group.parent.percentage > 100 ? 'text-error' : 'text-warning-darken-2'">
                      {{ group.parent.percentage > 100 ? 'Overspent' : 'Near Limit' }} ({{ group.parent.percentage.toFixed(0) }}%)
                    </div>
                  </div>
                </div>
                <div class="text-right">
                  <div class="text-subtitle-2 font-weight-black">{{ group.parent.remaining < 0 ? '-' : '' }}{{ formatAmount(Math.abs(group.parent.remaining)) }}</div>
                  <div class="font-weight-bold opacity-70" style="font-size: 10px">{{ group.parent.remaining < 0 ? 'OVERSPENT' : 'REMAINING' }}</div>
                </div>
              </div>
              <div class="mt-3 pt-3 border-t d-flex justify-center">
                <v-btn variant="text" size="x-small" color="on-surface" class="opacity-60 font-weight-bold" @click.stop="emit('open-details', group.parent.category, group.parent)">
                  View Analysis
                  <ArrowRight :size="12" class="ml-1" />
                </v-btn>
              </div>
            </v-card>
          </v-col>
        </v-row>
      </div>
    </v-expand-transition>
  </div>
</template>

<style scoped>
.premium-glass-card {
  background: rgba(var(--v-theme-surface), 0.6) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--v-border-color), 0.1);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.hover-scale {
  transition: transform 0.2s;
}

.hover-scale:hover {
  transform: translateY(-2px);
}
</style>
