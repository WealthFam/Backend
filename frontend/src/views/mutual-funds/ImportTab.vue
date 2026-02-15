<template>
    <v-container fluid class="fill-height justify-center align-center relative-pos overflow-hidden py-12">
        <!-- Background Mesh Blobs -->
        <div class="mesh-blob blob-1"
            style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
        </div>
        <div class="mesh-blob blob-2"
            style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
        </div>

        <v-card class="premium-glass-card pa-8 relative-pos z-10" rounded="xl" max-width="800" width="100%">
            <!-- Header -->
            <div class="text-center mb-8">
                <div class="d-flex justify-center mb-4">
                    <div class="icon-glow-box">
                        <Upload :size="32" class="text-primary" />
                    </div>
                </div>
                <h2 class="text-h4 font-weight-black mb-2 text-content">Wealth Import</h2>
                <p class="text-subtitle-1 text-medium-emphasis">Consolidate your mutual fund portfolio in one click</p>
            </div>

            <!-- Import Mode Toggles -->
            <div class="d-flex flex-wrap gap-4 mb-8 justify-center">
                <v-btn v-for="mode in importModes" :key="mode" :variant="importMode === mode ? 'flat' : 'tonal'"
                    :color="importMode === mode ? 'primary' : 'primary-lighten-4'" rounded="pill"
                    class="px-8 font-weight-black" @click="importMode = mode">
                    <component :is="mode === 'pdf' ? FileText : Lock" :size="18" class="mr-2" />
                    {{ mode === 'pdf' ? 'Upload PDF' : 'Scan Email' }}
                </v-btn>
            </div>

            <v-divider class="mb-8 opacity-10" />

            <v-row>
                <!-- Selection Column -->
                <v-col cols="12" md="6">
                    <label class="text-overline font-weight-black text-primary mb-2 d-block letter-spacing-2">FAMILY
                        MEMBER</label>
                    <v-select v-model="selectedMemberId" :items="memberOptions" item-title="title" item-value="value"
                        variant="outlined" density="comfortable" rounded="lg" bg-color="surface"
                        class="mb-6 font-weight-bold" placeholder="Import for whom?">
                        <template v-slot:item="{ props, item }">
                            <v-list-item v-bind="props" class="rounded-lg ma-1">
                                <template v-slot:prepend>
                                    <v-avatar size="28" color="primary" variant="tonal" class="mr-2">
                                        <span class="text-caption font-weight-black">{{ item.raw.initials }}</span>
                                    </v-avatar>
                                </template>
                            </v-list-item>
                        </template>
                    </v-select>

                    <label
                        class="text-overline font-weight-black text-primary mb-2 d-block letter-spacing-2">IDENTIFICATION
                        (PAN)</label>
                    <v-text-field v-model="panNumber" placeholder="ABCDE1234F" variant="outlined" density="comfortable"
                        rounded="lg" bg-color="surface" class="mb-2 font-weight-black" persistent-hint
                        hint="Auto-populated from member profile for password-protected statements.">
                    </v-text-field>
                </v-col>

                <!-- Action Column -->
                <v-col cols="12" md="6">
                    <template v-if="importMode === 'pdf'">
                        <label class="text-overline font-weight-black text-primary mb-2 d-block letter-spacing-2">CAS
                            STATEMENT PDF</label>
                        <v-file-input v-model="file" label="Drop CAS PDF here" variant="outlined" density="comfortable"
                            rounded="lg" bg-color="surface" accept=".pdf" class="mb-4 font-weight-bold" prepend-icon="">
                            <template v-slot:prepend-inner>
                                <FileText :size="24" class="text-medium-emphasis mr-2" />
                            </template>
                        </v-file-input>

                        <v-btn color="primary" block height="56" rounded="lg" class="font-weight-black elevation-4"
                            :loading="isProcessing" :disabled="!file" @click="handlePreview">
                            Process PDF
                            <ArrowRight :size="18" class="ml-2" />
                        </v-btn>
                    </template>

                    <template v-else>
                        <label class="text-overline font-weight-black text-primary mb-2 d-block letter-spacing-2">SYNC
                            PERIOD</label>
                        <v-select v-model="emailSyncPeriod" :items="periodOptions" variant="outlined"
                            density="comfortable" rounded="lg" bg-color="surface" class="mb-4 font-weight-bold">
                        </v-select>
                        <v-btn color="primary" block height="56" rounded="lg" class="font-weight-black elevation-4"
                            :loading="isProcessing" @click="handlePreview">
                            Scan Mailbox
                            <Upload :size="18" class="ml-2" />
                        </v-btn>
                    </template>
                </v-col>
            </v-row>

            <!-- Preview/Success States (Keep concise) -->
            <div v-if="previewResults.length"
                class="mt-8 pa-4 rounded-xl border border-primary border-dashed bg-primary-lighten-5">
                <div class="d-flex justify-space-between align-center mb-4">
                    <h3 class="text-subtitle-1 font-weight-black d-flex align-center">
                        <CheckCircle :size="18" class="text-success mr-2" />
                        Detected {{ previewResults.length }} Transactions
                    </h3>
                    <v-btn color="success" variant="flat" rounded="pill" size="small" class="font-weight-black px-6"
                        @click="handleConfirm">
                        Confirm Import
                    </v-btn>
                </div>
                <div class="preview-scroll max-h-60 overflow-y-auto">
                    <v-table density="compact" class="bg-transparent">
                        <thead>
                            <tr>
                                <th class="text-left text-tiny font-weight-black opacity-50">ST</th>
                                <th class="text-left text-tiny font-weight-black opacity-50">DATE</th>
                                <th class="text-left text-tiny font-weight-black opacity-50">FUND</th>
                                <th class="text-right text-tiny font-weight-black opacity-50">AMOUNT</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="(t, i) in previewResults" :key="i">
                                <td>
                                    <component
                                        :is="t.mapping_status === 'MAPPED' ? (t.is_duplicate ? AlertTriangle : CheckCircle) : HelpCircle"
                                        :size="16"
                                        :class="t.mapping_status === 'MAPPED' ? (t.is_duplicate ? 'text-warning' : 'text-success') : 'text-error'">
                                    </component>
                                    <v-tooltip activator="parent" location="top">
                                        {{ t.mapping_status === 'MAPPED' ? (t.is_duplicate ? 'Already exists' :
                                            'Mapped successfully') : 'Unknown fund (MAPPING FAILED)' }}
                                    </v-tooltip>
                                </td>
                                <td class="text-caption font-weight-bold opacity-70 white-space-nowrap">{{ t.date }}
                                </td>
                                <td class="text-caption font-weight-black lh-tight py-1">
                                    <div class="d-flex align-center gap-1 flex-wrap">
                                        {{ t.scheme_name }}
                                        <v-chip v-if="t.is_duplicate" size="x-small" color="warning" variant="flat"
                                            class="text-tiny font-weight-black px-1" style="height: 16px;">
                                            DUPLICATE
                                        </v-chip>
                                        <v-chip v-if="t.is_synthesized" size="x-small" color="info" variant="tonal"
                                            class="text-tiny font-weight-black px-1" style="height: 16px;">
                                            BALANCE
                                        </v-chip>
                                    </div>
                                    <div v-if="t.mapped_name && t.mapped_name !== t.scheme_name"
                                        class="text-tiny text-primary opacity-70">
                                        → {{ t.mapped_name }}
                                    </div>
                                    <div v-if="t.mapping_status === 'UNMAPPED'" class="text-tiny text-error">
                                        No match found in master list
                                    </div>
                                </td>
                                <td class="text-right text-caption font-weight-black">₹{{ t.amount }}</td>
                            </tr>
                        </tbody>
                    </v-table>
                </div>
            </div>

            <div v-if="uploadStatus === 'success'"
                class="mt-8 pa-4 rounded-xl bg-success-light text-center border border-success border-opacity-20 animate-in-up">
                <CheckCircle :size="40" class="text-success mb-2" />
                <h3 class="text-h6 font-weight-black text-success">{{ uploadMessage }}</h3>
                <v-btn to="/mutual-funds" variant="tonal" color="success" class="mt-4 font-weight-black"
                    rounded="pill">Back to
                    Portfolio</v-btn>
            </div>
        </v-card>
    </v-container>
