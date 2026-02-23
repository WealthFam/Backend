import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useStorePersistence } from '@/utils/persistence'
import { useNotificationStore } from '@/stores/notification'

export const useCategoriesStore = defineStore('categories', () => {
    // State
    const categories = ref<any[]>([])
    useStorePersistence('categories_full', categories)
    const loading = ref(false)
    const error = ref<string | null>(null)
    const searchFilter = ref('all') // 'all' | 'expense' | 'income' | 'transfer'
    const searchQuery = ref('')

    const notify = useNotificationStore()

    // Getters
    const filteredCategories = computed(() => {
        let result = categories.value
        if (searchFilter.value !== 'all') {
            result = result.filter(c => (c.type || 'expense') === searchFilter.value)
        }
        if (searchQuery.value) {
            const q = searchQuery.value.toLowerCase()
            result = result.filter(c => c.name.toLowerCase().includes(q))
        }
        return result
    })

    const rootCategories = computed(() => {
        return filteredCategories.value.filter(c => !c.parent_id)
    })

    const categoryStats = computed(() => {
        return {
            total: categories.value.length,
            expenses: categories.value.filter(c => (c.type || 'expense') === 'expense').length,
            income: categories.value.filter(c => c.type === 'income').length,
            transfer: categories.value.filter(c => c.type === 'transfer').length,
        }
    })

    function getChildren(parentId: string) {
        return filteredCategories.value.filter(c => c.parent_id === parentId)
    }

    function getCategoryDisplay(name: string) {
        if (!name) return '📝 General'
        const cat = categories.value.find(c => c.name === name)
        return cat ? `${cat.icon || '🏷️'} ${cat.name}` : `🏷️ ${name}`
    }

    // Actions
    async function fetchCategories() {
        loading.value = true
        error.value = null
        try {
            const res = await financeApi.getCategories()
            categories.value = res.data
        } catch (e: any) {
            console.error("Failed to fetch categories", e)
            error.value = e.message || "Failed to load categories"
            notify.error("Failed to load categories")
        } finally {
            loading.value = false
        }
    }

    async function createCategory(data: any) {
        try {
            await financeApi.createCategory(data)
            notify.success("Category created")
            await fetchCategories()
            return true
        } catch (e: any) {
            console.error("Failed to create category", e)
            if (e.response && e.response.data && e.response.data.detail) {
                notify.error(e.response.data.detail)
            } else {
                notify.error("Failed to create category")
            }
            return false
        }
    }

    async function updateCategory(id: string, data: any) {
        try {
            await financeApi.updateCategory(id, data)
            notify.success("Category updated")
            await fetchCategories()
            return true
        } catch (e: any) {
            console.error("Failed to update category", e)
            if (e.response && e.response.data && e.response.data.detail) {
                notify.error(e.response.data.detail)
            } else {
                notify.error("Failed to update category")
            }
            return false
        }
    }

    async function deleteCategory(id: string) {
        try {
            await financeApi.deleteCategory(id)
            notify.success("Category deleted")
            await fetchCategories()
            return true
        } catch (e: any) {
            console.error("Failed to delete category", e)
            notify.error("Failed to delete category")
            return false
        }
    }

    async function importCategories(file: File) {
        try {
            const reader = new FileReader()
            reader.onload = async (e) => {
                try {
                    const json = JSON.parse(e.target?.result as string)
                    if (!Array.isArray(json)) throw new Error("Invalid JSON format")
                    await financeApi.importCategories(json)
                    notify.success("Categories imported")
                    await fetchCategories()
                } catch (err) {
                    notify.error("Invalid JSON file")
                }
            }
            reader.readAsText(file)
        } catch (e) {
            notify.error("Failed to read file")
        }
    }

    function exportCategories() {
        const dataStr = JSON.stringify(categories.value, null, 2)
        const blob = new Blob([dataStr], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `finance_categories_${new Date().toISOString().split('T')[0]}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
        notify.success("Categories exported")
    }

    return {
        categories,
        loading,
        error,
        searchFilter,
        searchQuery,
        filteredCategories,
        rootCategories,
        categoryStats,
        getChildren,
        getCategoryDisplay,
        fetchCategories,
        createCategory,
        updateCategory,
        deleteCategory,
        importCategories,
        exportCategories
    }
})
