<template>
    <div class="animate-in">
        <!-- Family Hero -->
        <v-card v-if="tenants.length > 0" class="family-hero mb-8" elevation="10" rounded="xl">
            <div class="d-flex align-center gap-6 relative z-10 px-6 py-8">
                <div class="d-flex pl-3">
                    <div v-for="(m, i) in familyMembers.slice(0, 3)" :key="m.id" class="stack-avatar"
                        :style="{ zIndex: 3 - i }">
                        <span class="text-h5">{{ m.avatar || '👤' }}</span>
                    </div>
                </div>
                <div class="flex-grow-1 text-white">
                    <div class="d-flex align-center gap-2 mb-1">
                        <h2 class="text-h4 font-weight-black">{{ tenants[0].name }}</h2>
                        <v-btn icon density="compact" variant="text" color="white" class="opacity-80 hover:opacity-100"
                            @click="openRenameTenantModal(tenants[0])">
                            <Edit2 :size="20" />
                        </v-btn>
                    </div>
                    <p class="text-subtitle-1 font-weight-medium opacity-90">
                        {{ familyMembers.length }} Members • {{ accounts.length }} Accounts Tracked
                    </p>
                </div>
            </div>
            <!-- Decorative background element -->
            <div class="hero-bg-decoration"></div>
        </v-card>

        <v-row>
            <v-col v-for="member in familyMembers" :key="member.id" cols="12" md="6" lg="4">
                <v-card class="premium-glass-card member-profile-card h-100 pt-8" elevation="0">
                    <v-btn icon density="comfortable" variant="text" color="medium-emphasis" class="edit-profile-btn"
                        @click="openEditMemberModal(member)">
                        <Edit2 :size="18" />
                    </v-btn>

                    <v-card-text class="d-flex flex-column align-center text-center">
                        <div class="profile-avatar-wrapper mb-4">
                            <div class="gradient-avatar" :class="getRoleColorClass(member.role)">
                                <span class="text-h2">{{ member.avatar || '👤' }}</span>
                            </div>
                            <div v-if="currentUser && currentUser.id === member.id" class="you-indicator"
                                title="That's You!">
                                👋
                            </div>
                        </div>

                        <h3 class="text-h6 font-weight-bold mb-1">{{ member.full_name || 'Anonymous' }}</h3>
                        <div class="text-body-2 text-medium-emphasis mb-3">{{ member.email }}</div>

                        <v-chip size="small" :color="getRoleChipColor(member.role)" variant="flat"
                            class="font-weight-bold text-uppercase ls-1 mb-4">
                            <component :is="getRoleIconComponent(member.role)" :size="14" class="mr-1" />
                            {{ member.role }}
                        </v-chip>

                        <v-divider class="w-100 my-4"></v-divider>

                        <div class="d-flex justify-center w-100">
                            <div class="d-flex flex-column align-center">
                                <span class="text-h5 font-weight-black">{{ getMemberAccountCount(member.id) }}</span>
                                <span
                                    class="text-caption font-weight-bold text-medium-emphasis text-uppercase">Accounts</span>
                            </div>
                        </div>
                    </v-card-text>
                </v-card>
            </v-col>

            <!-- Add New Member Card -->
            <v-col cols="12" md="6" lg="4">
                <v-card class="add-account-card h-100 d-flex flex-column align-center justify-center" elevation="0"
                    @click="openAddMemberModal">
                    <div class="add-icon-circle mb-3">
                        <Plus :size="32" />
                    </div>
                    <div class="font-weight-bold">Add Family Member</div>
                </v-card>
            </v-col>
        </v-row>

        <!-- Add/Edit Family Member Modal -->
        <v-dialog v-model="showMemberModal" max-width="500">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">{{ isEditingMember ? 'Edit Profile' : 'Add Family Member'
                    }}</span>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showMemberModal = false"></v-btn>
                </v-card-title>

                <v-card-text class="pa-4">
                    <v-form @submit.prevent="handleMemberSubmit">
                        <!-- Avatar Picker -->
                        <div class="avatar-picker-grid mb-4">
                            <div v-for="a in ['👨‍💼', '👩‍💼', '👶', '👴', '👵', '👨‍🎓', '👩‍🎓', '🐶']" :key="a"
                                class="avatar-option" :class="{ active: memberForm.avatar === a }"
                                @click="memberForm.avatar = a">
                                {{ a }}
                            </div>
                            <v-btn variant="text" size="small" class="avatar-option" icon>
                                <input v-model="memberForm.avatar" class="emoji-input-sm" maxlength="2"
                                    placeholder="🔍" />
                            </v-btn>
                        </div>

                        <v-text-field v-model="memberForm.full_name" label="Full Name" placeholder="e.g. Sarah Smith"
                            variant="outlined" required></v-text-field>

                        <v-row>
                            <v-col cols="6">
                                <v-text-field v-model="memberForm.dob" label="Date of Birth" type="date"
                                    variant="outlined"></v-text-field>
                            </v-col>
                            <v-col cols="6">
                                <v-text-field v-model="memberForm.pan_number" label="PAN Number"
                                    :type="showPan ? 'text' : 'password'"
                                    :append-inner-icon="showPan ? 'EyeOff' : 'Eye'"
                                    @click:append-inner="showPan = !showPan" placeholder="ABCDE1234F" maxlength="10"
                                    variant="outlined"></v-text-field>
                            </v-col>
                        </v-row>

                        <v-text-field v-model="memberForm.email" label="Email Address" type="email"
                            :disabled="isEditingMember" placeholder="sarah@example.com" variant="outlined"
                            required></v-text-field>

                        <v-text-field v-model="memberForm.password"
                            :label="`Password ${isEditingMember ? '(Leave empty to keep current)' : ''}`"
                            type="password" :required="!isEditingMember" variant="outlined"></v-text-field>

                        <v-select v-model="memberForm.role" label="Role / Permissions" :items="[
                            { title: 'Admin (See everything)', value: 'OWNER' },
                            { title: 'Adult (Edit access)', value: 'ADULT' },
                            { title: 'Child (Watch only / Restricted)', value: 'CHILD' },
                            { title: 'Guest', value: 'GUEST' }
                        ]" variant="outlined"></v-select>

                        <div class="d-flex justify-end gap-3 mt-4">
                            <v-btn variant="text" @click="showMemberModal = false">Cancel</v-btn>
                            <v-btn type="submit" color="primary">
                                {{ isEditingMember ? 'Save Changes' : 'Add Member' }}
                            </v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>

        <!-- Tenant Rename Modal -->
        <v-dialog v-model="showTenantModal" max-width="400">
            <v-card class="rounded-xl">
                <v-card-title class="d-flex justify-space-between align-center pa-4 border-b">
                    <span class="text-h6 font-weight-bold">Rename Family Circle</span>
                    <v-btn icon="X" variant="text" density="comfortable" @click="showTenantModal = false"></v-btn>
                </v-card-title>

                <v-card-text class="pa-4">
                    <v-form @submit.prevent="handleRenameTenant">
                        <v-text-field v-model="tenantForm.name" label="New Family Name" placeholder="e.g. The Smiths"
                            variant="outlined" required autofocus></v-text-field>

                        <div class="d-flex justify-end gap-3 mt-4">
                            <v-btn variant="text" @click="showTenantModal = false">Cancel</v-btn>
                            <v-btn type="submit" color="primary">Save Changes</v-btn>
                        </div>
                    </v-form>
                </v-card-text>
            </v-card>
        </v-dialog>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'
