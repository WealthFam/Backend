<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { Target, X, Check } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
    holding: any
    modelValue: boolean
}>()

const emit = defineEmits(['update:modelValue', 'success'])

const notify = useNotificationStore()
const { formatAmount } = useCurrency()

const goals = ref<any[]>([])
const loading = ref(false)
const processing = ref(false)
const selectedGoalId = ref<string | null>(null)

const fetchGoals = async () => {
    loading.value = true
    try {
        const res = await financeApi.getInvestmentGoals()
        goals.value = res.data

        // If holding already has a goal_id, pre-select it
        if (props.holding?.goal_id) {
            selectedGoalId.value = props.holding.goal_id
        }
    } catch (e) {
        notify.error("Failed to load goals")
    } finally {
        loading.value = false
    }
}

const handleLink = async () => {
    if (!selectedGoalId.value) {
        // If unlinking (selecting none when previously linked)
        if (props.holding?.goal_id) {
            processing.value = true
            try {
                await financeApi.unlinkHoldingFromGoal(props.holding.goal_id, props.holding.id)
                notify.success("Goal unlinked successfully")
                emit('success')
                emit('update:modelValue', false)
            } catch (e) {
                notify.error("Failed to unlink goal")
            } finally {
                processing.value = false
            }
        }
        return
    }

    processing.value = true
    try {
        await financeApi.linkHoldingToGoal(selectedGoalId.value, props.holding.id)
        notify.success("Goal linked successfully")
        emit('success')
        emit('update:modelValue', false)
    } catch (e) {
        notify.error("Failed to link goal")
    } finally {
        processing.value = false
    }
}

onMounted(fetchGoals)
</script>

<template>
    <v-dialog :model-value="modelValue" @update:model-value="val => emit('update:modelValue', val)" max-width="450">
        <v-card rounded="xl" class="premium-glass-modal overflow-hidden">
            <div class="px-6 pt-6 pb-2 d-flex justify-space-between align-start">
                <div>
                    <div class="text-overline font-weight-black text-primary mb-1 letter-spacing-2">Link to Goal</div>
                    <h2 class="text-h5 font-weight-black text-content">Strategic Alignment</h2>
                </div>
                <v-btn icon variant="text" @click="emit('update:modelValue', false)" density="comfortable"
                    class="bg-surface-variant bg-opacity-10 opacity-70 hover:opacity-100">
                    <X :size="20" />
                </v-btn>
            </div>

            <v-card-text class="px-6 py-4">
                <div class="fund-summary mb-6 pa-4 rounded-xl bg-surface-variant bg-opacity-5 border border-opacity-10">
                    <div class="text-caption font-weight-bold text-medium-emphasis mb-1">SELECTED FUND</div>
                    <div class="text-h6 font-weight-black text-truncate">{{ holding?.scheme_name }}</div>
                    <div class="d-flex justify-space-between align-center mt-2">
                        <span class="text-caption font-weight-bold opacity-60">Value: {{
                            formatAmount(holding?.current_value) }}</span>
                        <span class="text-caption font-weight-bold opacity-60">Folio: {{ holding?.folio_number }}</span>
                    </div>
                </div>

                <div v-if="loading" class="d-flex flex-column align-center py-10">
                    <v-progress-circular indeterminate color="primary" />
                    <span class="mt-4 text-caption font-weight-bold opacity-60">Loading your goals...</span>
                </div>

                <div v-else-if="goals.length === 0" class="text-center py-10 px-6">
                    <v-avatar color="primary" variant="tonal" size="64" class="mb-4">
                        <Target :size="32" class="text-primary" />
                    </v-avatar>
                    <div class="text-h6 font-weight-black mb-1">No Goals Found</div>
                    <p class="text-caption font-weight-bold text-medium-emphasis mb-6">Create a financial goal first to
                        link your mutual funds to it.</p>
                    <v-btn color="primary" variant="flat" rounded="lg" to="/investment-goals"
                        class="px-8 font-weight-black text-none">
                        Go to Goals
                    </v-btn>
                </div>

                <div v-else>
                    <label class="text-caption font-weight-bold text-medium-emphasis mb-3 d-block">SELECT GOAL</label>
                    <v-radio-group v-model="selectedGoalId" class="goals-list" hide-details>
                        <v-card v-for="goal in goals" :key="goal.id" variant="flat"
                            class="mb-3 goal-item-card transition-all"
                            :class="{ 'active-goal': selectedGoalId === goal.id }" @click="selectedGoalId = goal.id">
                            <v-card-text class="pa-4 d-flex align-center cursor-pointer">
                                <v-avatar :style="{ background: goal.color + '15' }" rounded="lg" size="40"
                                    class="mr-4 border border-opacity-10">
                                    <span class="text-h6" :style="{ color: goal.color }">{{ goal.icon }}</span>
                                </v-avatar>
                                <div class="flex-grow-1 overflow-hidden mr-4">
                                    <div class="text-subtitle-2 font-weight-black text-truncate">{{ goal.name }}</div>
                                    <v-progress-linear :model-value="goal.progress_percentage" :color="goal.color"
                                        height="4" rounded="pill" class="mt-1" />
                                </div>
                                <v-radio :value="goal.id" color="primary" />
                            </v-card-text>
                        </v-card>

                        <!-- Unlink Option if already linked -->
                        <v-btn v-if="holding?.goal_id" variant="text" block color="error"
                            class="text-none font-weight-bold mt-2" @click="selectedGoalId = null">
                            Clear Link (Unlink)
                        </v-btn>
                    </v-radio-group>
                </div>
            </v-card-text>

            <v-card-actions class="px-6 pb-6 pt-2">
                <v-btn variant="text" @click="emit('update:modelValue', false)" height="48" rounded="lg"
                    class="px-6 font-weight-bold text-none text-medium-emphasis">
                    Cancel
                </v-btn>
                <v-spacer />
                <v-btn color="primary" variant="flat" rounded="lg" height="48"
                    class="px-8 font-weight-black text-none elevation-4" :disabled="loading || processing"
                    :loading="processing" @click="handleLink">
                    <Check :size="18" class="mr-2" />
                    {{ selectedGoalId ? 'Link to Goal' : 'Save' }}
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.premium-glass-modal {
    background: rgba(var(--v-theme-surface), 0.9) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1) !important;
}

.goal-item-card {
    background: rgba(var(--v-theme-surface-variant), 0.03) !important;
    border: 1px solid rgba(var(--v-border-color), 0.05) !important;
    border-radius: 12px !important;
}

.goal-item-card.active-goal {
    background: rgba(var(--v-theme-primary), 0.03) !important;
    border: 1px solid rgba(var(--v-theme-primary), 0.2) !important;
}

.transition-all {
    transition: all 0.2s ease;
}

.fund-summary {
    background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.05), rgba(var(--v-theme-secondary), 0.05));
}
</style>
