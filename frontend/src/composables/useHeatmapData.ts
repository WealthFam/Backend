import { ref, watch } from 'vue'
import { financeApi } from '@/api/client'
import { useAuthStore } from '@/stores/auth'

export interface HeatmapDataPoint {
    latitude: number
    longitude: number
    amount: number
    category?: string
    description?: string
    recipient?: string
}

export function useHeatmapData(startDate: () => string, endDate: () => string) {
    const data = ref<HeatmapDataPoint[]>([])
    const loading = ref(false)
    const auth = useAuthStore()

    async function fetchHeatmap() {
        loading.value = true
        try {
            const res = await financeApi.getHeatmapData(startDate(), endDate(), auth.selectedMemberId || undefined)
            data.value = res.data
        } catch (e) {
            console.error('Failed to fetch heatmap', e)
        } finally {
            loading.value = false
        }
    }

    watch([startDate, endDate, () => auth.selectedMemberId], () => {
        fetchHeatmap()
    })

    return {
        data,
        loading,
        fetchHeatmap
    }
}
