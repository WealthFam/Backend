<template>
    <div class="animate-in">
        <!-- Account Summary Widgets -->
        <v-row class="mb-6">
            <v-col cols="12" sm="6" md="3">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex justify-space-between align-center mb-2">
                        <span class="text-subtitle-2 text-medium-emphasis font-weight-bold text-uppercase ls-1">Total
                            Liquid</span>
                        <div class="stat-icon-bg gray">
                            <Scale :size="18" class="text-medium-emphasis" />
                        </div>
                    </div>
                    <div class="text-h4 font-weight-black">{{ formatAmount(accountMetrics.total) }}</div>
                </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex justify-space-between align-center mb-2">
                        <span class="text-subtitle-2 text-medium-emphasis font-weight-bold text-uppercase ls-1">Bank
                            Balance</span>
                        <div class="stat-icon-bg green">
                            <Landmark :size="18" class="text-success" />
                        </div>
                    </div>
                    <div class="text-h4 font-weight-black">{{ formatAmount(accountMetrics.bank) }}</div>
                </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex justify-space-between align-center mb-2">
                        <span class="text-subtitle-2 text-medium-emphasis font-weight-bold text-uppercase ls-1">Cash on
                            Hand</span>
                        <div class="stat-icon-bg yellow">
                            <Banknote :size="18" class="text-warning" />
                        </div>
                    </div>
                    <div class="text-h4 font-weight-black">{{ formatAmount(accountMetrics.cash) }}</div>
                </v-card>
            </v-col>
            <v-col cols="12" sm="6" md="3">
                <v-card class="premium-glass-card h-100 pa-4" elevation="0">
                    <div class="d-flex justify-space-between align-center mb-2">
                        <span class="text-subtitle-2 text-medium-emphasis font-weight-bold text-uppercase ls-1">Credit
                            Used</span>
                        <div class="stat-icon-bg red">
                            <CreditCard :size="18" class="text-error" />
                        </div>
                    </div>
                    <div class="text-h4 font-weight-black">{{ formatAmount(accountMetrics.credit) }}</div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Untrusted Accounts -->
        <div v-if="untrustedAccounts.length > 0" class="mb-8">
            <div class="d-flex align-center gap-3 mb-4">
                <h3 class="text-h6 font-weight-bold text-warning">⚠️ New Detected Accounts</h3>
                <v-chip color="warning" size="small" variant="flat" class="font-weight-bold">
                    {{ untrustedAccounts.length }} Action Needed
                </v-chip>
            </div>

            <v-row>
                <v-col v-for="acc in untrustedAccounts" :key="acc.id" cols="12" md="6" lg="4">
                    <v-card class="premium-glass-card untrusted-border" elevation="0">
                        <v-card-text>
                            <div class="d-flex justify-space-between align-start mb-4">
                                <div class="acc-icon-wrapper" :class="acc.type.toLowerCase()">
                                    <component :is="getAccountTypeIcon(acc.type)" :size="24" />
                                </div>
                                <div class="d-flex gap-2">
                                    <v-btn icon density="comfortable" variant="tonal" color="success"
                                        @click="openEditAccountModal(acc, true)" title="Verify Account">
                                        <Check :size="18" />
                                    </v-btn>
                                    <v-btn icon density="comfortable" variant="tonal" color="error"
                                        @click="deleteAccountRequest(acc)" title="Reject / Remove">
                                        <X :size="18" />
                                    </v-btn>
                                </div>
                            </div>

                            <div class="d-flex align-center gap-2 mb-1">
                                <span class="text-caption font-weight-bold text-uppercase text-medium-emphasis">{{
                                    getAccountTypeLabel(acc.type) }}</span>
                                <v-chip size="x-small" color="grey" variant="flat">Untrusted</v-chip>
                            </div>
                            <div class="text-h6 font-weight-bold mb-4 text-truncate">{{ acc.name }}</div>

                            <div class="d-flex justify-space-between align-end">
                                <div>
                                    <div class="text-caption font-weight-bold text-medium-emphasis">Balance</div>
                                    <div class="text-h6 font-weight-black">{{ formatAmount(acc.balance || 0) }}</div>
                                </div>
                            </div>
                        </v-card-text>
                    </v-card>
                </v-col>
            </v-row>
        </div>

        <!-- Verified Accounts Control Bar -->
        <div class="d-flex flex-column flex-sm-row align-center justify-space-between gap-4 mb-6">
            <v-text-field v-model="searchQuery" prepend-inner-icon="Search" placeholder="Search devices..."
                variant="outlined" density="comfortable" hide-details class="flex-grow-1"
                style="max-width: 400px; width: 100%;" bg-color="surface" rounded="lg"></v-text-field>

            <div class="d-flex align-center gap-3">
                <h3 class="text-subtitle-1 font-weight-bold">Tracked Accounts</h3>
                <v-chip color="success" size="small" variant="flat" class="font-weight-bold">
                    {{ verifiedAccounts.length }} Active
                </v-chip>
            </div>
        </div>

        <!-- Verified Accounts Grid -->
        <v-row>
            <v-col v-for="acc in verifiedAccounts" :key="acc.id" cols="12" md="6" lg="4">
                <v-card class="premium-glass-card account-card h-100" elevation="0"
                    :class="{ 'verified-highlight': acc.is_verified }" @click="openEditAccountModal(acc)">
                    <v-card-text class="h-100 d-flex flex-column">
                        <div class="d-flex justify-space-between align-start mb-4">
                            <div class="acc-icon-wrapper" :class="acc.type.toLowerCase()">
                                <component :is="getAccountTypeIcon(acc.type)" :size="20" />
                            </div>
                            <v-btn icon density="compact" variant="text" color="medium-emphasis">
                                <Edit2 :size="16" />
                            </v-btn>
                        </div>

                        <div class="mb-auto">
                            <div class="text-h6 font-weight-bold mb-1 line-clamp-1">{{ acc.name }}</div>
                            <div class="d-flex align-center gap-2 flex-wrap mb-2">
                                <span class="text-caption font-weight-bold text-uppercase text-medium-emphasis">{{
                                    getAccountTypeLabel(acc.type) }}</span>
                                <v-chip v-if="acc.account_mask" size="x-small" color="grey-lighten-3" variant="flat"
                                    class="font-weight-bold">
                                    ••{{ acc.account_mask }}
                                </v-chip>
                            </div>

                            <!-- Linked Goals -->
                            <div v-if="acc.linked_goals?.length || accountGoalMap[acc.id]" class="d-flex gap-1 mb-2">
                                <v-chip size="x-small" color="indigo-lighten-5"
                                    class="text-indigo-darken-1 border-indigo">
                                    🎯 {{ (acc.linked_goals?.[0]) || (accountGoalMap[acc.id]?.[0]) }}
                                    <span v-if="(acc.linked_goals?.length > 1) || (accountGoalMap[acc.id]?.length > 1)"
                                        class="ml-1">
                                        +{{ (acc.linked_goals?.length || accountGoalMap[acc.id]?.length) - 1 }}
                                    </span>
                                </v-chip>
                            </div>

                            <!-- Owner -->
                            <div class="d-flex align-center gap-2 mt-2">
                                <v-chip size="small" variant="flat" color="grey-lighten-4" class="px-2">
                                    <span class="mr-2">{{ resolveOwnerAvatar(acc) }}</span>
                                    <span class="text-caption font-weight-bold">{{ resolveOwnerName(acc) }}</span>
                                </v-chip>
                            </div>
                        </div>

                        <div class="mt-4 pt-4 border-t">
                            <div class="d-flex justify-space-between align-end">
                                <div>
                                    <div class="text-caption font-weight-bold text-medium-emphasis mb-1">Current Balance
                                    </div>
                                    <div class="text-h5 font-weight-black"
                                        :class="{ 'text-error': Number(acc.balance) < 0 && acc.type !== 'CREDIT_CARD' }">
                                        {{ formatAmount(Math.abs(Number(acc.balance || 0)), acc.currency) }}
                                        <span v-if="acc.type === 'CREDIT_CARD'"
                                            class="text-caption text-medium-emphasis font-weight-bold ml-1">USED</span>
                                    </div>
                                    <div v-if="acc.last_synced_at" class="text-caption text-medium-emphasis mt-1">
                                        Synced: {{ formatAmount(acc.last_synced_balance, acc.currency) }} ({{ new
                                            Date(acc.last_synced_at).toLocaleDateString() }})
                                    </div>
                                </div>
                            </div>

                            <!-- Credit Limit Bar -->
                            <div v-if="acc.type === 'CREDIT_CARD' && acc.credit_limit" class="mt-2">
                                <v-progress-linear
                                    :model-value="(Math.abs(Number(acc.balance || 0)) / Number(acc.credit_limit)) * 100"
                                    color="indigo" bg-color="grey-lighten-3" height="6" rounded></v-progress-linear>
                                <div class="text-caption text-medium-emphasis mt-1 text-right">
                                    {{ Math.round((Math.abs(Number(acc.balance || 0)) / Number(acc.credit_limit)) * 100)
                                    }}% utilized
                                </div>
                            </div>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Add New Account Card -->
            <v-col v-if="!searchQuery" cols="12" md="6" lg="4">
                <v-card class="add-account-card h-100 d-flex flex-column align-center justify-center" elevation="0"
                    @click="openCreateAccountModal">
                    <div class="add-icon-circle mb-3">
                        <Plus :size="32" />
                    </div>
                    <div class="font-weight-bold">Add New Account</div>
                </v-card>
            </v-col>
        </v-row>

        <div v-if="verifiedAccounts.length === 0 && searchQuery" class="text-center py-12 text-medium-emphasis">
            <p>No accounts match "{{ searchQuery }}"</p>
        </div>

        <!-- Account Modal -->
        <v-dialog v-model="showAccountModal" max-width="600">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">{{ editingAccountId ? 'Edit Account' : 'New Account'
                        }}</span>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showAccountModal = false"></v-btn>
                </v-card-title>

                <v-card-text class="pa-4">
                    <v-form @submit.prevent="handleAccountSubmit">
                        <v-text-field v-model="newAccount.name" label="Account Name" placeholder="e.g. HDFC Savings"
                            variant="outlined" class="mb-2" required></v-text-field>

                        <v-row>
                            <v-col cols="12" sm="6">
                                <v-select v-model="newAccount.type" label="Type" :items="[
                                    { title: '🏦 Bank Account', value: 'BANK' },
                                    { title: '💳 Credit Card', value: 'CREDIT_CARD' },
                                    { title: '💸 Loan / EMIs', value: 'LOAN' },
                                    { title: '👛 Wallet / Cash', value: 'WALLET' },
                                    { title: '📈 Investment', value: 'INVESTMENT' }
                                ]" variant="outlined"></v-select>
                            </v-col>
                            <v-col cols="12" sm="6">
                                <v-select v-model="newAccount.currency" label="Currency" :items="[
                                    { title: 'INR - Indian Rupee', value: 'INR' },
                                    { title: 'USD - US Dollar', value: 'USD' }
                                ]" variant="outlined"></v-select>
                            </v-col>
                        </v-row>

                        <v-text-field v-model="newAccount.account_mask" label="Account Mask (Last 4 Digits)"
                            placeholder="e.g. 1234" maxlength="4" variant="outlined" class="mb-2"></v-text-field>

                        <v-select v-model="newAccount.owner_id" label="Account Owner"
                            :items="familyMembers.map(m => ({ title: m.full_name || m.email, value: m.id }))"
                            variant="outlined" class="mb-2"></v-select>

                        <v-row>
                            <v-col :cols="newAccount.type === 'CREDIT_CARD' ? 6 : 12">
                                <v-text-field v-model.number="newAccount.balance" :label="consumedLimitMsg"
                                    type="number" step="0.01" variant="outlined" :disabled="!!editingAccountId"
                                    :hint="editingAccountId ? 'Use Balance Anchoring section below to update' : ''"
                                    persistent-hint></v-text-field>
                            </v-col>
                            <v-col v-if="newAccount.type === 'CREDIT_CARD'" cols="6">
                                <v-text-field v-model.number="newAccount.credit_limit" label="Total Credit Limit"
                                    type="number" step="0.01" variant="outlined" :disabled="!!editingAccountId"
                                    :hint="editingAccountId ? 'Use Balance Anchoring section below to update' : ''"
                                    persistent-hint></v-text-field>
                            </v-col>
                        </v-row>

                        <v-row v-if="newAccount.type === 'CREDIT_CARD'">
                            <v-col cols="6">
                                <v-text-field v-model.number="newAccount.billing_day" label="Billing Day (1-31)"
                                    type="number" min="1" max="31" variant="outlined"></v-text-field>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field v-model.number="newAccount.due_day" label="Due Day (1-31)" type="number"
                                    min="1" max="31" variant="outlined"></v-text-field>
                            </v-col>
                        </v-row>

                        <div class="d-flex justify-space-between align-center py-2 px-1">
                            <div>
                                <div class="font-weight-bold">Verified Account</div>
                                <div class="text-caption text-medium-emphasis">Trust transactions from this source</div>
                            </div>
                            <v-switch v-model="newAccount.is_verified" color="success" hide-details></v-switch>
                        </div>

                        <v-divider class="my-4"></v-divider>

                        <!-- Balance Sync / Anchor Section -->
                        <div v-if="editingAccountId" class="pa-4 bg-grey-lighten-4 rounded-lg mb-4">
                            <div class="d-flex align-center gap-2 mb-2">
                                <Anchor :size="16" class="text-primary" />
                                <span class="text-subtitle-2 font-weight-bold">Balance Anchoring</span>
                            </div>
                            <p class="text-caption text-medium-emphasis mb-4">
                                Manually override the current balance and create a "Ground Truth" anchor for analytics.
                            </p>

                            <v-row dense>
                                <v-col cols="12" sm="6">
                                    <v-text-field v-model.number="balanceOverrideForm.balance"
                                        label="Actual Bank Balance" type="number" step="0.01" variant="outlined"
                                        density="comfortable" hide-details class="mb-2 font-weight-bold"
                                        bg-color="surface"></v-text-field>
                                </v-col>
                                <v-col v-if="newAccount.type === 'CREDIT_CARD'" cols="12" sm="6">
                                    <v-text-field v-model.number="balanceOverrideForm.limit" label="Actual Credit Limit"
                                        type="number" step="0.01" variant="outlined" density="comfortable" hide-details
                                        class="mb-2 font-weight-bold" bg-color="surface"></v-text-field>
                                </v-col>
                            </v-row>

                            <v-btn color="primary" variant="tonal" block size="small" class="mt-2 font-weight-bold"
                                @click="handleBalanceOverride" :loading="overridingBalance">
                                Set New Ground Truth
                            </v-btn>
                        </div>

                        <div class="d-flex gap-3 mt-6">
                            <v-btn variant="text" @click="showAccountModal = false" class="flex-grow-1">Cancel</v-btn>
                            <v-btn type="submit" color="primary" class="flex-grow-1">Save Changes</v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Delete Confirmation -->
        <v-dialog v-model="showAccountDeleteConfirm" max-width="450">
            <v-card class="rounded-xl">
                <v-card-text class="text-center pa-6">
                    <div class="text-h2 mb-4">🗑️</div>
                    <div class="text-h5 font-weight-bold mb-2">Delete Account?</div>
                    <p class="text-body-2 text-medium-emphasis mb-4">
                        You are about to delete <strong>{{ accountToDelete?.name }}</strong>.
                    </p>
                    <v-alert v-if="accountTxCount > 0" type="warning" variant="tonal" class="mb-4 text-left"
                        density="compact">
                        This will also permanently delete {{ accountTxCount }} transactions.
                    </v-alert>
                    <p v-else class="text-caption text-medium-emphasis mb-4">No transactions are currently linked to
                        this account.</p>

                    <div class="d-flex gap-3">
                        <v-btn variant="text" @click="showAccountDeleteConfirm = false" class="flex-grow-1"
                            :disabled="isDeletingAccount">
                            Cancel
                        </v-btn>
                        <v-btn color="error" class="flex-grow-1" @click="confirmAccountDelete"
                            :loading="isDeletingAccount">
                            Delete
                        </v-btn>
                    </div>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useCurrency } from '@/composables/useCurrency'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { Check, X, Edit2, Plus, Landmark, CreditCard, Banknote, Wallet, TrendingUp, Scale, Anchor } from 'lucide-vue-next'

