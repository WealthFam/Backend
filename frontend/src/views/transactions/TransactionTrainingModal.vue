<template>
    <v-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" persistent
        max-width="720" transition="scale-transition">
        <v-card class="premium-training-modal" rounded="xl">
            <!-- Modal Background Glow -->
            <div class="modal-bg-glow"></div>
            <div class="modal-corner-accent top-left"></div>
            <div class="modal-corner-accent bottom-right"></div>

            <v-toolbar color="primary" class="px-2 training-toolbar" height="52">
                <template v-slot:prepend>
                    <v-avatar color="white" size="26" class="ml-1 elevation-4 cognitive-pulse">
                        <Brain :size="15" class="text-primary" />
                    </v-avatar>
                </template>
                <div class="d-flex flex-column ml-2">
                    <v-toolbar-title class="text-subtitle-2 font-weight-black tracking-tight leading-none">Neural Parser</v-toolbar-title>
                    <span class="text-micro-nano opacity-70 font-weight-bold uppercase tracking-widest mt-n0.5">Training Session</span>
                </div>
                <v-spacer></v-spacer>
                <v-btn icon variant="tonal" density="compact" @click="emit('update:modelValue', false)" class="mr-1">
                    <X :size="16" />
                </v-btn>
            </v-toolbar>

            <div class="training-layout">
                <!-- Left Column: Source & Intelligence -->
                <div class="source-pane pa-3 d-flex flex-column">
                    <div class="d-flex align-center justify-space-between mb-2">
                        <div class="d-flex align-center gap-1.5">
                            <Fingerprint :size="13" class="text-primary" />
                            <span class="text-micro font-weight-black uppercase">Forensic View</span>
                        </div>
                        <div class="status-dot online"></div>
                    </div>

                    <div class="raw-message-container flex-grow-1">
                        <div class="message-header d-flex align-center justify-space-between px-2.5 py-1.5 border-b">
                            <span class="text-micro-nano font-weight-black text-uppercase opacity-50 tracking-widest">Protocol</span>
                            <span class="text-micro-nano font-weight-bold opacity-40">SYNCED</span>
                        </div>
                        <div class="message-body pa-2.5">
                            <template v-for="(chunk, i) in highlightedContent" :key="i">
                                <span v-if="chunk.highlight" class="data-highlight" :style="{ backgroundColor: chunk.color + '33', borderBottomColor: chunk.color }">
                                    {{ chunk.text }}
                                </span>
                                <span v-else>{{ chunk.text }}</span>
                            </template>
                        </div>
                    </div>

                    <div class="debugger-meta mt-2 pa-2 rounded-lg">
                        <v-row dense>
                            <v-col cols="6">
                                <div class="meta-item-tech">
                                    <div class="meta-label">ID_REF</div>
                                    <div class="meta-val truncate">{{ selectedMessage?.id?.substring(0, 6) }}</div>
                                </div>
                            </v-col>
                            <v-col cols="6">
                                <div class="meta-item-tech">
                                    <div class="meta-label">TIME</div>
                                    <div class="meta-val">{{ selectedMessage?.created_at ? new Date(selectedMessage.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'N/A' }}</div>
                                </div>
                            </v-col>
                        </v-row>
                    </div>

                    <div class="ai-hint-futuristic mt-3 pa-2.5 rounded-lg d-flex align-top gap-2.5">
                        <div class="hint-icon-wrap">
                            <Bot :size="14" class="text-primary" />
                        </div>
                        <p class="text-micro-nano text-medium-emphasis leading-tight mb-0">Detected action. Mapping vector.</p>
                    </div>
                </div>

                <!-- Right Column: Learning Form -->
                <div class="form-pane pa-3 bg-surface-light">
                    <div class="d-flex align-center justify-space-between mb-3">
                        <div class="d-flex align-center gap-2">
                            <TrendingUp :size="15" class="text-primary" />
                            <span class="text-caption font-weight-black opacity-60">Annotation Details</span>
                        </div>
                        <v-btn variant="tonal" density="compact" color="primary" rounded="lg" 
                            class="px-2 text-micro-nano font-weight-black" :loading="isAutoParsing"
                            @click="handleAutoParse">
                            <template v-slot:prepend>
                                <Sparkles :size="12" class="mr-1" />
                            </template>
                            AI AUTO-PARSE
                        </v-btn>
                    </div>

                    <v-row dense>
                        <!-- Basic Info Row -->
                        <v-col cols="12" md="6">
                            <v-text-field v-model="labelForm.date" label="Date" type="datetime-local"
                                density="compact" variant="outlined" rounded="lg" class="modern-field mb-1 font-weight-bold">
                            </v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-autocomplete v-model="labelForm.type" label="Flow" :items="['DEBIT', 'CREDIT']"
                                density="compact" variant="outlined" rounded="lg" class="modern-field mb-1 font-weight-bold">
                            </v-autocomplete>
                        </v-col>

                        <v-col cols="12">
                            <v-text-field v-model="labelForm.recipient" label="Merchant Entity"
                                placeholder="Amazon, Uber, etc." density="compact" variant="outlined"
                                rounded="lg" class="modern-field mb-1 font-weight-bold">
                            </v-text-field>
                        </v-col>

                        <v-col cols="12" md="6">
                            <v-text-field v-model.number="labelForm.amount" label="Value" prefix="₹" type="number"
                                density="compact" variant="outlined" rounded="lg" class="modern-field mb-1 font-weight-black text-subtitle-1">
                            </v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-autocomplete v-model="labelForm.category" label="Category" :items="categoryOptions"
                                item-title="title" item-value="value" density="compact" variant="outlined"
                                rounded="lg" class="modern-field mb-1 font-weight-bold">
                            </v-autocomplete>
                        </v-col>

                        <v-col cols="12" md="5">
                            <v-text-field v-model="labelForm.account_mask" label="Account"
                                placeholder="Last 4" density="compact" variant="outlined" rounded="lg"
                                class="modern-field mb-1 font-weight-bold">
                            </v-text-field>
                        </v-col>
                        <v-col cols="12" md="7">
                            <v-text-field v-model="labelForm.ref_id" label="Registry ID" placeholder="Txn ID"
                                density="compact" variant="outlined" rounded="lg" class="modern-field mb-1 font-weight-bold">
                            </v-text-field>
                        </v-col>

                        <!-- Advanced Section -->
                        <v-col cols="12" class="mt-0.5">
                            <v-divider class="mb-2"></v-divider>
                            <div class="d-flex align-center justify-space-between mb-2 px-1">
                                <span class="text-micro font-weight-black uppercase color-primary">Anchoring & Logic</span>
                                <v-chip size="x-small" variant="tonal" color="primary" density="compact">v2</v-chip>
                            </div>
                        </v-col>

                        <v-col cols="12" md="6">
                            <v-text-field v-model.number="labelForm.balance" label="Balance"
                                prefix="₹" type="number" density="compact"
                                variant="outlined" rounded="lg" class="modern-field mb-0 font-weight-bold"></v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-switch v-model="labelForm.generate_pattern" label="Create Rule"
                                density="compact" color="success" hide-details inset class="font-weight-bold ml-1"></v-switch>
                        </v-col>

                        <v-col cols="12">
                            <v-checkbox v-model="labelForm.exclude_from_reports" label="Exclude from reports"
                                density="compact" color="error" hide-details class="font-weight-bold mt-n2"></v-checkbox>
                        </v-col>
                    </v-row>

                    <!-- Footer Actions -->
                    <div class="actions-gradient mt-2 pt-2 d-flex justify-end gap-2 border-t">
                        <v-btn variant="tonal" rounded="lg" height="36" @click="emit('update:modelValue', false)" class="px-3 text-none font-weight-bold text-caption">Cancel</v-btn>
                        <v-btn color="primary" rounded="lg" height="36" @click="emit('submit')" class="px-5 text-none font-weight-black text-caption elevation-4 shine-effect">
                            Finalize
                        </v-btn>
                    </div>
                </div>
            </div>
        </v-card>
    </v-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { Bot, Brain, X, Fingerprint, TrendingUp, Sparkles } from 'lucide-vue-next'
import { aiApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

const props = defineProps<{
    modelValue: boolean
    selectedMessage: any
    labelForm: any
    categories: any[]
}>()

const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    'submit': []
}>()

const categoryOptions = computed(() => {
    const list: any[] = []
    const flatten = (cats: any[], depth = 0) => {
        cats.forEach(c => {
            const prefix = depth > 0 ? '　'.repeat(depth) + '└ ' : ''
            list.push({
                title: `${prefix}${c.icon || '🏷️'} ${c.name}`,
                value: c.name
            })
            if (c.subcategories && c.subcategories.length > 0) {
                flatten(c.subcategories, depth + 1)
            }
        })
    }
    flatten(props.categories)
    if (!list.find(o => o.value === 'Uncategorized')) {
        list.push({ title: '🏷️ Uncategorized', value: 'Uncategorized' })
    }
    return list
})

interface MessageChunk {
    text: string
    highlight: boolean
    color?: string
}

const highlightedContent = computed<MessageChunk[]>(() => {
    let content = props.selectedMessage?.raw_content || props.selectedMessage?.raw_message || ''
    if (!content) return [{ text: 'No Payload', highlight: false }]

    // Values to find and highlight
    const searchPairs = [
        { val: props.labelForm.amount?.toString(), color: 'var(--v-theme-success)' },
        { val: props.labelForm.recipient, color: 'var(--v-theme-primary)' },
        { val: props.labelForm.ref_id, color: 'var(--v-theme-warning)' }
    ].filter(p => p.val && p.val.length > 2)

    if (searchPairs.length === 0) return [{ text: content, highlight: false }]

    // Simple multi-match split logic
    let temp: MessageChunk[] = [{ text: content, highlight: false }]
    
    searchPairs.forEach(pair => {
        const nextTemp: MessageChunk[] = []
        temp.forEach(chunk => {
            if (chunk.highlight) {
                nextTemp.push(chunk)
                return
            }
            
            const index = chunk.text.toLowerCase().indexOf(pair.val!.toLowerCase())
            if (index !== -1) {
                if (index > 0) nextTemp.push({ text: chunk.text.substring(0, index), highlight: false })
                nextTemp.push({ text: chunk.text.substring(index, index + pair.val!.length), highlight: true, color: pair.color })
                if (index + pair.val!.length < chunk.text.length) {
                    nextTemp.push({ text: chunk.text.substring(index + pair.val!.length), highlight: false })
                }
            } else {
                nextTemp.push(chunk)
            }
        })
        temp = nextTemp
    })

    return temp
})

const notify = useNotificationStore()
const isAutoParsing = ref(false)

const handleAutoParse = async () => {
    if (!props.selectedMessage?.id) return
    isAutoParsing.value = true
    try {
        const res = await aiApi.autoParseTrainingMessage(props.selectedMessage.id)
        const data = res.data
        if (data) {
            // Apply data to form
            if (data.amount !== undefined) props.labelForm.amount = data.amount
            if (data.recipient) props.labelForm.recipient = data.recipient
            if (data.date) {
                try {
                    const d = new Date(data.date)
                    if (!isNaN(d.getTime())) {
                        props.labelForm.date = d.toISOString().substring(0, 16)
                    }
                } catch (e) {
                    props.labelForm.date = data.date
                }
            }
            if (data.account_mask) props.labelForm.account_mask = data.account_mask
            if (data.ref_id) props.labelForm.ref_id = data.ref_id
            if (data.type) props.labelForm.type = data.type
            
            notify.success('AI Forensic extraction complete')
        }
    } catch (e) {
        // Error notification handled by interceptor or api
    } finally {
        isAutoParsing.value = false
    }
}
</script>

<style scoped>
.premium-training-modal {
    background: rgb(var(--v-theme-surface));
    position: relative;
    overflow: hidden;
    box-shadow: 0 40px 100px -20px rgba(0, 0, 0, 0.7) !important;
}

.modal-bg-glow {
    position: absolute;
    top: -10%;
    left: -10%;
    width: 60%;
    height: 60%;
    background: radial-gradient(circle, rgba(var(--v-theme-primary), 0.12) 0%, transparent 70%);
    filter: blur(60px);
    pointer-events: none;
    z-index: 0;
}

.modal-corner-accent {
    position: absolute;
    width: 100px;
    height: 100px;
    opacity: 0.05;
    pointer-events: none;
    z-index: 0;
}

.modal-corner-accent.top-left {
    top: 0;
    left: 0;
    border-top: 2px solid rgb(var(--v-theme-primary));
    border-left: 2px solid rgb(var(--v-theme-primary));
}

.modal-corner-accent.bottom-right {
    bottom: 0;
    right: 0;
    border-bottom: 2px solid rgb(var(--v-theme-primary));
    border-right: 2px solid rgb(var(--v-theme-primary));
}

.training-toolbar {
    background: linear-gradient(90deg, #0f172a 0%, #1e293b 100%) !important;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    z-index: 1;
}

.cognitive-pulse {
    animation: cognitive-glow 4s infinite ease-in-out;
}

@keyframes cognitive-glow {
    0%, 100% { box-shadow: 0 0 0px rgba(var(--v-theme-primary), 0); }
    50% { box-shadow: 0 0 20px rgba(var(--v-theme-primary), 0.5); }
}

.training-layout {
    display: grid;
    grid-template-columns: 350px 1fr;
    min-height: 580px;
    z-index: 1;
    position: relative;
}

.source-pane {
    background: rgba(var(--v-theme-surface), 0.5);
    border-right: 1px solid rgba(var(--v-border-color), 0.1);
}

.raw-message-container {
    background: #020617;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
    box-shadow: inset 0 4px 12px rgba(0, 0, 0, 0.5);
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.message-header {
    background: rgba(255, 255, 255, 0.02);
}

.status-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    align-self: center;
}

.status-dot.online {
    background: #10b981;
    box-shadow: 0 0 10px #10b981;
}

.message-body {
    flex-grow: 1;
    overflow-y: auto;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.75rem;
    line-height: 1.8;
    color: #e2e8f0;
    scrollbar-width: thin;
}

.data-highlight {
    padding: 2px 4px;
    border-radius: 4px;
    border-bottom: 2px solid transparent;
    color: #ffffff;
    font-weight: 800;
    transition: all 0.3s ease;
}

.debugger-meta {
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(var(--v-theme-primary), 0.2);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.meta-item-tech {
    padding: 6px 10px;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

.meta-label {
    font-size: 0.6rem;
    font-weight: 900;
    color: rgb(var(--v-theme-primary));
    text-transform: uppercase;
    letter-spacing: 0.12em;
    opacity: 0.9;
}

.meta-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #f8fafc;
    font-weight: 600;
}

.ai-hint-futuristic {
    background: linear-gradient(135deg, rgba(var(--v-theme-primary), 0.12) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
    border-left: 3px solid rgb(var(--v-theme-primary));
}

.hint-icon-wrap {
    background: rgba(var(--v-theme-primary), 0.15);
    padding: 8px;
    border-radius: 10px;
}

.form-pane {
    background: #ffffff;
}

:deep(.modern-field) .v-field--outlined {
    background: #fdfdfd !important;
    transition: all 0.3s ease;
}

:deep(.modern-field) .v-field__label {
    color: rgba(0, 0, 0, 0.7) !important;
    font-weight: 600 !important;
}

:deep(.modern-field) .v-field--focused {
    box-shadow: 0 4px 24px -4px rgba(var(--v-theme-primary), 0.2) !important;
}

.shine-effect {
    position: relative;
    overflow: hidden;
}

.shine-effect::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: linear-gradient(45deg, transparent 45%, rgba(255, 255, 255, 0.3) 50%, transparent 55%);
    animation: shine 4s infinite;
}

@keyframes shine {
    0% { transform: translateX(-100%) translateY(-100%); }
    100% { transform: translateX(100%) translateY(100%); }
}

.opacity-80 {
    opacity: 0.9 !important;
}

.opacity-60 {
    opacity: 1 !important;
}

.opacity-50 {
    opacity: 0.8 !important;
}

.opacity-40 {
    opacity: 0.7 !important;
}

.text-button {
    color: rgb(var(--v-theme-primary)) !important;
    letter-spacing: 0.05em !important;
}

:deep(.modern-field) .v-field__label {
    color: #000000 !important;
    opacity: 0.8 !important;
    font-weight: 700 !important;
}

.meta-label {
    font-size: 0.6rem;
    font-weight: 900;
    color: #38bdf8; /* Brighter light blue for dark background */
    text-transform: uppercase;
    letter-spacing: 0.12em;
}

.meta-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    color: #ffffff;
    font-weight: 700;
}

@media (max-width: 900px) {
    .training-layout {
        grid-template-columns: 1fr;
    }
}
</style>
