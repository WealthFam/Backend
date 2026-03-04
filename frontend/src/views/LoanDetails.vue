<template>
    <MainLayout>
        <v-container fluid class="page-container dashboard-page">
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
                <v-row v-if="loading" class="py-8">
                    <v-col cols="12" md="3" v-for="i in 4" :key="`skel-stat-${i}`">
                        <PremiumSkeleton type="stat-card" glass />
                    </v-col>
                    <v-col cols="12" class="mt-4">
                        <PremiumSkeleton type="hero" height="300" glass />
                    </v-col>
                </v-row>

                <div v-else-if="loan">
                    <!-- Header -->
                    <div class="d-flex flex-column flex-md-row justify-space-between align-md-center mb-10 gap-6">
                        <div class="d-flex align-center gap-5">
                            <v-avatar size="80" variant="tonal" color="primary" rounded="xl"
                                class="elevation-4 shadow-primary d-flex align-center justify-center">
                                <span class="text-h3">{{ getLoanIcon(loan.loan_type) }}</span>
                            </v-avatar>
                            <div>
                                <h1 class="text-h4 font-weight-black text-content mb-2 letter-spacing-negative-1">{{
                                    loan.name }}</h1>
                                <div class="d-flex align-center gap-3 text-medium-emphasis font-weight-bold">
                                    <v-chip size="small" color="primary" variant="flat"
                                        class="font-weight-black text-uppercase shadow-sm">
                                        {{ loan.loan_type?.replace('_', ' ') || 'LOAN' }}
                                    </v-chip>
                                    <span class="d-flex align-center gap-1">
                                        <Calendar :size="14" /> {{ loan.tenure_months }} Months
                                    </span>
                                    <span>•</span>
                                    <span class="d-flex align-center gap-1">
                                        <TrendingUp :size="14" class="text-error" /> {{ loan.interest_rate }}% Interest
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div
                            class="text-md-right pa-5 bg-surface-variant bg-opacity-5 rounded-2xl border border-primary border-opacity-25 glass-panel hover-lift">
                            <div
                                class="text-caption font-weight-black text-primary text-uppercase letter-spacing-1 mb-1 d-flex align-center justify-md-end gap-2">
                                <Activity :size="14" /> Current Outstanding
                            </div>
                            <div class="text-h3 font-weight-black text-primary" style="font-feature-settings: 'tnum';">
                                {{
                                    formatCurrency(loan.outstanding_balance) }}</div>
                        </div>
                    </div>

                    <!-- Stats Cards -->
                    <v-row class="mb-10">
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-5 h-100 hover-lift d-flex flex-column justify-center"
                                rounded="xl" elevation="0">
                                <div class="d-flex align-center gap-4 mb-2">
                                    <v-avatar size="48" variant="tonal" color="primary" rounded="lg">
                                        <Landmark :size="24" />
                                    </v-avatar>
                                    <div
                                        class="text-caption font-weight-black text-medium-emphasis text-uppercase letter-spacing-1">
                                        Principal Amount</div>
                                </div>
                                <div class="text-h5 font-weight-black text-content">{{
                                    formatCurrency(loan.principal_amount) }}</div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-5 h-100 hover-lift d-flex flex-column justify-center"
                                rounded="xl" elevation="0">
                                <div class="d-flex align-center gap-4 mb-2">
                                    <v-avatar size="48" variant="tonal" color="error" rounded="lg">
                                        <Wallet :size="24" />
                                    </v-avatar>
                                    <div
                                        class="text-caption font-weight-black text-medium-emphasis text-uppercase letter-spacing-1">
                                        EMI
                                        Amount</div>
                                </div>
                                <div class="text-h5 font-weight-black text-content">{{ formatCurrency(loan.emi_amount)
                                }}</div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-5 h-100 hover-lift d-flex flex-column justify-center"
                                rounded="xl" elevation="0">
                                <div class="d-flex align-center gap-4 mb-2">
                                    <v-avatar size="48" variant="tonal" color="warning" rounded="lg">
                                        <CalendarClock :size="24" />
                                    </v-avatar>
                                    <div
                                        class="text-caption font-weight-black text-medium-emphasis text-uppercase letter-spacing-1">
                                        Next Due Date</div>
                                </div>
                                <div class="text-h5 font-weight-black text-content">{{ formatDate(loan.next_emi_date)
                                }}</div>
                            </v-card>
                        </v-col>
                        <v-col cols="6" md="3">
                            <v-card class="premium-glass-card pa-5 h-100 hover-lift d-flex flex-column justify-center"
                                rounded="xl" elevation="0">
                                <div class="d-flex justify-space-between align-center mb-3">
                                    <div class="d-flex align-center gap-4">
                                        <v-avatar size="48" variant="tonal" color="success" rounded="lg">
                                            <Target :size="24" />
                                        </v-avatar>
                                        <span
                                            class="text-caption font-weight-black text-medium-emphasis text-uppercase letter-spacing-1">Progress</span>
                                    </div>
                                    <v-chip size="x-small" color="primary" variant="tonal"
                                        class="font-weight-black px-2">{{
                                            loan.progress_percentage }}%</v-chip>
                                </div>
                                <v-progress-linear :model-value="loan.progress_percentage" color="primary" rounded
                                    height="10" class="loan-progress-premium shadow-sm"></v-progress-linear>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- AI Insights Section -->
                    <v-card class="premium-glass-card mb-10 overflow-hidden insights-glow" elevation="0">
                        <div
                            class="pa-6 d-flex flex-column flex-md-row justify-space-between align-md-center gap-4 insights-header-bg">
                            <div class="d-flex align-center gap-4">
                                <div class="primary-glow-box shadow-primary">
                                    <Sparkles :size="24" class="text-primary" />
                                </div>
                                <div>
                                    <h3 class="text-h5 font-weight-black text-content letter-spacing-negative-1 mb-1">AI
                                        Loan Advisor</h3>
                                    <p
                                        class="text-caption font-weight-bold text-medium-emphasis letter-spacing-1 text-uppercase">
                                        Get personalized prepayment and saving strategies</p>
                                </div>
                            </div>
                            <v-btn color="primary" variant="flat" rounded="pill"
                                class="font-weight-black px-6 shadow-primary hover-lift" @click="generateInsights"
                                :loading="insightLoading" height="48">
                                {{ insights ? 'Refresh Analysis' : 'Generate Insights' }}
                            </v-btn>
                        </div>
                        <div v-if="insights" class="pa-8 pt-6">
                            <div class="markdown-body premium-markdown" v-html="renderedInsights"></div>
                        </div>
                    </v-card>

                    <!-- Amortization Chart Section -->
                    <v-row class="mb-4">
                        <v-col cols="12">
                            <v-card class="premium-glass-card pa-6" elevation="0">
                                <h3 class="text-h6 font-weight-black text-content mb-2">Monthly Amortization Breakdown
                                </h3>
                                <p class="text-caption font-weight-bold text-medium-emphasis mb-6">
                                    Projected Interest vs. Principal payments over time
                                </p>
                                <div style="height: 350px; position: relative;">
                                    <Bar v-if="amortizationChartData" :data="amortizationChartData as any"
                                        :options="amortizationChartOptions as any" />
                                </div>
                            </v-card>
                        </v-col>
                    </v-row>

                    <!-- Content Split -->
                    <v-row>
                        <!-- Chart Section -->
                        <v-col cols="12" lg="4">
                            <v-card class="premium-glass-card pa-6 h-100 d-flex flex-column hover-lift" elevation="0">
                                <h3 class="text-h6 font-weight-black text-content mb-6 letter-spacing-negative-1">
                                    Principal vs Interest</h3>
                                <div class="flex-grow-1 d-flex flex-column justify-center"
                                    style="min-height: 250px; position: relative;">
                                    <Pie v-if="chartData" :data="chartData as any" :options="chartOptions as any" />
                                </div>
                                <div
                                    class="mt-8 text-center pa-5 bg-surface-variant bg-opacity-5 rounded-xl border border-primary border-opacity-25 glass-panel">
                                    <div
                                        class="text-caption font-weight-black text-medium-emphasis text-uppercase letter-spacing-1 mb-2">
                                        Total Interest Payable</div>
                                    <div class="text-h4 font-weight-black text-error"
                                        style="font-feature-settings: 'tnum';">{{ formatCurrency(totalInterest) }}</div>
                                </div>
                            </v-card>
                        </v-col>

                        <!-- Amortization Schedule -->
                        <v-col cols="12" lg="8">
                            <v-card class="premium-glass-card h-100 d-flex flex-column overflow-hidden hover-lift"
                                elevation="0">
                                <div
                                    class="pa-6 pb-4 border-b border-opacity-10 d-flex justify-space-between align-center">
                                    <h3 class="text-h6 font-weight-black text-content letter-spacing-negative-1">
                                        Amortization Schedule</h3>
                                    <v-chip size="small" variant="tonal" color="primary" class="font-weight-black">{{
                                        loan.amortization_schedule?.length || 0 }} Installments</v-chip>
                                </div>
                                <div class="flex-grow-1 overflow-auto" style="max-height: 500px;">
                                    <v-table class="bg-transparent premium-table">
                                        <thead>
                                            <tr>
                                                <th
                                                    class="text-left font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    #</th>
                                                <th
                                                    class="text-left font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    DATE</th>
                                                <th
                                                    class="text-right font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    EMI</th>
                                                <th
                                                    class="text-right font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    PRINCIPAL</th>
                                                <th
                                                    class="text-right font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    INTEREST</th>
                                                <th
                                                    class="text-right font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    BALANCE</th>
                                                <th
                                                    class="text-center font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    STATUS</th>
                                                <th
                                                    class="text-center font-weight-black text-caption text-medium-emphasis letter-spacing-1 py-4">
                                                    ACTION</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="item in loan.amortization_schedule" :key="item.installment_no"
                                                class="hover-row transition-fast">
                                                <td class="font-weight-bold text-caption opacity-70">{{
                                                    item.installment_no }}</td>
                                                <td class="font-weight-bold text-caption">{{ formatDate(item.due_date)
                                                    }}</td>
                                                <td class="text-right font-weight-black text-body-2"
                                                    style="font-feature-settings: 'tnum';">{{ formatCurrency(item.emi)
                                                    }}</td>
                                                <td class="text-right font-weight-bold text-caption text-primary"
                                                    style="font-feature-settings: 'tnum';">{{
                                                        formatCurrency(item.principal_component) }}</td>
                                                <td class="text-right font-weight-bold text-caption text-error"
                                                    style="font-feature-settings: 'tnum';">{{
                                                        formatCurrency(item.interest_component) }}</td>
                                                <td class="text-right font-weight-black text-caption text-medium-emphasis"
                                                    style="font-feature-settings: 'tnum';">{{
                                                        formatCurrency(item.closing_balance) }}</td>
                                                <td class="text-center">
                                                    <v-chip size="x-small" :color="getStatusColor(item.status)"
                                                        variant="flat"
                                                        class="font-weight-black text-uppercase shadow-sm">
                                                        {{ item.status }}
                                                    </v-chip>
                                                </td>
                                                <td class="text-center">
                                                    <v-btn v-if="item.status !== 'PAID'" size="small" color="primary"
                                                        variant="tonal" rounded="pill"
                                                        class="font-weight-bold px-4 hover-lift" height="28"
                                                        @click="openRepaymentModal(item)">
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
                                    density="comfortable" hide-details rounded="lg" bg-color="surface" class="mb-4">
                                    <template v-slot:append-inner>
                                        <ChevronDown :size="16" class="text-primary opacity-70" />
                                    </template>
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
import { todayLocalString } from '@/utils/time'
import MainLayout from '@/layouts/MainLayout.vue'
import { financeApi as api } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { useCurrency } from '@/composables/useCurrency'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement } from 'chart.js'
import { Pie, Bar } from 'vue-chartjs'
import { marked } from 'marked'
import PremiumSkeleton from '@/components/common/PremiumSkeleton.vue'
import { ChevronLeft, Sparkles, X, ChevronDown, TrendingUp, Calendar, Activity, Landmark, Wallet, CalendarClock, Target } from 'lucide-vue-next'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement)

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
    date: todayLocalString(),
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

