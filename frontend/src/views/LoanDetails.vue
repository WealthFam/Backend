<template>
    <MainLayout>
        <v-container fluid class="dashboard-page pa-6 pa-md-10 relative-pos overflow-hidden">
            <!-- Animated Mesh Background -->
            <div class="mesh-blob blob-1"
                style="background: rgba(var(--v-theme-primary), 0.1); width: 600px; height: 600px; top: -200px; right: -100px;">
            </div>
            <div class="mesh-blob blob-2"
                style="background: rgba(var(--v-theme-secondary), 0.05); width: 400px; height: 400px; bottom: -100px; left: -100px;">
            </div>

            <div class="relative-pos z-10">
                <div class="mb-6">
                    <v-btn variant="text" color="primary" class="pl-0 font-weight-bold" @click="router.back()">
                        <ChevronLeft :size="20" class="mr-1" />
                        Back to Loans
                    </v-btn>
                </div>

                <!-- Loading State -->
                <div v-if="loading" class="d-flex justify-center align-center py-16">
                    <v-progress-circular indeterminate color="primary" size="64" width="6" />
                </div>

                <div v-else-if="loan">
                    <!-- Header -->
                    <div class="d-flex flex-column flex-md-row justify-space-between align-md-start mb-8 gap-4">
                        <div class="d-flex align-top gap-4">
                            <v-avatar size="64" variant="tonal" color="primary" rounded="xl" class="elevation-4">
                                <span class="text-h4">{{ getLoanIcon(loan.loan_type) }}</span>
                            </v-avatar>
                            <div>
                                <h1 class="text-h4 font-weight-black text-content mb-1">{{ loan.name }}</h1>
                                <div class="d-flex align-center gap-3 text-medium-emphasis font-weight-bold">
                                    <v-chip size="small" variant="outlined" class="font-weight-bold text-uppercase">
                                        {{ loan.loan_type?.replace('_', ' ') || 'LOAN' }}
                                    </v-chip>
                                    <span>{{ loan.tenure_months }} Months</span>
                                    <span>•</span>
                                    <span>{{ loan.interest_rate }}% Interest</span>
                                </div>
                            </div>
                        </div>
                        <div class="text-md-right p-4 bg-surface-variant bg-opacity-5 rounded-xl border border-dashed">
                            <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Current
                                Outstanding</div>
                            <div class="text-h4 font-weight-black text-primary">{{
                                formatCurrency(loan.outstanding_balance) }}</div>
                        </div>
                    </div>

                    <!-- Stats Cards -->
                    <v-row class="mb-8">
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-4 h-100" elevation="0">
                                <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">
                                    Principal Amount</div>
                                <div class="text-h6 font-weight-black text-content">{{
                                    formatCurrency(loan.principal_amount) }}</div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-4 h-100" elevation="0">
                                <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">EMI
                                    Amount</div>
                                <div class="text-h6 font-weight-black text-content">{{ formatCurrency(loan.emi_amount)
                                }}</div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-4 h-100" elevation="0">
                                <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase mb-1">Next
                                    Due Date</div>
                                <div class="text-h6 font-weight-black text-content">{{ formatDate(loan.next_emi_date) }}
                                </div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-4 h-100 d-flex flex-column justify-center"
                                elevation="0">
                                <div class="d-flex justify-space-between text-caption font-weight-bold mb-1">
                                    <span class="text-medium-emphasis text-uppercase">Progress</span>
                                    <span class="text-primary">{{ loan.progress_percentage }}%</span>
                                </div>
                                <v-progress-linear :model-value="loan.progress_percentage" color="primary" rounded
                                    height="8"></v-progress-linear>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- AI Insights Section -->
                    <v-card class="premium-glass-card mb-8 overflow-hidden" elevation="0"
                        style="border-color: rgba(var(--v-theme-primary), 0.2) !important;">
                        <div
                            class="pa-6 d-flex flex-column flex-md-row justify-space-between align-md-center gap-4 bg-primary bg-opacity-5">
                            <div class="d-flex align-center gap-3">
                                <div class="primary-glow-box">
                                    <Sparkles :size="24" class="text-primary" />
                                </div>
                                <div>
                                    <h3 class="text-h6 font-weight-black text-content">AI Loan Advisor</h3>
                                    <p class="text-caption font-weight-bold text-medium-emphasis">Get personalized
                                        prepayment and saving strategies</p>
                                </div>
                            </div>
                            <v-btn color="primary" variant="flat" rounded="pill" class="font-weight-bold"
                                @click="generateInsights" :loading="insightLoading">
                                {{ insights ? 'Refresh Analysis' : 'Generate Insights' }}
                            </v-btn>
                        </div>
                        <div v-if="insights" class="pa-6 pt-2">
                            <div class="markdown-body premium-markdown" v-html="renderedInsights"></div>
                        </div>
                    </v-card>

                    <!-- Content Split -->
                    <v-row>
                        <!-- Chart Section -->
                        <v-col cols="12" lg="4">
                            <v-card class="premium-glass-card pa-6 h-100" elevation="0">
                                <h3 class="text-h6 font-weight-black text-content mb-6">Principal vs Interest</h3>
                                <div style="height: 300px; position: relative;">
                                    <Pie v-if="chartData" :data="chartData as any" :options="chartOptions as any" />
                                </div>
                                <div
                                    class="mt-6 text-center pa-4 bg-surface-variant bg-opacity-5 rounded-lg border border-dashed">
                                    <div class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Total
                                        Interest Payable</div>
                                    <div class="text-h5 font-weight-black text-error">{{ formatCurrency(totalInterest)
                                    }}</div>
                                </div>
                            </v-card>
                        </v-col>

                        <!-- Amortization Schedule -->
                        <v-col cols="12" lg="8">
                            <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden" elevation="0">
                                <div class="pa-6 pb-2">
                                    <h3 class="text-h6 font-weight-black text-content">Amortization Schedule</h3>
                                </div>
                                <div class="flex-grow-1 overflow-auto" style="max-height: 500px;">
                                    <v-table class="bg-transparent">
                                        <thead>
                                            <tr>
                                                <th
                                                    class="text-left font-weight-bold text-caption text-medium-emphasis">
                                                    #</th>
                                                <th
                                                    class="text-left font-weight-bold text-caption text-medium-emphasis">
                                                    DATE</th>
                                                <th
                                                    class="text-right font-weight-bold text-caption text-medium-emphasis">
                                                    EMI</th>
                                                <th
                                                    class="text-right font-weight-bold text-caption text-medium-emphasis">
                                                    PRINCIPAL</th>
                                                <th
                                                    class="text-right font-weight-bold text-caption text-medium-emphasis">
                                                    INTEREST</th>
                                                <th
                                                    class="text-right font-weight-bold text-caption text-medium-emphasis">
                                                    BALANCE</th>
                                                <th
                                                    class="text-center font-weight-bold text-caption text-medium-emphasis">
                                                    STATUS</th>
                                                <th
                                                    class="text-center font-weight-bold text-caption text-medium-emphasis">
                                                    ACTION</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="item in loan.amortization_schedule" :key="item.installment_no"
                                                class="hover-row">
                                                <td class="font-weight-bold text-caption">{{ item.installment_no }}</td>
                                                <td class="font-weight-bold text-caption">{{ formatDate(item.due_date)
                                                }}</td>
                                                <td class="text-right font-weight-black text-body-2">{{
                                                    formatCurrency(item.emi) }}</td>
                                                <td class="text-right font-weight-bold text-caption text-success">{{
                                                    formatCurrency(item.principal_component) }}</td>
                                                <td class="text-right font-weight-bold text-caption text-error">{{
                                                    formatCurrency(item.interest_component) }}</td>
                                                <td
                                                    class="text-right font-weight-bold text-caption text-medium-emphasis">
                                                    {{ formatCurrency(item.closing_balance) }}</td>
                                                <td class="text-center">
                                                    <v-chip size="x-small" :color="getStatusColor(item.status)"
                                                        variant="flat" class="font-weight-bold">
                                                        {{ item.status }}
                                                    </v-chip>
                                                </td>
                                                <td class="text-center">
                                                    <v-btn v-if="item.status !== 'PAID'" size="small" color="primary"
                                                        variant="tonal" rounded="pill" class="font-weight-bold px-4"
                                                        height="24" @click="openRepaymentModal(item)">
                                                        Pay
                                                    </v-btn>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </v-table>
                                </div>
                            </v-card>
                        </v-col>
                    </v-row>
                </div>

                <!-- Repayment Modal -->
                <v-dialog v-model="showRepaymentModal" max-width="500">
                    <v-card rounded="xl" class="premium-glass-modal elevation-24">
                        <div class="px-6 pt-6 pb-2 d-flex justify-space-between align-center">
                            <div>
                                <div class="text-overline font-weight-black text-primary mb-1 letter-spacing-2">RECORD
                                    PAYMENT</div>
                                <h2 class="text-h5 font-weight-black text-content">EMI #{{ repaymentForm.installment_no
                                }}</h2>
                            </div>
                            <v-btn icon variant="text" @click="showRepaymentModal = false" density="comfortable"
                                class="bg-surface-variant bg-opacity-10 opacity-70 hover:opacity-100">
                                <X :size="20" />
                            </v-btn>
                        </div>

                        <v-card-text class="px-6 py-4">
                            <v-form @submit.prevent="submitRepayment">
                                <v-text-field v-model.number="repaymentForm.amount" label="Amount" type="number"
                                    prefix="₹" variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" class="mb-4 font-weight-black text-h6">
                                </v-text-field>

                                <v-text-field v-model="repaymentForm.date" label="Payment Date" type="date"
                                    variant="outlined" density="comfortable" hide-details rounded="lg"
                                    bg-color="surface" class="mb-4">
                                </v-text-field>

                                <v-select v-model="repaymentForm.bank_account_id" :items="accountOptions"
                                    item-title="label" item-value="value" label="Paid From" variant="outlined"
                                    density="comfortable" hide-details rounded="lg" bg-color="surface" class="mb-4"
                                    append-inner-icon="mdi-chevron-down">
                                </v-select>

                                <v-text-field v-model="repaymentForm.description" label="Notes (Optional)"
                                    placeholder="e.g. Paid via UPI" variant="outlined" density="comfortable"
                                    hide-details rounded="lg" bg-color="surface">
                                </v-text-field>
                            </v-form>
                        </v-card-text>

                        <v-card-actions class="px-6 pb-6 pt-2">
                            <v-btn variant="text" @click="showRepaymentModal = false" height="48" rounded="lg"
                                class="px-6 font-weight-bold text-none text-medium-emphasis">
                                Cancel
                            </v-btn>
                            <v-spacer />
                            <v-btn color="primary" variant="flat" rounded="lg" height="48"
                                class="px-8 font-weight-black text-none elevation-4" @click="submitRepayment"
                                :loading="isSubmitting">
                                Record Payment
                            </v-btn>
                        </v-card-actions>
                    </v-card>
                </v-dialog>
            </div>
        </v-container>
    </MainLayout>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi as api } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useCurrency } from '@/composables/useCurrency'
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js'
import { Pie } from 'vue-chartjs'
import { marked } from 'marked'
import { ChevronLeft, Sparkles, X } from 'lucide-vue-next'

