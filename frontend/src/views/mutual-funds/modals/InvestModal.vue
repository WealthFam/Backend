<script setup lang="ts">
import { ref, computed } from 'vue'
import { useNotificationStore } from '@/stores/notification'
import { CheckCircle, ArrowRight, X } from 'lucide-vue-next'
import { useCurrency } from '@/composables/useCurrency'

defineProps<{
    modelValue: boolean
    fund: any
}>()

const emit = defineEmits(['update:modelValue', 'success'])
const notify = useNotificationStore()
const { formatAmount } = useCurrency()

const activeTab = ref('lumpsum') // lumpsum | sip
const amount = ref<number | null>(null)
const sipDate = ref<number>(5) // Day of month
const isLoading = ref(false)
const showSuccess = ref(false)

const isValid = computed(() => {
    return amount.value && amount.value > 0
})

async function handleSubmit() {
    if (!isValid.value) return
    isLoading.value = true
    try {


        // await financeApi.invest(payload) 
        // Mocking API call for now as backend might not be ready
        await new Promise(resolve => setTimeout(resolve, 1500))

        showSuccess.value = true
        setTimeout(() => {
            showSuccess.value = false
            emit('update:modelValue', false)
            emit('success')
            notify.success(`Investment of ${formatAmount(amount.value!)} initiated!`)
        }, 2000)
    } catch (e) {
        notify.error("Investment failed. Please try again.")
    } finally {
        isLoading.value = false
    }
}

function close() {
    if (!isLoading.value) {
        emit('update:modelValue', false)
    }
}
</script>

<template>
    <v-dialog :model-value="modelValue" @update:model-value="close" max-width="480" persistent>
        <v-card class="premium-glass-card pa-0 overflow-hidden" rounded="xl">
            <!-- Header -->
            <div class="px-6 py-4 border-b bg-surface-variant bg-opacity-5 d-flex justify-space-between align-center">
                <div>
                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Invest In</div>
                    <div class="text-h6 font-weight-black line-clamp-1">{{ fund?.scheme_name }}</div>
                </div>
                <v-btn icon variant="text" density="compact" @click="close">
                    <X :size="20" />
                    <!-- <span class="text-h6">&times;</span> -->
                </v-btn>
            </div>

            <div class="pa-6">
                <!-- Investment Type Tabs -->
                <v-tabs v-model="activeTab" color="primary" grow density="compact"
                    class="mb-6 rounded-lg overflow-hidden border">
                    <v-tab value="lumpsum" class="font-weight-bold">One-Time (Lumpsum)</v-tab>
                    <v-tab value="sip" class="font-weight-bold">Monthly SIP</v-tab>
                </v-tabs>

                <!-- Amount Input -->
                <div class="mb-6">
                    <label class="text-caption font-weight-bold text-medium-emphasis mb-1 d-block">Investment
                        Amount</label>
                    <v-text-field v-model.number="amount" placeholder="e.g. 5000" prefix="₹" variant="outlined"
                        rounded="lg" density="comfortable" type="number" autofocus
                        class="font-weight-black text-h6"></v-text-field>

                    <div class="d-flex gap-2 mt-2">
                        <v-chip size="small" variant="outlined" @click="amount = 5000">+ ₹5,000</v-chip>
                        <v-chip size="small" variant="outlined" @click="amount = 10000">+ ₹10,000</v-chip>
                        <v-chip size="small" variant="outlined" @click="amount = 25000">+ ₹25,000</v-chip>
                    </div>
                </div>

                <!-- SIP Date Selection -->
                <div v-if="activeTab === 'sip'" class="mb-6">
                    <label class="text-caption font-weight-bold text-medium-emphasis mb-1 d-block">SIP Date (Day of
                        Month)</label>
                    <div class="d-flex overflow-x-auto pb-2 gap-2 hide-scrollbar">
                        <div v-for="d in [1, 5, 10, 15, 20, 25]" :key="d"
                            class="date-pill cursor-pointer transition-all" :class="{ 'active': sipDate === d }"
                            @click="sipDate = d">
                            <div class="text-caption font-weight-bold">{{ d }}th</div>
                        </div>
                    </div>
                </div>

                <!-- Footer Actions -->
                <v-btn block color="primary" size="large" rounded="lg" class="font-weight-bold" :loading="isLoading"
                    :disabled="!isValid" @click="handleSubmit">
                    <span v-if="isLoading">Processing...</span>
                    <span v-else>Invest {{ amount ? formatAmount(amount) : '' }}</span>
                    <ArrowRight v-if="!isLoading" :size="18" class="ml-2" />
                </v-btn>
            </div>

            <!-- Success Overlay -->
            <v-overlay v-model="showSuccess" contained class="align-center justify-center">
                <div class="text-center pa-6">
                    <div class="bg-success rounded-circle d-inline-flex pa-4 mb-4 elevation-4">
                        <CheckCircle :size="48" color="white" />
                    </div>
                    <h3 class="text-h5 font-weight-black text-white mb-1">Success!</h3>
                    <p class="text-body-1 text-white opacity-90">Investment initiated successfully.</p>
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

.date-pill {
    min-width: 48px;
    height: 48px;
    border-radius: 12px;
    border: 1px solid rgba(var(--v-border-color), 0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(var(--v-theme-surface), 0.5);
}

.date-pill:hover {
    background: rgba(var(--v-theme-primary), 0.05);
    border-color: rgba(var(--v-theme-primary), 0.3);
}

.date-pill.active {
    background: rgb(var(--v-theme-primary));
    color: white;
    border-color: rgb(var(--v-theme-primary));
    box-shadow: 0 4px 12px rgba(var(--v-theme-primary), 0.3);
}

.hide-scrollbar::-webkit-scrollbar {
    display: none;
}

.hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
}
</style>