const notify = useNotificationStore()
const { formatAmount } = useCurrency()

// --- Internal State ---
const accounts = ref<any[]>([])
const goals = ref<any[]>([])
const tenants = ref<any[]>([])
const familyMembers = ref<any[]>([])
const searchQuery = ref('')
const loading = ref(false)

const showAccountModal = ref(false)
const editingAccountId = ref<string | null>(null)
const newAccount = ref({
    name: '',
    type: 'BANK',
    currency: 'INR',
    account_mask: '',
    balance: 0,
    credit_limit: null as number | null,
    billing_day: null as number | null,
    due_day: null as number | null,
    is_verified: true,
    tenant_id: '',
    owner_id: ''
})

const balanceOverrideForm = ref({
    balance: 0,
    limit: null as number | null
})
const overridingBalance = ref(false)

const showAccountDeleteConfirm = ref(false)
const accountToDelete = ref<any>(null)
const accountTxCount = ref(0)
const isDeletingAccount = ref(false)

// --- Computed ---
const consumedLimitMsg = computed(() => newAccount.value.type === 'CREDIT_CARD' ? 'Consumed Limit' : 'Current Balance')

const verifiedAccounts = computed(() => {
    let filtered = accounts.value.filter(a => a.is_verified !== false)
    if (searchQuery.value) {
        filtered = filtered.filter(a => a.name.toLowerCase().includes(searchQuery.value.toLowerCase()))
    }
    return filtered
})
const untrustedAccounts = computed(() => accounts.value.filter(a => a.is_verified === false))