import { Edit2, Plus, Shield, ShieldCheck, Baby, User } from 'lucide-vue-next'

const notify = useNotificationStore()

// --- Internal State ---
const tenants = ref<any[]>([])
const familyMembers = ref<any[]>([])
const accounts = ref<any[]>([])
const currentUser = ref<any>(null)
const loading = ref(false)

const showMemberModal = ref(false)
const isEditingMember = ref(false)
const memberForm = ref({
    id: '',
    email: '',
    full_name: '',
    password: '',
    role: 'ADULT',
    avatar: '👨‍💼',
    dob: '',
    pan_number: ''
})
const showPan = ref(false)

const showTenantModal = ref(false)
const tenantForm = ref({ id: '', name: '' })

// --- Computed ---
const getMemberAccountCount = (memberId: string) => {
    return accounts.value.filter(a => a.owner_id === memberId).length
}

const getRoleIconComponent = (role: string) => {
    switch (role) {
        case 'OWNER': return ShieldCheck
        case 'ADULT': return Shield
        case 'CHILD': return Baby
        default: return User
    }
}

const getRoleChipColor = (role: string) => {
    switch (role) {
        case 'OWNER': return 'orange-lighten-4' // Customized via class for text color usually, but keeping simple
        case 'ADULT': return 'blue-lighten-4'
        case 'CHILD': return 'green-lighten-4'
        default: return 'grey-lighten-3'
    }
}

const getRoleColorClass = (role: string) => {
    switch (role) {
        case 'OWNER': return 'ring-gold'
        case 'ADULT': return 'ring-blue'
        case 'CHILD': return 'ring-green'
        default: return 'ring-gray'
    }
}

// --- Fetch Data ---
async function fetchData() {
    loading.value = true
    try {
        const [tenantsRes, usersRes, accountsRes, meRes] = await Promise.all([
            financeApi.getTenants(),
            financeApi.getUsers(),
            financeApi.getAccounts(),
            financeApi.getMe()
        ])
        tenants.value = tenantsRes.data
        familyMembers.value = usersRes.data
        accounts.value = accountsRes.data
        currentUser.value = meRes.data
    } catch (e) {
        console.error("Failed to fetch family settings", e)
        notify.error("Failed to load family settings")
    } finally {
        loading.value = false
    }
}

// Logic
function openRenameTenantModal(tenant: any) {
    tenantForm.value = { id: tenant.id, name: tenant.name }
    showTenantModal.value = true
}

