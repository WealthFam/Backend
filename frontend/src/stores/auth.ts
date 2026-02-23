import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import apiClient from '@/api/client'
import { clearStoreCache } from '@/utils/persistence'

interface User {
    id: string
    email: string
    role: string
    tenant_id: string
    full_name?: string
    avatar?: string
}

export const useAuthStore = defineStore('auth', () => {
    const user = ref<User | null>(null)

    const get_url_token = () => {
        const urlParams = new URLSearchParams(window.location.search)
        return urlParams.get('auth_token')
    }

    const token = ref<string | null>(get_url_token() || localStorage.getItem('access_token'))

    if (get_url_token()) {
        localStorage.setItem('access_token', token.value!)
        // Clean up URL after consumption
        const url = new URL(window.location.href)
        url.searchParams.delete('auth_token')
        window.history.replaceState({}, '', url.pathname + url.search)
    }

    const isAuthenticated = computed(() => !!token.value)

    const familyMembers = ref<any[]>([])
    const selectedMemberId = ref<string | null>(null)

    const selectedMemberName = computed(() => {
        if (!selectedMemberId.value) return 'All Members'
        const member = familyMembers.value.find(m => m.id === selectedMemberId.value)
        return member ? (member.full_name || member.email) : 'All Members'
    })

    async function fetchUser() {
        if (!token.value) return
        try {
            const response = await apiClient.get('/auth/me')
            user.value = response.data
            // Fetch family members as well if user is authenticated
            await fetchFamilyMembers()
        } catch (error) {
            console.error("Failed to fetch user profile", error)
        }
    }

    async function fetchFamilyMembers() {
        try {
            const response = await apiClient.get('/auth/users')
            familyMembers.value = response.data
        } catch (error) {
            console.error("Failed to fetch family members", error)
        }
    }

    function selectMember(id: string | null) {
        selectedMemberId.value = id
    }

    async function login(email: string, password: string) {
        try {
            const formData = new FormData()
            formData.append('username', email)
            formData.append('password', password)

            const response = await apiClient.post('/auth/login', formData, {
                headers: { 'Content-Type': 'multipart/form-data' }
            })

            token.value = response.data.access_token
            if (token.value) {
                localStorage.setItem('access_token', token.value)
                await fetchUser()
            }
        } catch (error) {
            throw error
        }
    }

    function logout() {
        token.value = null
        user.value = null
        selectedMemberId.value = null
        familyMembers.value = []
        localStorage.removeItem('access_token')
        clearStoreCache()
    }

    if (token.value) {
        fetchUser()
    }

    return {
        user,
        token,
        isAuthenticated,
        familyMembers,
        selectedMemberId,
        selectedMemberName,
        login,
        logout,
        fetchUser,
        fetchFamilyMembers,
        selectMember
    }
})
