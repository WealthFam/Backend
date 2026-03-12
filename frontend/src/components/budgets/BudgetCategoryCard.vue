<script setup lang="ts">
import { computed } from 'vue'
import { Pencil, Flame, PieChart } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
  group: any
  activeTab: 'expense' | 'income'
  isInactive?: boolean
}>()

const emit = defineEmits<{
  (e: 'edit', budget: any): void
  (e: 'open-details', category: string, budget: any): void
}>()

const { formatAmount } = useCurrency()

function getBudgetHealthClass(percentage: number) {
  if (percentage > 90) return 'health-danger'
  if (percentage > 70) return 'health-warning'
  return 'health-success'
}

const iconColor = computed(() => {
  // Simple heuristic for icon colors if not provided
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']
  const hash = props.group.parent.category.split('').reduce((acc: number, char: string) => acc + char.charCodeAt(0), 0)
  return colors[hash % colors.length]
})
</script>

<template>
  <v-card 
    :class="['premium-glass-card h-100 d-flex flex-column', { 'opacity-70': isInactive }]" 
    rounded="xl"
    :style="isInactive ? 'background: rgba(var(--v-theme-surface), 0.3) !important' : ''"
  >
    <div class="pa-6 flex-grow-1 relative-pos overflow-hidden">
      <!-- Header Info -->
      <div class="d-flex justify-space-between align-start mb-6 relative-pos z-2">
        <div class="d-flex align-center ga-3">
          <div class="category-icon-container" :style="{ '--icon-color': iconColor }">
            <div class="icon-gradient-bg"></div>
            <span class="text-h5 relative-pos z-2">{{ group.parent.icon || '🏷️' }}</span>
          </div>
          <div>
            <span class="text-subtitle-1 font-weight-black line-height-1 mb-1 d-block">{{ group.parent.category }}</span>
            <v-chip v-if="isInactive" size="x-small" variant="tonal" class="font-weight-bold">No Activity</v-chip>
            <v-chip v-else size="x-small" variant="tonal" color="primary" class="font-weight-bold">
              {{ group.children.length }} Categories
            </v-chip>
          </div>
        </div>
        <div class="d-flex ga-1">
          <v-btn icon variant="text" size="small" @click="emit('open-details', group.parent.category, group.parent)" color="primary" class="hover-glow">
            <PieChart :size="18" />
            <v-tooltip activator="parent" location="top">View Analytics</v-tooltip>
          </v-btn>
          <v-btn icon variant="text" size="small" @click="emit('edit', group.parent)" color="slate-400">
            <Pencil :size="16" />
            <v-tooltip activator="parent" location="top">Edit Budget</v-tooltip>
          </v-btn>
        </div>

      </div>

      <!-- Metrics for Active Groups -->
      <template v-if="!isInactive">
        <div class="metrics-grid pa-4 rounded-xl border mb-6 relative-pos overflow-hidden cursor-pointer hover-brighten" @click="emit('open-details', group.parent.category, group.parent)">

          <v-row no-gutters>
            <v-col cols="6" class="metric-col">
              <div class="text-overline font-weight-black opacity-50 line-height-1 mb-1">SPENT</div>
              <div class="text-h6 font-weight-black">{{ formatAmount(activeTab === 'expense' ? group.parent.spent : group.parent.income) }}</div>
            </v-col>
            <v-col cols="6" class="text-right metric-col">
              <div class="text-overline font-weight-black opacity-50 line-height-1 mb-1">
                {{ group.parent.remaining < 0 ? 'OVERSPENT' : 'REMAINING' }}
              </div>
              <div :class="['text-h6 font-weight-black', group.parent.remaining < 0 ? 'text-error' : 'text-success']">
                 {{ group.parent.remaining < 0 ? '-' : '' }}{{ formatAmount(Math.abs(group.parent.remaining)) }}
              </div>
            </v-col>
          </v-row>
          <div :class="['health-glow', { 'is-overspent': group.parent.percentage > 100, 'is-warning': group.parent.percentage > 70 }]"></div>
        </div>

        <!-- Progress for Active Groups -->
        <div v-if="group.parent.amount_limit" class="mb-6 relative-pos">
          <v-progress-linear 
            :model-value="Math.min(group.parent.percentage, 100)" 
            height="10" 
            rounded="pill"
            :class="['mb-3 elevation-1', getBudgetHealthClass(group.parent.percentage)]"
          />
          <!-- Overspent Marker -->
          <div v-if="group.parent.percentage > 100" class="overspent-indicator mini" :style="{ left: '100%' }">
            <Flame :size="10" class="text-white" />
          </div>
          <div class="d-flex justify-space-between text-caption font-weight-black opacity-50" :class="{ 'text-error opacity-100': group.parent.percentage > 100 }">
            <span>{{ group.parent.percentage.toFixed(0) }}% OF LIMIT</span>
            <span>{{ formatAmount(group.parent.amount_limit) }}</span>
          </div>
        </div>

        <!-- Sub-categories List (Always Visible) -->
        <div v-if="group.children.length > 0" class="mt-4">
          <div class="d-flex align-center justify-space-between mb-3 px-1">
            <span class="text-caption font-weight-black opacity-60 letter-spacing-1">
              BREAKDOWN
            </span>
            <v-chip size="x-small" variant="tonal" color="primary" class="font-weight-bold">
              {{ group.children.length }} Categories
            </v-chip>
          </div>
          
          <div class="d-flex flex-column ga-0">
            <div v-for="child in group.children" :key="child.category"
              class="subcategory-row py-1 px-3 group/sub cursor-pointer rounded-lg relative-pos overflow-hidden transition-all d-flex align-center ga-3 mb-1"
              @click.stop="emit('open-details', child.category, child)">
              
              <!-- Left: Icon & Category Name -->
              <div class="d-flex align-center ga-2 flex-grow-1" style="min-width: 0;">
                <span class="text-caption" style="font-size: 0.75rem;">{{ child.icon }}</span>
                <span class="text-caption font-weight-black truncate" style="max-width: 120px; font-size: 0.75rem;">
                  {{ child.category }}
                </span>
              </div>

              <!-- Center: Mini Progress Bar (if limit exists) -->
              <div v-if="child.amount_limit" class="flex-grow-1 d-none d-sm-block px-1" style="min-width: 30px; max-width: 60px;">
                <v-progress-linear 
                  :model-value="Math.min(child.percentage, 100)" 
                  height="2" 
                  rounded="pill"
                  :class="getBudgetHealthClass(child.percentage)"
                />
              </div>

              <!-- Right: Spent / Limit -->
              <div class="d-flex align-center ga-1 justify-end text-right" style="min-width: 80px;">
                <span class="text-caption font-weight-black" :class="[{ 'text-error': child.percentage > 100 }]" style="font-size: 0.75rem;">
                  {{ formatAmount(activeTab === 'expense' ? child.spent : child.income) }}
                </span>
                
                <template v-if="child.amount_limit">
                  <span class="text-tiny opacity-30">/</span>
                  <span class="text-tiny opacity-60 font-weight-bold">{{ formatAmount(child.amount_limit) }}</span>
                </template>
                <v-btn v-else size="x-small" variant="text" color="primary" @click.stop="emit('edit', child)" class="pa-0 text-none font-weight-black" style="height: 16px; font-size: 9px; min-width: auto;">
                  Set
                </v-btn>
              </div>

              <div class="subcategory-hover-bg"></div>
            </div>
          </div>
        </div>
      </template>

      <!-- Placeholder for Inactive Groups -->
      <template v-else>
        <div class="text-center pa-2">
          <v-btn variant="tonal" size="small" color="primary" rounded="pill" @click="emit('edit', group.parent)" class="text-none font-weight-black px-6">
            Set Limit
          </v-btn>
        </div>
      </template>

      <!-- Background decorative icon -->
      <PieChart class="card-bg-icon-standard" />
    </div>
  </v-card>