</template>
<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Upload, FileText, Lock, CheckCircle, ArrowRight, AlertTriangle, HelpCircle } from 'lucide-vue-next'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useAuthStore } from '@/stores/auth'

const notify = useNotificationStore()
const authStore = useAuthStore()

const importMode = ref<'pdf' | 'email'>('pdf')
const importModes = ['pdf', 'email'] as const
const selectedMemberId = ref<string | null>(authStore.selectedMemberId)
const panNumber = ref('')
const file = ref<File | null>(null)
const emailSyncPeriod = ref('all')
const isProcessing = ref(false)
const previewResults = ref<any[]>([])
const uploadStatus = ref<'idle' | 'success' | 'error'>('idle')
const uploadMessage = ref('')

const periodOptions = [
    { title: 'Last 3 Months', value: '3m' },
    { title: 'Last 6 Months', value: '6m' },
    { title: 'Last 1 Year', value: '1y' },
    { title: 'All Time', value: 'all' }
]

const memberOptions = computed(() => {
    return authStore.familyMembers.map(m => ({
        title: m.full_name || m.email,
        value: m.id,
        initials: (m.full_name || m.email).substring(0, 2).toUpperCase(),
        pan: m.pan_number
    }))
})

// Auto-populate PAN when member changes
watch(selectedMemberId, (newId) => {
    if (!newId) return
    const member = authStore.familyMembers.find(m => m.id === newId)
    if (member && member.pan_number) {
        panNumber.value = member.pan_number
    }
}, { immediate: true })