ChartJS.register(ArcElement, Tooltip, Legend)

const route = useRoute()
const router = useRouter()
const notificationStore = useNotificationStore()
const { formatAmount } = useCurrency()
const loading = ref(true)
const loan = ref<any>(null)
const accounts = ref<any[]>([])
const insightLoading = ref(false)
const insights = ref<string | null>(null)
const isSubmitting = ref(false)

const showRepaymentModal = ref(false)
const repaymentForm = ref({
    amount: 0,
    date: new Date().toISOString().split('T')[0],
    bank_account_id: '',
    installment_no: null as number | null,
    description: ''
})

const loanTypeOptions = [
    { label: 'Home Loan', value: 'HOME_LOAN', icon: '🏠' },
    { label: 'Personal Loan', value: 'PERSONAL_LOAN', icon: '👤' },
    { label: 'Car Loan', value: 'CAR_LOAN', icon: '🚗' },
    { label: 'Education Loan', value: 'EDUCATION_LOAN', icon: '🎓' },
    { label: 'Credit Card', value: 'CREDIT_CARD', icon: '💳' },
    { label: 'Other', value: 'OTHER', icon: '💰' }
]

const getLoanIcon = (type: string) => {
    const opt = loanTypeOptions.find(o => o.value === type)
    return opt ? opt.icon : '💰'
}