const accountMetrics = computed(() => {
    let total = 0
    let cash = 0
    let bank = 0
    let credit = 0

    accounts.value.forEach(a => {
        const bal = Number(a.balance || 0)
        if (a.type === 'CREDIT_CARD' || a.type === 'LOAN') {
            credit += bal
            total -= bal
        } else {
            total += bal
            if (a.type === 'BANK') bank += bal
            if (a.type === 'WALLET' || a.type === 'CASH') cash += bal
        }
    })

    return { total, cash, bank, credit }
})

const accountGoalMap = computed(() => {
    const map: Record<string, string[]> = {}
    if (!goals.value) return map

    goals.value.forEach(goal => {
        if (goal.assets) {
            goal.assets.forEach((asset: any) => {
                if (asset.linked_account_id) {
                    if (!map[asset.linked_account_id]) map[asset.linked_account_id] = []
                    map[asset.linked_account_id].push(goal.name)
                }
            })
        }
    })
    return map
})

function getAccountTypeIcon(type: string) {
    const icons: Record<string, any> = {
        'BANK': Landmark,
        'CREDIT_CARD': CreditCard,
        'LOAN': Banknote,
        'WALLET': Wallet,
        'INVESTMENT': TrendingUp
    }
    return icons[type] || Wallet
}

