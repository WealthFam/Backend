<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import apiClient from '@/api/client'
import { Mail, Lock, Building, ArrowRight, Loader2 } from 'lucide-vue-next'

const router = useRouter()

const familyName = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
    if (password.value !== confirmPassword.value) {
        error.value = "Passwords do not match"
        return
    }

    loading.value = true
    error.value = ''

    try {
        await apiClient.post('/auth/register', {
            tenant: { name: familyName.value },
            user: { email: email.value, password: password.value }
        })
        router.push('/login')
    } catch (e: any) {
        error.value = e.response?.data?.detail || 'Registration failed'
    } finally {
        loading.value = false
    }
}
</script>

<template>
    <v-app>
        <v-main class="bg-grey-lighten-4 d-flex align-center position-relative overflow-hidden"
            style="min-height: 100vh;">
            <!-- Animated Background Mesh -->
            <div class="mesh-background">
                <div class="mesh-blob blob-1"></div>
                <div class="mesh-blob blob-2"></div>
                <div class="mesh-blob blob-3"></div>
            </div>

            <v-container class="position-relative" style="z-index: 10;" fluid>
                <v-row align="center" justify="center">
                    <v-col cols="12" sm="10" md="6" lg="5">
                        <v-card class="pa-8 pa-sm-12 rounded-xl border elevation-0"
                            style="background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);">
                            <div class="text-center mb-8">
                                <v-avatar size="64" rounded="lg" class="elevation-2 mb-6 bg-white">
                                    <v-img src="/logo.png" alt="WealthFam Logo" cover></v-img>
                                </v-avatar>
                                <h1 class="text-h5 font-weight-black text-slate-900 mb-2">Join WealthFam</h1>
                                <p class="text-body-1 text-grey-darken-1 font-weight-medium">Start your family's journey
                                    to financial freedom</p>
                            </div>

                            <v-form @submit.prevent="handleRegister">
                                <v-text-field v-model="familyName" label="Family Name" placeholder="The Smiths"
                                    variant="outlined" color="primary" required class="mb-4" rounded="lg"
                                    hide-details="auto">
                                    <template v-slot:prepend-inner>
                                        <Building :size="20" class="text-grey-lighten-1 mr-2" />
                                    </template>
                                </v-text-field>

                                <v-text-field v-model="email" label="Email Address" placeholder="admin@family.com"
                                    variant="outlined" color="primary" required class="mb-6" rounded="lg"
                                    hide-details="auto">
                                    <template v-slot:prepend-inner>
                                        <Mail :size="20" class="text-grey-lighten-1 mr-2" />
                                    </template>
                                </v-text-field>

                                <v-row class="mb-4">
                                    <v-col cols="12" sm="6" class="py-0">
                                        <div class="mb-4 mb-sm-0">
                                            <span
                                                class="text-caption font-weight-bold text-uppercase tracking-wider text-grey-darken-2 d-block mb-1 px-1">Password</span>
                                            <v-text-field v-model="password" placeholder="••••••••" variant="outlined"
                                                color="primary" type="password" required rounded="lg"
                                                hide-details="auto">
                                                <template v-slot:prepend-inner>
                                                    <Lock :size="20" class="text-grey-lighten-1 mr-2" />
                                                </template>
                                            </v-text-field>
                                        </div>
                                    </v-col>
                                    <v-col cols="12" sm="6" class="py-0">
                                        <div>
                                            <span
                                                class="text-caption font-weight-bold text-uppercase tracking-wider text-grey-darken-2 d-block mb-1 px-1">Confirm</span>
                                            <v-text-field v-model="confirmPassword" placeholder="••••••••"
                                                variant="outlined" color="primary" type="password" required rounded="lg"
                                                hide-details="auto">
                                                <template v-slot:prepend-inner>
                                                    <Lock :size="20" class="text-grey-lighten-1 mr-2" />
                                                </template>
                                            </v-text-field>
                                        </div>
                                    </v-col>
                                </v-row>

                                <v-expand-transition>
                                    <v-alert v-if="error" type="error" variant="tonal" class="mb-6 rounded-lg"
                                        density="comfortable">
                                        {{ error }}
                                    </v-alert>
                                </v-expand-transition>

                                <v-btn type="submit" color="primary" size="x-large" block
                                    class="rounded-lg font-weight-bold text-none elevation-4 mt-2" :loading="loading"
                                    style="height: 56px;">
                                    <div class="d-flex align-center gap-2">
                                        Get Started
                                        <ArrowRight :size="20" />
                                    </div>
                                    <template v-slot:loader>
                                        <Loader2 :size="28" class="spinner" />
                                    </template>
                                </v-btn>
                            </v-form>

                            <div class="text-center mt-10">
                                <p class="text-body-2 text-grey-darken-1 font-weight-medium">
                                    Already have an account?
                                    <router-link to="/login" class="text-primary text-decoration-none font-weight-bold">
                                        Sign In
                                    </router-link>
                                </p>
                            </div>
                        </v-card>

                        <div class="text-center mt-8 overflow-hidden">
                            <p class="text-overline tracking-widest text-grey-darken-1" style="opacity: 0.7;">
                                Securely organized. Beautifully managed.
                            </p>
                        </div>
                    </v-col>
                </v-row>
            </v-container>
        </v-main>
    </v-app>
</template>

<style scoped>
/* Mesh Background Animation preserved for premium feel */
.mesh-background {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 0;
    background: radial-gradient(circle at 50% 50%, #f1f5f9 0%, #e2e8f0 100%);
}

.mesh-blob {
    position: absolute;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.4;
}

.blob-1 {
    width: 600px;
    height: 600px;
    background: #4f46e5;
    top: -150px;
    left: -150px;
    animation: float 20s infinite alternate;
}

.blob-2 {
    width: 500px;
    height: 500px;
    background: #8b5cf6;
    bottom: -100px;
    right: -100px;
    animation: float 25s infinite alternate-reverse;
}

.blob-3 {
    width: 400px;
    height: 400px;
    background: #0ea5e9;
    top: 40%;
    right: 15%;
    animation: float 18s infinite alternate;
}

@keyframes float {
    0% {
        transform: translateY(0) scale(1);
    }

    100% {
        transform: translateY(40px) scale(1.1);
    }
}

.spinner {
    animation: spin 1s linear infinite;
}

@keyframes spin {
    from {
        transform: rotate(0deg);
    }

    to {
        transform: rotate(360deg);
    }
}

/* Custom gap utility */
.gap-2 {
    gap: 0.5rem;
}
</style>