// --- Monthly Amortization Chart Logic ---
const amortizationChartData = computed(() => {
    if (!loan.value || !loan.value.amortization_schedule) return null;

    const monthlyData: Record<string, { principal: number, interest: number }> = {};
    const labelOrder: string[] = [];

    loan.value.amortization_schedule.forEach((item: any) => {
        const date = new Date(item.due_date);
        const monthYear = date.toLocaleDateString('en-US', { month: 'short', year: '2-digit' });

        if (!monthlyData[monthYear]) {
            monthlyData[monthYear] = { principal: 0, interest: 0 };
            labelOrder.push(monthYear);
        }
        monthlyData[monthYear].principal += Number(item.principal_component);
        monthlyData[monthYear].interest += Number(item.interest_component);
    });

    const principalData = labelOrder.map(label => Math.round(monthlyData[label].principal));
    const interestData = labelOrder.map(label => Math.round(monthlyData[label].interest));

    return {
        labels: labelOrder,
        datasets: [
            {
                label: 'Principal',
                backgroundColor: '#3B82F6', // Primary Blue
                data: principalData,
                stack: 'Stack 0',
                borderRadius: 4
            },
            {
                label: 'Interest',
                backgroundColor: '#EF4444', // Red
                data: interestData,
                stack: 'Stack 0',
                borderRadius: 4
            }
        ]
    };
});

const amortizationChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
        intersect: false,
        mode: 'index',
    },
    scales: {
        x: {
            stacked: true,
            grid: { display: false }
        },
        y: {
            stacked: true,
            border: { display: false },
            grid: { color: 'rgba(128, 128, 128, 0.1)' }
        }
    },
    plugins: {
        legend: {
            position: 'top' as const,
            labels: {
                usePointStyle: true,
                padding: 20,
                font: {
                    family: 'Inter',
                    size: 11,
                    weight: 'bold'
                }
            }
        },
        tooltip: {
            callbacks: {
                label: function (context: any) {
                    let label = context.dataset.label || '';
                    if (label) {
                        label += ': ';
                    }
                    if (context.parsed.y !== null) {
                        label += new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(context.parsed.y);
                    }
                    return label;
                }
            }
        }
    }
}

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
.shadow-primary {
    box-shadow: 0 10px 25px -5px rgba(var(--v-theme-primary), 0.4) !important;
}

.shadow-sm {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1) !important;
}

.letter-spacing-1 {
    letter-spacing: 0.05em;
}

.letter-spacing-negative-1 {
    letter-spacing: -0.02em;
}

.icon-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    flex-shrink: 0;
}

.hover-lift {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.hover-lift:hover {
    transform: translateY(-4px);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04) !important;
}

