<template>
    <div class="animate-in">
        <v-row>
            <!-- Left Column: Config -->
            <v-col cols="12" md="8">
                <!-- AI Status Hero -->
                <v-card class="ai-toggle-banner mb-6 px-6 py-6 d-flex align-center justify-space-between" elevation="10"
                    rounded="xl">
                    <div class="d-flex flex-column text-white">
                        <h3 class="text-h6 font-weight-black">AI Transaction Safety Net</h3>
                        <p class="text-subtitle-2 opacity-90 mb-0">Automatically extract details when static rules fail.
                        </p>
                    </div>
                    <v-switch v-model="aiStore.aiForm.is_enabled" color="white" inset hide-details
                        density="comfortable"></v-switch>
                </v-card>

                <v-card class="premium-glass-card mb-6" elevation="0">
                    <v-card-title class="d-flex align-center gap-3 py-4 px-6 border-b">
                        <v-avatar color="primary" variant="tonal" size="40" rounded="lg">
                            <Cpu :size="24" class="text-primary" />
                        </v-avatar>
                        <span class="text-h6 font-weight-black font-family-premium">LLM Configuration</span>
                    </v-card-title>

                    <v-card-text class="pa-6">
                        <v-form @submit.prevent="aiStore.saveAiSettings">
                            <v-row>
                                <v-col cols="12" sm="6">
                                    <v-select v-model="aiStore.aiForm.provider" label="AI Provider"
                                        :items="[{ title: 'Google Gemini', value: 'gemini' }]" variant="outlined">
                                        <template v-slot:prepend-inner>
                                            <Sparkles :size="20" />
                                        </template>
                                    </v-select>
                                </v-col>
                                <v-col cols="12" sm="6">
                                    <div class="d-flex gap-2 align-center">
                                        <v-select v-model="aiStore.aiForm.model_name" label="Model Selection"
                                            :items="aiStore.aiModels" item-title="label" item-value="value"
                                            variant="outlined" class="flex-grow-1" hide-details>
                                            <template v-slot:item="{ props, item }">
                                                <v-list-item v-bind="props" :subtitle="(item.raw as any).detail">
                                                    <template v-slot:append>
                                                        <v-chip size="x-small"
                                                            :color="(item.raw as any).speed === 'Fast' ? 'success' : 'primary'"
                                                            variant="tonal">
                                                            {{ (item.raw as any).speed }}
                                                        </v-chip>
                                                    </template>
                                                </v-list-item>
                                            </template>
                                        </v-select>
                                        <v-btn icon variant="tonal" density="comfortable" @click="aiStore.fetchAiModels"
                                            title="Refresh Models">
                                            <RefreshCw :size="18" />
                                        </v-btn>
                                    </div>
                                </v-col>
                            </v-row>

                            <div class="mt-4">
                                <v-text-field v-model="aiStore.aiForm.api_key" label="Secure API Key"
                                    :type="showApiKey ? 'text' : 'password'"
                                    :placeholder="aiStore.aiForm.has_api_key ? 'Using stored key...' : 'Paste API key...'"
                                    variant="outlined" persistent-hint
                                    hint="Keys are encrypted at rest. Visibility toggled via eye icon."
                                    hide-details="auto">
                                    <template v-slot:append-inner>
                                        <v-btn icon variant="text" density="compact" @click="showApiKey = !showApiKey">
                                            <component :is="showApiKey ? EyeOff : Eye" :size="16"
                                                class="text-medium-emphasis" />
                                        </v-btn>
                                    </template>
                                </v-text-field>
                            </div>

                            <div class="mt-6">
                                <div class="d-flex justify-space-between align-center mb-2">
                                    <label class="v-label font-weight-bold">System Instruction</label>
                                    <v-btn variant="text" density="compact" color="primary"
                                        class="font-weight-bold text-caption" @click="resetPrompt">
                                        Reset to Default
                                    </v-btn>
                                </div>
                                <v-textarea v-model="aiStore.aiForm.prompts.parsing" rows="4" variant="outlined"
                                    class="font-mono text-body-2" hide-details></v-textarea>
                                <div class="text-caption text-medium-emphasis mt-2">
                                    Define how the AI should structure the extracted JSON data.
                                </div>
                            </div>

                            <div class="d-flex justify-end mt-6 pt-4 border-t">
                                <v-btn type="submit" color="primary" size="large" class="px-6 font-weight-bold">
                                    Save Preferences
                                </v-btn>
                            </div>
                        </v-form>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Right Column: Playground -->
            <v-col cols="12" md="4">
                <div class="sticky-top">
                    <v-card class="premium-glass-card" elevation="0">
                        <v-card-title class="d-flex align-center gap-3 py-4 px-6 border-b">
                            <v-avatar color="warning" variant="tonal" size="32" rounded="lg">
                                <Beaker :size="18" class="text-warning" />
                            </v-avatar>
                            <span class="text-subtitle-1 font-weight-black">Test Playground</span>
                        </v-card-title>

                        <v-card-text class="pa-4">
                            <p class="text-caption text-medium-emphasis mb-4">
                                Paste a message below to see how the current configuration parses it.
                            </p>

                            <v-textarea v-model="testMessage" rows="3" variant="outlined" bg-color="grey-lighten-5"
                                class="text-body-2 mb-4" placeholder="e.g. Spent Rs 500 at Amazon..."
                                hide-details></v-textarea>

                            <v-btn block color="primary" class="mb-6 font-weight-bold" :loading="aiStore.isTestingAi"
                                @click="handleTest">
                                {{ aiStore.isTestingAi ? 'Analyzing...' : 'Test Extraction' }}
                            </v-btn>

                            <div class="code-block pa-4 rounded-lg bg-grey-darken-4 text-white font-mono text-caption overflow-auto"
                                style="min-height: 200px; max-height: 400px;">
                                <div v-if="!aiStore.aiTestResult && !aiStore.isTestingAi" class="text-grey font-italic">
                                    Waiting for data...
                                </div>
                                <div v-if="aiStore.isTestingAi" class="text-indigo-lighten-3 animate-pulse">
                                    > Initializing Gemini provider...<br>
                                    > Sending payload...
                                </div>
                                <pre v-if="aiStore.aiTestResult">{{ JSON.stringify(aiStore.aiTestResult.data ||
                                    aiStore.aiTestResult.message, null, 2) }}</pre>
                            </div>
                        </v-card-text>
                    </v-card>
                </div>
            </v-col>
        </v-row>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useAiStore } from '@/stores/ai'
import { Cpu, RefreshCw, Beaker, Eye, EyeOff, Sparkles } from 'lucide-vue-next'

const aiStore = useAiStore()
const showApiKey = ref(false)

const testMessage = ref("Spent Rs 500.50 at Amazon using card ending in 1234 on 14/01/2026")

const resetPrompt = () => {
    aiStore.aiForm.prompts.parsing = "Extract transaction details from the following message. Return JSON with: amount (number), date (DD/MM/YYYY), recipient (string), account_mask (4 digits), ref_id (string or null), type (DEBIT/CREDIT)."
}

const handleTest = () => {
    aiStore.testAi(testMessage.value)
}

onMounted(() => {
    aiStore.fetchAiSettings()
})
</script>

<style scoped>
/* glass-card removed - using global premium-glass-card */

.ai-toggle-banner {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, rgba(var(--v-theme-primary), 0.8) 100%);
    border: none;
}

.sticky-top {
    position: sticky;
    top: 24px;
}

.code-block {
    box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.3);
}

.animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes pulse {

    0%,
    100% {
        opacity: 1;
    }

    50% {
        opacity: .5;
    }
}
</style>