async function handleRenameTenant() {
    if (!tenantForm.value.name) return
    try {
        await financeApi.updateTenant(tenantForm.value.id, { name: tenantForm.value.name })
        notify.success("Family name updated")
        showTenantModal.value = false
        fetchData()
    } catch (err) {
        notify.error("Rename failed")
    }
}

function openAddMemberModal() {
    isEditingMember.value = false
    memberForm.value = {
        id: '',
        email: '',
        full_name: '',
        password: '',
        role: 'ADULT' as any,
        avatar: '👨‍💼',
        dob: '',
        pan_number: ''
    }
    showPan.value = false
    showMemberModal.value = true
}

function openEditMemberModal(member: any) {
    isEditingMember.value = true
    memberForm.value = {
        id: member.id,
        email: member.email,
        full_name: member.full_name || '',
        password: '',
        role: member.role,
        avatar: member.avatar || '👤',
        dob: member.dob || '',
        pan_number: member.pan_number || ''
    }
    showPan.value = false
    showMemberModal.value = true
}

async function handleMemberSubmit() {
    try {
        if (isEditingMember.value) {
            await financeApi.updateUser(memberForm.value.id, {
                full_name: memberForm.value.full_name,
                avatar: memberForm.value.avatar,
                role: memberForm.value.role,
                dob: memberForm.value.dob || undefined,
                pan_number: memberForm.value.pan_number || undefined,
                password: memberForm.value.password || undefined
            })
            notify.success("Member updated")
        } else {
            await financeApi.createUser(memberForm.value)
            notify.success("Member added successfully")
        }
        showMemberModal.value = false
        fetchData()
    } catch (err: any) {
        notify.error(err.response?.data?.detail || "Action failed")
    }
}

onMounted(() => {
    fetchData()
})
</script>

<style scoped>
.family-hero {
    background: linear-gradient(135deg, rgb(var(--v-theme-primary)) 0%, rgb(var(--v-theme-secondary)) 100%);
    position: relative;
    overflow: hidden;
    color: white;
}

.hero-bg-decoration {
    position: absolute;
    top: 0;
    right: 0;
    width: 250px;
    height: 250px;
    background: radial-gradient(circle, rgba(var(--v-theme-on-primary), 0.2) 0%, transparent 70%);
    transform: translate(30%, -30%);
    pointer-events: none;
}

.stack-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background: rgba(var(--v-theme-primary), 0.1);
    border: 3px solid rgba(var(--v-theme-on-surface), 0.1);
    display: flex;
    align-items: center;
    justify-content: center;
    margin-left: -12px;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* glass-card removed - using global premium-glass-card */

.member-profile-card:hover {
    border-color: rgb(var(--v-theme-primary));
    transform: translateY(-4px);
    box-shadow: 0 10px 20px -10px rgba(var(--v-theme-primary), 0.2);
}

.edit-profile-btn {
    position: absolute;
    top: 8px;
    right: 8px;
}

.gradient-avatar {
    width: 80px;
    height: 80px;
    border-radius: 24px;
    background: rgba(var(--v-theme-on-surface), 0.05);
    display: flex;
    align-items: center;
    justify-content: center;
    border: 4px solid rgb(var(--v-theme-surface));
    box-shadow: 0 4px 10px -2px rgba(0, 0, 0, 0.1);
}

.ring-gold {
    background: linear-gradient(135deg, rgba(var(--v-theme-warning), 0.2), rgba(var(--v-theme-warning), 0.1));
}

.ring-blue {
    background: linear-gradient(135deg, rgba(var(--v-theme-info), 0.2), rgba(var(--v-theme-info), 0.1));
}

.ring-green {
    background: linear-gradient(135deg, rgba(var(--v-theme-success), 0.2), rgba(var(--v-theme-success), 0.1));
}

.ring-gray {
    background: rgba(var(--v-theme-on-surface), 0.05);
}

.you-indicator {
    position: absolute;
    bottom: -8px;
    right: -8px;
    background: rgb(var(--v-theme-surface));
    border: 2px solid rgba(var(--v-border-color), 0.5);
}

.add-account-card {
    border: 2px dashed rgba(var(--v-border-color), 0.3);
    background: transparent !important;
    transition: all 0.2s;
    cursor: pointer;
    min-height: 280px;
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
    background: rgb(var(--v-theme-surface));
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.avatar-picker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(40px, 1fr));
    gap: 8px;
    padding: 16px;
    background: rgba(var(--v-theme-surface-variant), 0.3);
    border-radius: 12px;
}

.avatar-option {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    cursor: pointer;
    border-radius: 8px;
    border: 2px solid transparent;
    transition: all 0.2s;
}

.avatar-option.active {
    border-color: rgb(var(--v-theme-primary));
    background: white;
    box-shadow: 0 2px 4px rgba(var(--v-theme-primary), 0.2);
}

.emoji-input-sm {
    text-align: center;
    font-size: 1.25rem;
    width: 100%;
    outline: none;
}
</style>