const accountOptions = computed(() => {
    return accounts.value
        .filter(a => a.type === 'BANK' || a.type === 'WALLET')
        .map(a => ({ label: a.name, value: a.id }))
})

const openRepaymentModal = (item: any) => {
    repaymentForm.value = {
        amount: item.emi,
        date: item.due_date.split('T')[0],
        bank_account_id: loan.value.bank_account_id || '',
        installment_no: item.installment_no,
        description: `EMI #${item.installment_no} for ${loan.value.name}`
    }
    showRepaymentModal.value = true
}

const submitRepayment = async () => {
    if (!repaymentForm.value.bank_account_id) {
        notificationStore.error("Please select a bank account")
        return
    }

    isSubmitting.value = true
    try {
        const id = route.params.id as string
        await api.recordLoanRepayment(id, repaymentForm.value)
        notificationStore.success("Repayment recorded successfully")
        showRepaymentModal.value = false
        fetchLoanDetails()
    } catch (e) {
        console.error("Failed to record repayment", e)
        notificationStore.error("Failed to record repayment")
    } finally {
        isSubmitting.value = false
    }
}

const renderedInsights = computed(() => {
    return insights.value ? marked(insights.value) : ''
})

const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric'
    })
}

const formatCurrency = (amount: any) => formatAmount(amount)

