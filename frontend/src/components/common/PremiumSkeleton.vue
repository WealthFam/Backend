<template>
    <div class="premium-skeleton-container" :class="[type, { 'is-glass': glass }]">
        <v-skeleton-loader :type="skeletonType" :height="height" :width="width" rounded="xl" class="premium-loader">
        </v-skeleton-loader>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
    type: 'hero' | 'stat-card' | 'category-card' | 'insight-card' | 'list-item'
    height?: string | number
    width?: string | number
    glass?: boolean
}>()

const skeletonType = computed(() => {
    switch (props.type) {
        case 'hero': return 'card-avatar'
        case 'stat-card': return 'card'
        case 'category-card': return 'image, heading, subtitle'
        case 'insight-card': return 'article'
        case 'list-item': return 'list-item-avatar-two-line'
        default: return 'card'
    }
})
</script>

<style scoped>
.premium-skeleton-container {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
}

.premium-skeleton-container.is-glass {
    background: rgba(var(--v-theme-surface), 0.4);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
}

.premium-loader {
    background: transparent !important;
}

/* Custom Overrides for deep skeleton elements if needed */
:deep(.v-skeleton-loader__bone) {
    background: rgba(var(--v-theme-on-surface), 0.05) !important;
}

/* Hero Variant */
.hero {
    min-height: 300px;
}

/* Stat Card Variant */
.stat-card {
    height: 120px;
}

/* Category Card Variant */
.category-card {
    height: 240px;
}
</style>
