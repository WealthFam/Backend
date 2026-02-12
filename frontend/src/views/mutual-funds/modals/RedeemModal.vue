<script setup lang="ts">
import { ref, computed } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { CheckCircle } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

const props = defineProps<{
    modelValue: boolean
    holding: any // Contains units, current_value, last_nav
}>()

const emit = defineEmits(['update:modelValue', 'success'])
const notify = useNotificationStore()
const { formatAmount } = useCurrency()

const activeTab = ref('amount') // amount | units
const inputValue = ref<number | null>(null)
const isLoading = ref(false)
const showSuccess = ref(false)

// Formatting
const estimatedValue = computed(() => {
    if (!inputValue.value || !props.holding) return 0
    if (activeTab.value === 'units') {
        return inputValue.value * (Number(props.holding.last_nav) || 0)
    } else {
        return inputValue.value / (Number(props.holding.last_nav) || 1)
    }
})

const isValid = computed(() => {
    if (!inputValue.value || inputValue.value <= 0) return false
    if (activeTab.value === 'units') {
        return inputValue.value <= props.holding.units
    } else {
        return inputValue.value <= props.holding.current_value
    }
})

async function handleSubmit() {
    if (!isValid.value) return
    isLoading.value = true
    try {


        // await financeApi.redeem(payload)
        await new Promise(resolve => setTimeout(resolve, 1500))

        showSuccess.value = true
        setTimeout(() => {
            showSuccess.value = false
            emit('update:modelValue', false)
            emit('success')
            notify.success("Redemption request placed successfully!")
        }, 2000)
    } catch (e) {
        notify.error("Redemption failed. Please try again.")
    } finally {
        isLoading.value = false
    }
}

function close() {
    if (!isLoading.value) emit('update:modelValue', false)
}

function setMax() {
    if (activeTab.value === 'units') {
        inputValue.value = props.holding.units
    } else {
        inputValue.value = props.holding.current_value
    }
}
</script>

<template>
    <v-dialog :model-value="modelValue" @update:model-value="close" max-width="480" persistent>
        <v-card class="premium-glass-card pa-0 overflow-hidden" rounded="xl">
            <!-- Header -->
            <div class="px-6 py-4 border-b bg-surface-variant bg-opacity-5 d-flex justify-space-between align-center">
                <div>
                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Redeem From</div>
                    <div class="text-h6 font-weight-black line-clamp-1">{{ holding?.scheme_name }}</div>
                </div>
                <v-btn icon variant="text" density="compact" @click="close">
                    <span class="text-h6">&times;</span>
                </v-btn>
            </div>

            <div class="pa-6">
                <!-- Available Balance -->
                <div
                    class="mb-6 p-4 rounded-lg bg-surface-variant bg-opacity-10 d-flex justify-space-between align-center">
                    <div>
                        <div class="text-caption font-weight-bold text-medium-emphasis">Available Units</div>
                        <div class="text-body-1 font-weight-black">{{ holding?.units?.toFixed(3) }}</div>
                    </div>
                    <div class="text-right">
                        <div class="text-caption font-weight-bold text-medium-emphasis">Current Value</div>
                        <div class="text-body-1 font-weight-black">{{ formatAmount(holding?.current_value) }}</div>
                    </div>
                </div>

                <!-- Type Toggle -->
                <v-btn-toggle v-model="activeTab" mandatory rounded="lg" color="primary" class="w-100 mb-6 border"
                    density="compact">
                    <v-btn value="amount" class="flex-1 font-weight-bold">By Amount</v-btn>
                    <v-btn value="units" class="flex-1 font-weight-bold">By Units</v-btn>
                </v-btn-toggle>

                <!-- Input -->
                <div class="mb-2">
                    <label class="text-caption font-weight-bold text-medium-emphasis mb-1 d-block">
                        {{ activeTab === 'amount' ? 'Amount to Redeem' : 'Units to Redeem' }}
                    </label>
                    <v-text-field v-model.number="inputValue" :prefix="activeTab === 'amount' ? '₹' : ''"
                        :suffix="activeTab === 'units' ? 'Units' : ''" variant="outlined" rounded="lg"
                        density="comfortable" type="number" autofocus class="font-weight-black text-h6"
                        :error-messages="!isValid && inputValue ? 'Insufficient balance' : ''">
                        <template v-slot:append-inner>
                            <v-btn size="small" variant="text" color="primary" class="font-weight-bold px-0"
                                @click="setMax">Max</v-btn>
                        </template>
                    </v-text-field>
                </div>

                <!-- Estimation -->
                <div class="mb-6 text-center text-caption font-weight-medium text-medium-emphasis" v-if="inputValue">
                    <span v-if="activeTab === 'amount'">Unknown Units (approx {{ estimatedValue.toFixed(3) }}
                        units)</span>
                    <span v-else>Approx Value: {{ formatAmount(estimatedValue) }}</span>
                    <div class="mt-1 opacity-70">Based on latest NAV: {{ holding?.last_nav }}</div>
                </div>

                <v-alert v-if="holding?.lock_in_period" type="warning" variant="tonal" density="compact"
                    class="mb-6 text-caption">
                    Some units might be in lock-in period. Oldest units will be redeemed first.
                </v-alert>

                <!-- Footer Actions -->
                <v-btn block color="error" size="large" rounded="lg" class="font-weight-bold" :loading="isLoading"
                    :disabled="!isValid" @click="handleSubmit">
                    Redeem {{ activeTab === 'amount' && inputValue ? formatAmount(inputValue) : '' }}
                </v-btn>
            </div>

            <!-- Success Overlay -->
            <v-overlay v-model="showSuccess" contained class="align-center justify-center">
                <div class="text-center pa-6">
                    <div class="bg-success rounded-circle d-inline-flex pa-4 mb-4 elevation-4">
                        <CheckCircle :size="48" color="white" />
                    </div>
                    <h3 class="text-h5 font-weight-black text-white mb-1">Redemption Placed!</h3>
                    <p class="text-body-1 text-white opacity-90">Amount will credit in 3-4 working days.</p>
                </div>
            </v-overlay>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.1) !important;
}

.flex-1 {
    flex: 1;
}
</style>
