<script setup lang="ts">
import { computed } from 'vue'
import { Bot, Brain, X, Calendar, Tag, EyeOff } from 'lucide-vue-next'

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
</script>

<template>
    <v-dialog :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)" persistent
        max-width="850">
        <v-card class="glass-card overflow-hidden" rounded="xl">
            <v-toolbar color="warning" density="compact">
                <template v-slot:prepend>
                    <Bot :size="18" class="ml-4" />
                </template>
                <v-toolbar-title class="text-subtitle-1 font-weight-bold">Train Transaction Parser</v-toolbar-title>
                <v-spacer></v-spacer>
                <v-btn variant="text" @click="emit('update:modelValue', false)">
                    <X :size="20" />
                </v-btn>
            </v-toolbar>

            <div class="labeling-layout pa-4">
                <!-- Left: Raw Message -->
                <div class="labeling-raw h-100">
                    <div class="section-label mb-2">Message Content</div>
                    <div class="raw-content-box flex-grow-1 mb-4">
                        {{ selectedMessage?.raw_content || selectedMessage?.raw_message || 'N/A' }}
                    </div>
                    <div class="raw-meta">
                        <div class="mb-1"><span class="font-weight-bold">Sender:</span> {{ selectedMessage?.sender }}
                        </div>
                        <div class="mb-1"><span class="font-weight-bold">Source:</span> {{ selectedMessage?.source }}
                        </div>
                        <div><span class="font-weight-bold">Received:</span> {{
                            selectedMessage?.created_at ? new Date(selectedMessage.created_at).toLocaleString() :
                                'N/A' }}</div>
                    </div>
                </div>

                <!-- Right: Form -->
                <div class="labeling-form">
                    <div class="section-label mb-2">Extracted Information</div>
                    <v-row dense>
                        <v-col cols="12" md="6">
                            <v-text-field v-model="labelForm.date" label="Transaction Date" type="datetime-local"
                                density="comfortable" variant="outlined" hide-details class="mb-3">
                                <template v-slot:prepend-inner>
                                    <Calendar :size="16" class="opacity-60" />
                                </template>
                            </v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-autocomplete v-model="labelForm.type" label="Type" :items="['DEBIT', 'CREDIT']"
                                density="comfortable" variant="outlined" hide-details class="mb-3"></v-autocomplete>
                        </v-col>

                        <v-col cols="12">
                            <v-text-field v-model="labelForm.recipient" label="Merchant / Recipient"
                                placeholder="e.g. Amazon, Starbucks" density="comfortable" variant="outlined"
                                hide-details class="mb-3"></v-text-field>
                        </v-col>

                        <v-col cols="12" md="6">
                            <v-text-field v-model.number="labelForm.amount" label="Amount" prefix="₹" type="number"
                                density="comfortable" variant="outlined" hide-details class="mb-3"></v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-autocomplete v-model="labelForm.category" label="Category" :items="categoryOptions"
                                item-title="title" item-value="value" density="comfortable" variant="outlined"
                                hide-details class="mb-3">
                                <template v-slot:prepend-inner>
                                    <Tag :size="16" class="opacity-60" />
                                </template>
                            </v-autocomplete>
                        </v-col>

                        <v-col cols="12" md="6">
                            <v-text-field v-model="labelForm.account_mask" label="Account Mask"
                                placeholder="Last 4 digits" density="comfortable" variant="outlined" hide-details
                                class="mb-3"></v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-text-field v-model="labelForm.ref_id" label="Reference ID" placeholder="Txn ID"
                                density="comfortable" variant="outlined" hide-details class="mb-3"></v-text-field>
                        </v-col>

                        <v-divider class="my-2 w-100"></v-divider>
                        <v-col cols="12">
                            <p class="text-caption font-weight-bold text-warning mb-2">BALANCE ANCHORING (OPTIONAL)</p>
                        </v-col>

                        <v-col cols="12" md="6">
                            <v-text-field v-model.number="labelForm.balance" label="Bank Balance"
                                placeholder="Balance after txn" prefix="₹" type="number" density="comfortable"
                                variant="outlined" hide-details class="mb-3"></v-text-field>
                        </v-col>
                        <v-col cols="12" md="6">
                            <v-text-field v-model.number="labelForm.credit_limit" label="Credit Limit"
                                placeholder="If card txn" prefix="₹" type="number" density="comfortable"
                                variant="outlined" hide-details class="mb-3"></v-text-field>
                        </v-col>

                        <v-col cols="12">
                            <v-divider class="my-2"></v-divider>
                        </v-col>

                        <v-col cols="12" class="d-flex flex-column gap-1">
                            <v-checkbox v-model="labelForm.generate_pattern" label="Create Auto-Categorization Rule"
                                density="compact" color="primary" hide-details></v-checkbox>
                            <v-checkbox v-model="labelForm.exclude_from_reports" label="Exclude from Reports"
                                density="compact" color="warning" hide-details>
                                <template v-slot:prepend>
                                    <EyeOff :size="16" />
                                </template>
                            </v-checkbox>
                        </v-col>
                    </v-row>

                    <div class="d-flex justify-end gap-2 mt-4">
                        <v-btn variant="text" @click="emit('update:modelValue', false)">Cancel</v-btn>
                        <v-btn color="warning" @click="emit('submit')" class="px-6">
                            <template v-slot:prepend>
                                <Brain :size="18" />
                            </template>
                            Train & Approve
                        </v-btn>
                    </div>
                </div>
            </div>
        </v-card>
    </v-dialog>
</template>

<style scoped>
.glass-card {
    background: rgba(var(--v-theme-surface), 0.7);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(var(--v-border-color), 0.1);
    border-radius: 24px;
}

.labeling-layout {
    display: grid;
    grid-template-columns: 1fr 1.2fr;
    gap: 1rem;
    padding: 1rem;
}

.labeling-raw {
    background: #f9fafb;
    border-radius: 0.75rem;
    padding: 0.75rem;
    border: 1px solid #e5e7eb;
    display: flex;
    flex-direction: column;
}

.raw-content-box {
    background: white;
    padding: 0.875rem;
    border-radius: 0.5rem;
    font-family: monospace;
    font-size: 0.75rem;
    white-space: pre-wrap;
    border: 1px solid #f3f4f6;
    flex-grow: 1;
    overflow-y: auto;
    max-height: 300px;
    color: #111827;
}

.raw-meta {
    margin-top: 1rem;
    font-size: 0.75rem;
    color: #6b7280;
}

.section-label {
    font-size: 0.65rem;
    text-transform: uppercase;
    color: #6b7280;
    margin-bottom: 0.5rem;
    letter-spacing: 0.05em;
}

.labeling-form .form-group {
    margin-bottom: 0.75rem;
}

.labeling-form .form-label {
    font-size: 0.75rem;
    margin-bottom: 2px;
}

.labeling-form .form-grid-2 {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.75rem;
}
</style>
