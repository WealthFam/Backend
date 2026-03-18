<script setup lang="ts">
import { Sparkles, RefreshCw } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

defineProps<{
  insights: any[]
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'analyze'): void
}>()

const router = useRouter()
</script>

<template>
  <div class="mb-10">
    <div class="d-flex align-center ga-3 mb-6">
      <v-avatar color="primary" variant="tonal" size="44">
        <Sparkles class="text-primary" :size="24" />
      </v-avatar>
      <div>
        <h2 class="text-h6 font-weight-black line-height-1 mb-1">AI Intelligence</h2>
        <p class="text-caption font-weight-bold opacity-60">Smart financial analysis & recommendations</p>
      </div>
      <v-spacer></v-spacer>
      <v-btn v-if="insights.length === 0" variant="tonal" color="primary" rounded="pill" size="small" :loading="loading" @click="emit('analyze')" class="text-none px-6 font-weight-bold">
        Analyze Now
      </v-btn>
      <v-btn v-else icon variant="text" size="small" :loading="loading" @click="emit('analyze')" color="primary">
        <RefreshCw :size="20" />
      </v-btn>
    </div>

    <div v-if="loading" class="d-flex flex-column ga-4">
      <v-skeleton-loader v-for="i in 2" :key="`insight-skel-${i}`" type="article" height="120" rounded="xl" class="premium-glass-card"></v-skeleton-loader>
    </div>

    <div v-else-if="insights.length > 0" class="d-flex flex-column ga-4">
      <v-card v-for="insight in insights" :key="insight.id" class="premium-glass-card pa-6" rounded="xl" elevation="2"
        @click="insight.action === 'settings' ? router.push('/settings') : null"
        :class="{ 'cursor-pointer hover-scale': insight.action }">
        <div class="d-flex align-start ga-4">
          <v-avatar size="48" :color="insight.type === 'danger' ? 'error' : (insight.type === 'warning' ? 'warning' : 'primary')"
            variant="tonal" rounded="lg">
            <span class="text-h5">{{ insight.icon || '✨' }}</span>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="d-flex justify-space-between align-start">
              <h4 class="text-h6 font-weight-black line-height-1 mb-2">{{ insight.title }}</h4>
              <v-chip size="small" variant="outlined" :color="insight.type === 'danger' ? 'error' : 'primary'" class="font-weight-black">
                {{ insight.action ? 'Action Required' : 'AI Insight' }}
              </v-chip>
            </div>
            <p class="text-body-1 font-weight-medium opacity-80 line-height-relaxed">{{ insight.content }}</p>
          </div>
        </div>
      </v-card>
    </div>
  </div>
</template>

<style scoped>
.premium-glass-card {
  background: rgba(var(--v-theme-surface), 0.6) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--v-border-color), 0.1);
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.line-height-1 { line-height: 1; }
.line-height-relaxed { line-height: 1.6; }

.hover-scale {
  transition: transform 0.2s;
}
.hover-scale:hover {
  transform: translateY(-2px);
}
</style>