function getAccountTypeLabel(type: string) {
    const labels: Record<string, string> = {
        'BANK': 'Bank account',
        'CREDIT_CARD': 'Credit Card',
        'LOAN': 'Loans / EMIs',
        'WALLET': 'Wallet / Cash',
        'INVESTMENT': 'Investment'
    }
    return labels[type] || type
}

const resolveOwnerAvatar = (account: any) => {
    if (account.owner_id) {
        const member = familyMembers.value.find(m => m.id === account.owner_id)
        if (member && member.avatar) return member.avatar
    }
    return '👨\u200D👩\u200D👧\u200D👦'
}

const resolveOwnerName = (account: any) => {
    if (account.owner_id) {
        const member = familyMembers.value.find(m => m.id === account.owner_id)
        if (member) return member.full_name || member.email
    }
    return 'Family'
}

async function fetchData() {
    loading.value = true
    try {
        const [accRes, goalsRes, tenantsRes, usersRes] = await Promise.all([
            financeApi.getAccounts(undefined, true), // Include unverified accounts for management
            financeApi.getInvestmentGoals(),
            financeApi.getTenants(),
            financeApi.getUsers()
        ])
        accounts.value = accRes.data
        goals.value = goalsRes.data
        tenants.value = tenantsRes.data
        familyMembers.value = usersRes.data
    } catch (err) {
        console.error('Failed to fetch account settings data', err)
        notify.error("Failed to load data")
    } finally {
        loading.value = false
    }
}