const totalInterest = computed(() => {
    if (!loan.value || !loan.value.amortization_schedule) return 0
    return loan.value.amortization_schedule.reduce((sum: number, item: any) => sum + Number(item.interest_component), 0)
})

const chartData = computed(() => {
    if (!loan.value) return null
    return {
        labels: ['Principal', 'Total Interest'],
        datasets: [
            {
                backgroundColor: ['#3B82F6', '#EF4444'],
                data: [Number(loan.value.principal_amount), totalInterest.value]
            }
        ]
    }
})

const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            position: 'bottom' as const,
            labels: {
                usePointStyle: true,
                padding: 20,
                font: {
                    family: 'Inter',
                    size: 11,
                    weight: 'bold'
                }
            }
        }
    }
}

const getStatusColor = (status: string) => {
    switch (status) {
        case 'PAID': return 'success'
        case 'OVERDUE': return 'error'
        case 'PENDING': return 'warning'
        default: return 'medium-emphasis'
    }
}

const fetchLoanDetails = async () => {
    loading.value = true
    try {
        const [loanRes, accRes] = await Promise.all([
            api.getLoanDetails(route.params.id as string),
            api.getAccounts()
        ])
        loan.value = loanRes.data
        accounts.value = accRes.data
    } catch (e) {
        console.error("Failed to fetch loan details", e)
        notificationStore.error("Failed to load loan details")
    } finally {
        loading.value = false
    }
}

const generateInsights = async () => {
    insightLoading.value = true
    try {
        const id = route.params.id as string
        const response = await api.getLoanInsights(id)
        insights.value = response.data.insights
        notificationStore.success("AI Insights generated!")
    } catch (e) {
        console.error("Failed to generate insights", e)
        notificationStore.error("Failed to generate AI insights. Please check if AI is enabled in settings.")
    } finally {
        insightLoading.value = false
    }
}

onMounted(() => {
    fetchLoanDetails()
})
</script>

<style scoped>
.dashboard-page {
    position: relative;
    min-height: calc(100vh - 64px);
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

.premium-glass-card {
    background: rgba(var(--v-theme-surface), 0.7) !important;
    backdrop-filter: blur(20px) saturate(180%);
    border: 1px solid rgba(128, 128, 128, 0.15) !important;
    box-shadow: none !important;
}

.premium-glass-card:not(.border-dashed) {
    border-color: rgba(var(--v-border-color), 0.15) !important;
}

.premium-glass-modal {
    background: rgba(var(--v-theme-surface), 0.95) !important;
    backdrop-filter: blur(24px) saturate(200%);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.primary-glow-box {
    width: 48px;
    height: 48px;
    background: rgba(var(--v-theme-primary), 0.1);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
}

.premium-markdown :deep(h1),
.premium-markdown :deep(h2),
.premium-markdown :deep(h3) {
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    font-weight: 800;
    line-height: 1.2;
}

.premium-markdown :deep(p) {
    margin-bottom: 1rem;
    line-height: 1.6;
    opacity: 0.9;
}

.premium-markdown :deep(ul) {
    padding-left: 1.5rem;
    margin-bottom: 1rem;
}

.hover-row:hover {
    background-color: rgba(var(--v-theme-surface-variant), 0.05);
}
</style>
