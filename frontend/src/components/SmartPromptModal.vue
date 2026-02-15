<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
    isOpen: boolean
    data: {
        txnId: string
        category: string
        pattern: string
        count: number
        createRule: boolean
        applyToSimilar: boolean
        excludeFromReports: boolean
    }
}>()

const emit = defineEmits(['close', 'confirm'])

const hasSimilar = computed(() => props.data.count > 0)

function handleConfirm() {
    emit('confirm')
}
</script>

<template>
    <v-dialog :model-value="isOpen" @update:model-value="emit('close')" max-width="500px">
        <v-card class="premium-modal overflow-hidden">
            <!-- Header with Gradient -->
            <div class="modal-header-gradient pa-6 text-white relative-pos">
                <div class="d-flex align-center justify-space-between mb-2">
                    <div class="d-flex align-center gap-3">
                        <v-icon icon="Sparkles" size="32" class="header-icon-glow"></v-icon>
                        <div>
                            <h2 class="text-h5 font-weight-black mb-0">Smart Action</h2>
                            <p class="text-caption opacity-80 font-weight-bold">Automate your categorization</p>
                        </div>
                    </div>
                    <v-btn icon="X" variant="text" color="white" @click="emit('close')" density="compact"></v-btn>
                </div>
            </div>

            <v-card-text class="pa-6 pt-8">
                <!-- Info Section -->
                <div class="info-banner mb-6 d-flex align-center gap-4 pa-4 rounded-xl">
                    <div class="pattern-avatar d-flex align-center justify-center">
                        <v-icon icon="Tag" color="primary"></v-icon>
                    </div>
                    <div>
                        <div class="text-caption text-medium-emphasis font-weight-bold text-uppercase letter-spacing-1">
                            Detected Pattern</div>
                        <div class="text-subtitle-1 font-weight-black text-primary">"{{ data.pattern }}"</div>
                    </div>
                </div>

                <div class="text-body-2 text-medium-emphasis mb-6">
                    You've assigned <strong>{{ data.category }}</strong> to this transaction.
                    <span v-if="hasSimilar">
                        We found <strong>{{ data.count }}</strong> similar transactions in your history.
                    </span>
                </div>

                <!-- Options -->
                <div class="options-container d-flex flex-column gap-3">
                    <v-hover v-slot="{ isHovering, props: hoverProps }">
                        <div v-bind="hoverProps"
                            class="option-pill d-flex align-center pa-4 rounded-xl transition-all cursor-pointer"
                            :class="{ 'active': data.createRule, 'hover': isHovering }"
                            @click="data.createRule = !data.createRule">
                            <div class="option-icon-box mr-4">
                                <v-icon icon="ShieldCheck"
                                    :color="data.createRule ? 'primary' : 'medium-emphasis'"></v-icon>
                            </div>
                            <div class="flex-grow-1">
                                <div class="text-subtitle-2 font-weight-bold mb-0">Create Permanent Rule</div>
                                <div class="text-caption opacity-70">Auto-categorize matching future transactions</div>
                            </div>
                            <v-checkbox-btn v-model="data.createRule" color="primary" density="compact"
                                hide-details></v-checkbox-btn>
                        </div>
                    </v-hover>

                    <v-hover v-slot="{ isHovering, props: hoverProps }" v-if="hasSimilar">
                        <div v-bind="hoverProps"
                            class="option-pill d-flex align-center pa-4 rounded-xl transition-all cursor-pointer"
                            :class="{ 'active': data.applyToSimilar, 'hover': isHovering }"
                            @click="data.applyToSimilar = !data.applyToSimilar">
                            <div class="option-icon-box mr-4">
                                <v-icon icon="History"
                                    :color="data.applyToSimilar ? 'primary' : 'medium-emphasis'"></v-icon>
                            </div>
                            <div class="flex-grow-1">
                                <div class="text-subtitle-2 font-weight-bold mb-0">Apply to Past History</div>
                                <div class="text-caption opacity-70">Update {{ data.count }} similar transactions now
                                </div>
                            </div>
                            <v-checkbox-btn v-model="data.applyToSimilar" color="primary" density="compact"
                                hide-details></v-checkbox-btn>
                        </div>
                    </v-hover>

                    <v-hover v-slot="{ isHovering, props: hoverProps }">
                        <div v-bind="hoverProps"
                            class="option-pill d-flex align-center pa-4 rounded-xl transition-all cursor-pointer"
                            :class="{ 'active': data.excludeFromReports, 'hover': isHovering }"
                            @click="data.excludeFromReports = !data.excludeFromReports">
                            <div class="option-icon-box mr-4">
                                <v-icon icon="EyeOff"
                                    :color="data.excludeFromReports ? 'primary' : 'medium-emphasis'"></v-icon>
                            </div>
                            <div class="flex-grow-1">
                                <div class="text-subtitle-2 font-weight-bold mb-0">Exclude from Reports</div>
                                <div class="text-caption opacity-70">Don't count matching transactions in analytics
                                </div>
                            </div>
                            <v-checkbox-btn v-model="data.excludeFromReports" color="primary" density="compact"
                                hide-details></v-checkbox-btn>
                        </div>
                    </v-hover>
                </div>
            </v-card-text>

            <v-divider class="opacity-10"></v-divider>

            <v-card-actions class="pa-6 bg-surface">
                <v-spacer></v-spacer>
                <v-btn variant="text" color="medium-emphasis" class="px-6 rounded-xl font-weight-bold"
                    @click="emit('close')">Skip</v-btn>
                <v-btn color="primary" class="px-8 rounded-xl font-weight-black shadow-primary" @click="handleConfirm">
                    Approve Action
                </v-btn>
            </v-card-actions>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.premium-modal {
    border-radius: 28px !important;
    background: rgb(var(--v-theme-surface)) !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
}

.modal-header-gradient {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, #6366f1 100%);
}

.header-icon-glow {
    filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.4));
}

.info-banner {
    background: rgba(var(--v-theme-primary), 0.05);
    border: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.pattern-avatar {
    width: 48px;
    height: 48px;
    background: white;
    border-radius: 16px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.options-container {
    perspective: 1000px;
}

.option-pill {
    border: 2px solid rgba(var(--v-border-color), 0.05);
    background: rgba(var(--v-theme-surface), 1);
}

.option-pill.hover {
    border-color: rgba(var(--v-theme-primary), 0.2);
    transform: translateY(-2px);
    box-shadow: 0 8px 16px -4px rgba(0, 0, 0, 0.05);
}

.option-pill.active {
    border-color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.02);
}

.option-icon-box {
    width: 44px;
    height: 44px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #f8fafc;
    border-radius: 12px;
}

.option-pill.active .option-icon-box {
    background: rgba(var(--v-theme-primary), 0.1);
}

.letter-spacing-1 {
    letter-spacing: 1px;
}

.shadow-primary {
    box-shadow: 0 4px 14px 0 rgba(var(--v-theme-primary), 0.39) !important;
}

.relative-pos {
    position: relative;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
}
</style>