// --- Methods ---
function openCreateAccountModal() {
    editingAccountId.value = null
    newAccount.value = {
        name: '', type: 'BANK', currency: 'INR',
        account_mask: '', balance: 0,
        credit_limit: null,
        billing_day: null,
        due_day: null,
        is_verified: true,
        tenant_id: tenants.value[0]?.id || '',
        owner_id: ''
    }
    showAccountModal.value = true
}

onMounted(() => {
    fetchData()
})

function openEditAccountModal(account: any, autoVerify: boolean = false) {
    editingAccountId.value = account.id
    newAccount.value = {
        name: account.name,
        type: account.type,
        currency: account.currency,
        account_mask: account.account_mask,
        balance: account.balance,
        credit_limit: account.credit_limit,
        billing_day: account.billing_day,
        due_day: account.due_day,
        owner_id: account.owner_id,
        tenant_id: account.tenant_id,
        is_verified: autoVerify ? true : account.is_verified
    }
    // Pre-fill override form
    balanceOverrideForm.value = {
        balance: Number(account.balance || 0),
        limit: account.credit_limit ? Number(account.credit_limit) : null
    }
    showAccountModal.value = true
}

async function handleBalanceOverride() {
    if (!editingAccountId.value) return
    overridingBalance.value = true
    try {
        await financeApi.overrideAccountBalance(editingAccountId.value, {
            balance: balanceOverrideForm.value.balance,
            credit_limit: balanceOverrideForm.value.limit,
            timestamp: new Date().toISOString()
        })
        notify.success("Account balance anchored and snapshot created")
        fetchData()
    } catch (e) {
        notify.error("Failed to anchor balance")
    } finally {
        overridingBalance.value = false
    }
}