async function handlePreview() {
    isProcessing.value = true
    uploadStatus.value = 'idle'
    previewResults.value = []

    try {
        let res
        if (importMode.value === 'pdf') {
            if (!file.value) return
            const formData = new FormData()
            formData.append('file', file.value)
            formData.append('password', panNumber.value)
            res = await financeApi.previewCAS(formData)
        } else {
            const formData = new FormData()
            formData.append('password', panNumber.value)
            formData.append('period', emailSyncPeriod.value)
            res = await financeApi.previewCASEmail(formData)
        }

        previewResults.value = res.data.transactions || []
        if (previewResults.value.length === 0) {
            notify.info("No new transactions found to import.")
        }
    } catch (err: any) {
        uploadStatus.value = 'error'
        uploadMessage.value = err.response?.data?.detail || 'Process failed. Please verify statement password.'
        notify.error('Preview failed')
    } finally {
        isProcessing.value = false
    }
}

async function handleConfirm() {
    isProcessing.value = true
    try {
        await financeApi.confirmImport(previewResults.value, selectedMemberId.value || undefined)
        uploadStatus.value = 'success'
        uploadMessage.value = `Successfully imported ${previewResults.value.length} transactions!`
        previewResults.value = []
        notify.success('Import complete')
    } catch (err: any) {
        notify.error('Confirmation failed')
    } finally {
        isProcessing.value = false
    }
}
</script>

<style scoped>
.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(var(--v-border-color), 0.15) !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.05) !important;
}

.mesh-blob {
    position: absolute;
    filter: blur(80px);
    opacity: 0.15;
    border-radius: 50%;
}

.relative-pos {
    position: relative;
}

.z-10 {
    z-index: 10;
}

.icon-glow-box {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: rgba(var(--v-theme-primary), 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 40px rgba(var(--v-theme-primary), 0.2);
    border: 1px solid rgba(var(--v-theme-primary), 0.2);
}

.white-space-nowrap {
    white-space: nowrap;
}

.lh-tight {
    line-height: 1.2;
}

.text-tiny {
    font-size: 0.7rem;
}

.letter-spacing-2 {
    letter-spacing: 2px !important;
}

.bg-success-light {
    background: rgba(var(--v-theme-success), 0.1);
}

.bg-error-light {
    background: rgba(var(--v-theme-error), 0.1);
}

.preview-scroll::-webkit-scrollbar {
    width: 4px;
}

.preview-scroll::-webkit-scrollbar-thumb {
    background: rgba(var(--v-theme-primary), 0.2);
    border-radius: 10px;
}

.animate-in-up {
    animation: fadeInUp 0.4s ease-out forwards;
}

@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }

    to {
        opacity: 1;
        transform: translateY(0);
    }
}
</style>
