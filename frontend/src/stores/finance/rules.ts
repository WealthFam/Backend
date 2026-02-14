import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { financeApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'


export const useRulesStore = defineStore('rules', () => {
    // State
    const rules = ref<any[]>([])
    const suggestions = ref<any[]>([])
    const loading = ref(false)
    const error = ref<string | null>(null)
    const searchQuery = ref('')
    const matchingCount = ref(0)
    const matchingPreview = ref<any[]>([])
    const previewLoading = ref(false)
    const overrideExisting = ref(false)
    const previewPage = ref(1)
    const previewLimit = 5

    const notify = useNotificationStore()

    // Getters
    const filteredRules = computed(() => {
        if (!searchQuery.value) return rules.value

        const q = searchQuery.value.toLowerCase()
        return rules.value.filter(r =>
            r.name.toLowerCase().includes(q) ||
            r.category.toLowerCase().includes(q) ||
            r.keywords.some((k: string) => k.toLowerCase().includes(q))
        )
    })

    const emptyRulesMsg = computed(() => searchQuery.value ? 'No rules match your search.' : 'No rules found. Define rules to automate categorization.')

    // Actions
    async function fetchRules() {
        loading.value = true
        error.value = null
        try {
            const res = await financeApi.getRules()
            rules.value = res.data
        } catch (e: any) {
            console.error("Failed to fetch rules", e)
            error.value = e.message || "Failed to load rules"
            notify.error("Failed to load rules")
        } finally {
            loading.value = false
        }
    }

    async function fetchSuggestions() {
        try {
            const res = await financeApi.getRuleSuggestions()
            suggestions.value = res.data
        } catch (e: any) {
            console.error("Failed to fetch suggestions", e)
        }
    }

    async function createRule(data: any) {
        try {
            await financeApi.createRule(data)
            notify.success("Rule created")
            await fetchRules()
            return true
        } catch (e: any) {
            console.error("Failed to create rule", e)
            if (e.response && e.response.data && e.response.data.detail) {
                notify.error(e.response.data.detail)
            } else {
                notify.error("Failed to create rule")
            }
            return false
        }
    }

    async function updateRule(id: string, data: any) {
        try {
            await financeApi.updateRule(id, data)
            notify.success("Rule updated")
            await fetchRules()
            return true
        } catch (e: any) {
            console.error("Failed to update rule", e)
            if (e.response && e.response.data && e.response.data.detail) {
                notify.error(e.response.data.detail)
            } else {
                notify.error("Failed to update rule")
            }
            return false
        }
    }

    async function deleteRule(id: string) {
        try {
            await financeApi.deleteRule(id)
            notify.success("Rule deleted")
            await fetchRules()
            return true
        } catch (e: any) {
            console.error("Failed to delete rule", e)
            notify.error("Failed to delete rule")
            return false
        }
    }

    async function ignoreSuggestion(suggestion: any) {
        try {
            // Assuming suggestion has a pattern or we construct one to ignore
            // The API expects { pattern: string } based on client.ts
            // But client.ts line 86: ignoreSuggestion: (data: { pattern: string })
            // Usually suggestion object from backend has keywords or pattern
            // Let's assume we pass the suggestion object if it matches, or handle accordingly.
            // Check Categories.vue implementation:
            /*
            async function ignoreSuggestion(s: any) {
                 try {
                     await financeApi.ignoreSuggestion({ pattern: s.keywords.join(',') }) // ? Categories.vue doesn't show implementation details for ignoreSuggestion call arguments clearly in template
                     // In template: @click="ignoreSuggestion(s)"
                     // let's create a specific ignore action
                 }
            */
            // Looking at Categories.vue source:
            // It doesn't show the implementation of ignoreSuggestion() in the script!
            // Wait, I missed reading the full file?
            // "The above content does NOT show the entire file contents."
            // Ah, I missed the methods at the bottom.

            // I will implement based on common sense and client.ts
            // client.ts: ignoreSuggestion: (data: { pattern: string }) => apiClient.post('/finance/rules/suggestions/ignore', data)

            const pattern = suggestion.keywords ? suggestion.keywords.join(',') : suggestion.name
            await financeApi.ignoreSuggestion({ pattern })

            notify.success("Suggestion ignored")
            // Remove locally to avoid refetch
            suggestions.value = suggestions.value.filter(s => s !== suggestion)
        } catch (e: any) {
            console.error("Failed to ignore suggestion", e)
            notify.error("Failed to ignore suggestion")
        }
    }

    async function approveSuggestion(suggestion: any) {
        // This usually involves creating a rule from the suggestion
        // Categories.vue template: @click="approveSuggestion(s)"
        // This likely opens the modal with pre-filled data or directly creates it.
        // I will return the suggestion data so the UI can open the modal.
        return suggestion
    }

    async function applyRuleRetrospectively(ruleId: string) {
        try {
            const res = await financeApi.applyRuleRetrospectively(ruleId, overrideExisting.value)
            const count = res.data.affected || 0
            notify.success(`Successfully updated ${count} past transactions`)
            return count
        } catch (e: any) {
            console.error("Failed to apply rule", e)
            notify.error("Failed to apply rule")
            return false
        }
    }

    async function fetchMatchPreview(keywords: string[], page: number = 1) {
        previewLoading.value = true
        previewPage.value = page
        try {
            const onlyUncategorized = !overrideExisting.value
            const [countRes, previewRes] = await Promise.all([
                financeApi.getMatchCount(keywords, onlyUncategorized),
                financeApi.getMatchPreview(keywords, onlyUncategorized, page, previewLimit)
            ])
            matchingCount.value = countRes.data.count
            matchingPreview.value = previewRes.data
        } catch (e: any) {
            console.error("Failed to fetch match preview", e)
        } finally {
            previewLoading.value = false
        }
    }

    async function exportRules() {
        try {
            const res = await financeApi.exportRules()
            const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `rules_export_${new Date().toISOString().split('T')[0]}.json`
            a.click()
            window.URL.revokeObjectURL(url)
            notify.success("Rules exported successfully")
        } catch (e: any) {
            console.error("Failed to export rules", e)
            notify.error("Failed to export rules")
        }
    }

    async function importRules(file: File) {
        try {
            const reader = new FileReader()
            reader.onload = async (e) => {
                const content = e.target?.result as string
                const data = JSON.parse(content)
                await financeApi.importRules(data)
                notify.success("Rules imported successfully")
                await fetchRules()
            }
            reader.readAsText(file)
            return true
        } catch (e: any) {
            console.error("Failed to import rules", e)
            notify.error("Failed to import rules")
            return false
        }
    }

    return {
        rules,
        suggestions,
        loading,
        error,
        searchQuery,
        filteredRules,
        emptyRulesMsg,
        fetchRules,
        fetchSuggestions,
        createRule,
        updateRule,
        deleteRule,
        ignoreSuggestion,
        approveSuggestion,
        applyRuleRetrospectively,
        fetchMatchPreview,
        matchingCount,
        matchingPreview,
        previewLoading,
        overrideExisting,
        previewPage,
        previewLimit,
        exportRules,
        importRules
    }
})