async function handleAccountSubmit() {
    try {
        const payload = {
            ...newAccount.value,
            balance: Number(newAccount.value.balance),
            credit_limit: newAccount.value.type === 'CREDIT_CARD' ? Number(newAccount.value.credit_limit) : null,
            billing_day: (newAccount.value.type === 'CREDIT_CARD' && newAccount.value.billing_day) ? Number(newAccount.value.billing_day) : null,
            due_day: (newAccount.value.type === 'CREDIT_CARD' && newAccount.value.due_day) ? Number(newAccount.value.due_day) : null
        }

        if (editingAccountId.value) {
            await financeApi.updateAccount(editingAccountId.value, payload)
            notify.success("Account updated")
        } else {
            await financeApi.createAccount(payload)
            notify.success("Account created")
        }
        showAccountModal.value = false
        fetchData()
    } catch (e) {
        notify.error("Failed to save account")
    }
}

async function deleteAccountRequest(account: any) {
    accountToDelete.value = account
    accountTxCount.value = 0
    try {
        const res = await financeApi.getAccountTransactionCount(account.id)
        accountTxCount.value = res.data.count
    } catch (e) {
        console.error("Failed to fetch tx count", e)
    }
    showAccountDeleteConfirm.value = true
}

async function confirmAccountDelete() {
    if (!accountToDelete.value) return
    isDeletingAccount.value = true
    try {
        await financeApi.deleteAccount(accountToDelete.value.id)
        notify.success("Account and related data removed")
        showAccountDeleteConfirm.value = false
        fetchData()
    } catch (e) {
        notify.error("Failed to delete account")
    } finally {
        isDeletingAccount.value = false
        accountToDelete.value = null
    }
}
</script>

<style scoped>
/* glass-card removed - using global premium-glass-card */

.account-card {
    cursor: pointer;
}

.account-card:hover {
    border-color: rgb(var(--v-theme-primary));
}

.untrusted-border {
    border-top: 3px solid rgb(var(--v-theme-warning)) !important;
}

.verified-highlight {
    border-top: 3px solid rgb(var(--v-theme-success)) !important;
}

.add-account-card {
    border: 2px dashed rgba(var(--v-border-color), 0.3);
    background: transparent !important;
    transition: all 0.2s;
    cursor: pointer;
    min-height: 200px;
}

.add-account-card:hover {
    border-color: rgb(var(--v-theme-primary));
    background: rgba(var(--v-theme-primary), 0.05) !important;
    color: rgb(var(--v-theme-primary));
}

.add-icon-circle {
    width: 64px;
    height: 64px;
    border-radius: 50%;
    background: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.acc-icon-wrapper {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.25rem;
    background: #f8fafc;
    border: 1px solid #f1f5f9;
}

.acc-icon-wrapper.bank {
    background: #e0f2fe;
    color: #0284c7;
}

.acc-icon-wrapper.credit_card {
    background: #fef2f2;
    color: #dc2626;
}

.acc-icon-wrapper.wallet {
    background: #ecfdf5;
    color: #059669;
}

.stat-icon-bg {
    width: 32px;
    height: 32px;
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

.stat-icon-bg.gray {
    background: #f1f5f9;
}

.stat-icon-bg.green {
    background: #ecfdf5;
}

.stat-icon-bg.yellow {
    background: #fffbeb;
}

.stat-icon-bg.red {
    background: #fef2f2;
}

.ls-1 {
    letter-spacing: 0.05em;
}

.gap-1 {
    gap: 4px;
}

.gap-2 {
    gap: 8px;
}

.gap-3 {
    gap: 12px;
}

.gap-4 {
    gap: 16px;
}

.line-clamp-1 {
    overflow: hidden;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 1;
}

.border-indigo {
    border: 1px solid rgb(var(--v-theme-indigo-lighten-4));
}
</style>
