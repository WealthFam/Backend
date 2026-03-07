import { defineStore } from 'pinia'
import { ref } from 'vue'
import { aiApi, parserApi } from '@/api/client'
import { useNotificationStore } from '@/stores/notification'

export const useAiStore = defineStore('ai', () => {
    const notify = useNotificationStore()

    const aiForm = ref({
        provider: 'gemini',
        model_name: 'gemini-1.5-flash',
        api_key: '',
        is_enabled: false,
        prompts: {
            parsing: "Extract transaction details from the following message. Return JSON with: amount (number), date (DD/MM/YYYY), recipient (string), account_mask (4 digits), ref_id (string or null), type (DEBIT/CREDIT)."
        } as Record<string, string>,
        has_api_key: false
    })

    const aiModels = ref<{ label: string, value: string, detail?: string, speed?: string }[]>([])
    const isTestingAi = ref(false)
    const aiTestResult = ref<any>(null)

    async function fetchAiSettings() {
        try {
            const res = await aiApi.getSettings()
            const data = res.data
            aiForm.value = {
                ...aiForm.value,
                ...data,
                api_key: data.api_key || '',
                prompts: data.prompts || aiForm.value.prompts
            }
            fetchAiModels()
        } catch (e) {
            console.error("Failed to load AI settings", e)
        }
    }

    async function fetchAiModels() {
        try {
            const res = await aiApi.listModels(aiForm.value.provider, aiForm.value.api_key)
            if (res.data && res.data.length > 0) {
                aiModels.value = res.data
            } else {
                aiModels.value = [
                    { label: 'Gemini 1.5 Flash', value: 'models/gemini-1.5-flash', detail: 'Speed: Ultra Fast / Best for extraction', speed: 'Fast' },
                    { label: 'Gemini 1.5 Pro', value: 'models/gemini-1.5-pro', detail: 'Speed: Balanced / High reasoning', speed: 'Smart' },
                    { label: 'Gemini 2.0 Flash', value: 'models/gemini-2.0-flash', detail: 'Speed: Next-gen / Best all-rounder', speed: 'V2' }
                ]
            }
        } catch (e) {
            console.error("Failed to fetch AI models", e)
        }
    }

    async function saveAiSettings() {
        try {
            await aiApi.updateSettings(aiForm.value)
            if (aiForm.value.api_key || aiForm.value.has_api_key) {
                try {
                    await parserApi.updateAiConfig({
                        is_enabled: aiForm.value.is_enabled,
                        model_name: aiForm.value.model_name,
                        api_key: aiForm.value.api_key || undefined
                    })
                } catch (pe) {
                    console.error("Failed to auto-configure parser", pe)
                }
            }
            notify.success("AI settings updated")
            fetchAiSettings()
        } catch (e) {
            notify.error("Failed to update AI settings")
        }
    }

    async function testAi(message: string) {
        if (isTestingAi.value) return
        isTestingAi.value = true
        aiTestResult.value = null
        try {
            const res = await aiApi.testConnection(message)
            aiTestResult.value = res.data
            if (res.data.status === 'success') {
                notify.success("AI test successful")
            } else {
                notify.info("AI test failed")
            }
        } catch (e) {
            notify.error("AI test error")
        } finally {
            isTestingAi.value = false
        }
    }

    return {
        aiForm,
        aiModels,
        isTestingAi,
        aiTestResult,
        fetchAiSettings,
        fetchAiModels,
        saveAiSettings,
        testAi
    }
})
