import { useSettingsStore } from '@/stores/settings'

export function useCurrency() {
    const settings = useSettingsStore()

    const formatAmount = (amount: number | string | null | undefined, currency = 'INR', compact = false, skipMasking = false) => {
        if (amount === null || amount === undefined || amount === '') return '-'

        const val = Number(amount)
        if (isNaN(val)) return '-'

        // Apply Masking
        const maskedVal = skipMasking ? val : val / (settings.maskingFactor || 1)

        const options: Intl.NumberFormatOptions = {
            style: 'currency',
            currency: currency,
            maximumFractionDigits: 0
        }

        if (compact) {
            options.notation = 'compact'
            options.compactDisplay = 'short'
        }

        return new Intl.NumberFormat('en-IN', options).format(maskedVal)
    }

    return {
        formatAmount
    }
}
