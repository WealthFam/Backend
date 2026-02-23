<script setup lang="ts">
import { ref, reactive, watch } from 'vue'
import { financeApi } from '@/api/client'

const props = defineProps<{
    modelValue: boolean
    initialPattern?: string
    initialAlias?: string
}>()

const emit = defineEmits<{
    'update:modelValue': [value: boolean]
    'saved': []
}>()

const isOpen = ref(props.modelValue)
watch(() => props.modelValue, (val) => isOpen.value = val)
watch(isOpen, (val) => emit('update:modelValue', val))

// Form State
const loading = ref(false)
const impact = ref<number | null>(null)
const form = reactive({
    pattern: '',
    alias: '',
    update_past: true
})

// Initialize form when opening
watch(() => props.modelValue, (val) => {
    if (val) {
        form.pattern = props.initialPattern || ''
        form.alias = props.initialAlias || ''
        form.update_past = true
        impact.value = null
        checkImpact()
    }
})

let impactDebounce: any = null
function checkImpact() {
    if (!form.pattern) {
        impact.value = null
        return
    }
    if (impactDebounce) clearTimeout(impactDebounce)
    impactDebounce = setTimeout(async () => {
        try {
            const res = await financeApi.previewAliasImpact(form.pattern)
            impact.value = res.data.match_count
        } catch (e) {
            console.error(e)
        }
    }, 500)
}

async function save() {
    loading.value = true
    try {
        await financeApi.createAlias({
            pattern: form.pattern,
            alias: form.alias,
            update_past_transactions: form.update_past
        })
        emit('saved')
        isOpen.value = false
    } catch (err) {
        console.error("Failed to create alias", err)
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <v-dialog v-model="isOpen" max-width="500">
        <v-card class="rounded-xl">
            <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                <span class="text-h6 font-weight-bold">New Merchant Alias</span>
                <v-btn icon="X" variant="text" density="comfortable" @click="isOpen = false"></v-btn>
            </v-card-title>
            <v-card-text class="pa-6">
                <v-form @submit.prevent="save">
                    <v-text-field v-model="form.pattern" label="Raw Text Pattern" placeholder="e.g. AMZN MKTP"
                        variant="outlined" class="mb-4" hint="Matches if this text appears in description"
                        persistent-hint required readonly></v-text-field>

                    <v-text-field v-model="form.alias" label="Clean Merchant Name" placeholder="e.g. Amazon"
                        variant="outlined" class="mb-6" required></v-text-field>

                    <v-checkbox v-model="form.update_past" color="primary" hide-details class="mb-2">
                        <template v-slot:label>
                            <div>
                                <div class="font-weight-bold">Update past transactions?</div>
                                <div class="text-caption text-medium-emphasis" v-if="impact !== null">
                                    Will update approx. <strong>{{ impact }}</strong> transactions
                                </div>
                                <div class="text-caption text-medium-emphasis" v-else>
                                    Select to verify impact on history
                                </div>
                            </div>
                        </template>
                    </v-checkbox>

                    <div class="d-flex justify-end gap-3 pt-4">
                        <v-btn variant="text" @click="isOpen = false">Cancel</v-btn>
                        <v-btn type="submit" color="primary" :loading="loading">
                            Create Rule
                        </v-btn>
                    </div>
                </v-form>
            </v-card-text>
        </v-card>
    </v-dialog>
</template>
