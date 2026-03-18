<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  modelValue: boolean
  newBudget: any
  categories: any[]
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', val: boolean): void
  (e: 'save'): void
  (e: 'close'): void
}>()

const show = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit('update:modelValue', val)
})

const categoryOptions = computed(() => {
  return props.categories.map(c => ({
    label: `${c.icon} ${c.name}`,
    value: c.name
  }))
})

function onCategoryChange(val: string) {
  const cat = props.categories.find(c => c.name === val)
  if (cat) {
    props.newBudget.icon = cat.icon
  }
}
</script>

<template>
  <v-dialog v-model="show" max-width="500">
    <v-card class="premium-glass-card no-hover" rounded="xl">
      <v-card-title class="pa-6 border-b d-flex align-center">
        <div class="d-flex align-center ga-3 flex-grow-1">
          <v-avatar color="primary" variant="tonal" rounded="lg" size="40">
            <span class="text-h6">{{ newBudget.icon || '🏷️' }}</span>
          </v-avatar>
          <div>
            <div class="text-caption font-weight-bold opacity-60 line-height-1 mb-1">SET BUDGET FOR</div>
            <div class="text-h6 font-weight-black line-height-1">
              {{ newBudget.category || 'Select Category' }}
            </div>
          </div>
        </div>
        <v-btn icon variant="text" size="small" @click="emit('close')" color="slate-400">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <v-card-text class="pa-6">
        <v-form @submit.prevent="emit('save')">
          <div v-if="!newBudget.category" class="mb-6">
            <label class="d-block text-caption font-weight-black mb-2 opacity-60">CATEGORY</label>
            <v-select 
              v-model="newBudget.category" 
              :items="categoryOptions" 
              item-title="label"
              item-value="value" 
              variant="outlined" 
              rounded="lg" 
              density="comfortable"
              placeholder="Choose a category" 
              class="font-weight-bold" 
              @update:model-value="onCategoryChange"
            />
          </div>

          <div class="mb-4">
            <label class="d-block text-subtitle-2 font-weight-black mb-3 opacity-60">
              MONTHLY BUDGET LIMIT (₹)
            </label>
            <v-text-field 
              v-model="newBudget.amount_limit" 
              type="number" 
              variant="outlined" 
              rounded="lg"
              prefix="₹" 
              placeholder="Enter amount" 
              hide-details 
              required
              class="font-weight-black text-h6"
            />
          </div>

          <div class="d-flex ga-4 justify-end mt-10">
            <v-btn variant="text" rounded="pill" class="text-none px-8 font-weight-black" @click="emit('close')">
              Cancel
            </v-btn>
            <v-btn color="primary" rounded="pill" class="text-none px-8 btn-primary-glow font-weight-black" type="submit" size="large">
              Save Budget
            </v-btn>
          </div>
        </v-form>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.premium-glass-card {
  background: rgba(var(--v-theme-surface), 0.6) !important;
  backdrop-filter: blur(12px);
  border: 1px solid rgba(var(--v-border-color), 0.1);
}

.line-height-1 {
  line-height: 1;
}

.btn-primary-glow {
  box-shadow: 0 4px 15px rgba(var(--v-theme-primary), 0.3);
}

.no-hover:hover {
  transform: none !important;
  box-shadow: none !important;
}

.border-b {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.1);
}
</style>
