<template>
    <div class="animate-in">
        <v-row justify="center">
            <v-col cols="12" md="8" lg="6">
                <v-card class="glass-card pa-6" elevation="0">
                    <div class="text-center mb-6">
                        <div class="text-h2 mb-4">🛡️</div>
                        <h2 class="text-h5 font-weight-bold mb-2">Privacy & Anonymity</h2>
                        <p class="text-body-2 text-medium-emphasis">
                            Adjust how sensitive financial data is displayed across the application.
                        </p>
                    </div>

                    <v-label class="mb-2 font-weight-bold">Masking Factor</v-label>
                    <div class="d-flex gap-4 align-center mb-2">
                        <v-text-field v-model.number="localMaskingFactor" type="number" min="1" variant="outlined"
                            density="comfortable" hide-details class="flex-grow-1" bg-color="surface">
                        </v-text-field>
                        <v-btn color="primary" @click="handleSave" height="48" class="px-6 text-capitalize">
                            Save
                        </v-btn>
                    </div>
                    <div class="text-caption text-medium-emphasis mb-6">
                        Divide all amounts by this number (e.g., 1, 10, 100)
                    </div>

                    <v-alert icon="mdi-lightbulb-on-outline" variant="tonal" color="info" border="start"
                        class="info-box">
                        <div class="text-subtitle-2 font-weight-bold mb-1">How it works</div>
                        <div class="text-body-2">
                            If you set the factor to <strong>10</strong>, a transaction of
                            <strong>₹10,000</strong> will be displayed as <strong>₹1,000</strong>.
                            This allows you to share your screen or demo the app without revealing actual values.
                        </div>
                    </v-alert>
                </v-card>
            </v-col>
        </v-row>
    </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useSettingsStore } from '@/stores/settings'
import { useNotificationStore } from '@/stores/notification'

const settingsStore = useSettingsStore()
const notify = useNotificationStore()

const localMaskingFactor = ref(settingsStore.maskingFactor)

// Sync local state when store changes (optional, but good if changed elsewhere)
watch(() => settingsStore.maskingFactor, (newVal) => {
    localMaskingFactor.value = newVal
})

function handleSave() {
    settingsStore.maskingFactor = localMaskingFactor.value
    notify.success("Settings saved")
}
</script>

<style scoped>
.glass-card {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.2);
    border-radius: 16px;
}

.animate-in {
    animation: slideUp 0.4s ease-out forwards;
}

@keyframes slideUp {
    from {
        opacity: 0;
        transform: translateY(10px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