.loan-progress-premium :deep(.v-progress-linear__determinate) {
    background: linear-gradient(90deg, #3b82f6 0%, #60a5fa 100%) !important;
    box-shadow: 0 0 10px rgba(59, 130, 246, 0.4);
}

.loan-progress-premium :deep(.v-progress-linear__background) {
    opacity: 0.15 !important;
}

.glass-panel {
    background: rgba(var(--v-theme-surface), 0.6) !important;
    backdrop-filter: blur(20px) saturate(180%);
}

.insights-glow {
    border: 1px solid rgba(var(--v-theme-primary), 0.3) !important;
    box-shadow: 0 0 40px rgba(var(--v-theme-primary), 0.05) !important;
}

.insights-header-bg {
    background: linear-gradient(90deg, rgba(var(--v-theme-primary), 0.08) 0%, rgba(var(--v-theme-primary), 0.02) 100%);
    border-bottom: 1px solid rgba(var(--v-theme-primary), 0.1);
}

.premium-table th {
    background: rgba(var(--v-theme-surface), 0.8) !important;
    backdrop-filter: blur(10px);
    position: sticky;
    top: 0;
    z-index: 2;
    border-bottom: 2px solid rgba(var(--v-border-color), 0.1) !important;
}

.premium-table td {
    border-bottom: 1px solid rgba(var(--v-border-color), 0.05) !important;
}

.transition-fast {
    transition: all 0.2s ease;
}

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