</template>

<style scoped>
.relative-pos { position: relative; }
.z-2 { z-index: 2; }

.premium-glass-card {
  background: rgba(var(--v-theme-surface), 0.6) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--v-border-color), 0.1);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.premium-glass-card:hover {
  transform: translateY(-8px);
  background: rgba(var(--v-theme-surface), 0.8) !important;
  box-shadow: 0 20px 40px -15px rgba(0, 0, 0, 0.2) !important;
}

.category-icon-container {
  position: relative;
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  border: 1px solid rgba(var(--v-border-color), 0.1);
  background: rgba(var(--v-theme-on-surface), 0.05);
  overflow: hidden;
  transition: all 0.3s ease;
}

.icon-gradient-bg {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 140%;
  height: 140%;
  transform: translate(-50%, -50%);
  background: radial-gradient(circle, var(--icon-color) 0%, transparent 70%);
  opacity: 0.15;
  z-index: 1;
  transition: all 0.3s ease;
}

.premium-glass-card:hover .category-icon-container {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.1);
  border-color: var(--icon-color);
}

.metrics-grid {
  background: rgba(var(--v-theme-surface), 0.5);
  transition: all 0.3s ease;
}

.metric-col {
  position: relative;
  z-index: 2;
}

.health-glow {
  position: absolute;
  top: -50%;
  right: -20%;
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(var(--v-theme-primary), 0.05) 0%, transparent 70%);
  pointer-events: none;
  z-index: 1;
  transition: background 0.5s ease;
}

.health-glow.is-overspent {
  background: radial-gradient(circle, rgba(var(--v-theme-error), 0.1) 0%, transparent 70%);
}

.health-glow.is-warning {
  background: radial-gradient(circle, rgba(var(--v-theme-warning), 0.1) 0%, transparent 70%);
}

.overspent-indicator.mini {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 20px;
  height: 20px;
  background: #ef4444;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.4);
}

.subcategory-row {
  background: rgba(var(--v-theme-on-surface), 0.02);
  border: 1px solid rgba(var(--v-border-color), 0.05);
  transition: all 0.2s ease;
}

.subcategory-row:hover {
  background: rgba(var(--v-theme-on-surface), 0.05);
  transform: translateX(4px);
  border-color: rgba(var(--v-theme-primary), 0.2);
}

.subcategory-hover-bg {
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  background: rgb(var(--v-theme-primary));
  opacity: 0;
  transition: all 0.2s ease;
}

.subcategory-row:hover .subcategory-hover-bg {
  opacity: 1;
}

.premium-accordion :deep(.v-expansion-panel-title) {
  min-height: 48px !important;
}

.card-bg-icon-standard {
  position: absolute;
  bottom: -1.5rem;
  right: -1rem;
  font-size: 8rem;
  color: rgb(var(--v-theme-on-surface));
  opacity: 0.04;
  pointer-events: none;
  line-height: 1;
  transform: rotate(-12deg);
  transition: all 0.5s ease;
  z-index: 0;
}

.premium-glass-card:hover .card-bg-icon-standard {
  transform: rotate(0deg) scale(1.1);
  opacity: 0.05;
}

.line-height-1 { line-height: 1; }

.hover-brighten:hover {
  background: rgba(var(--v-theme-surface), 0.8) !important;
  border-color: rgba(var(--v-theme-primary), 0.3) !important;
}

.hover-glow:hover {
  background: rgba(var(--v-theme-primary), 0.1) !important;
  box-shadow: 0 0 15px rgba(var(--v-theme-primary), 0.2);
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
</style>
