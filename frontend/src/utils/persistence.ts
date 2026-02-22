import { watch, type Ref, computed } from 'vue'

/**
 * Simple Pinia store persistence helper.
 * Loads state from localStorage on init and watches for changes to save.
 * @param name - Unique name for the cache key
 * @param state - The reactive state ref to persist
 * @param memberId - Optional ref to a member ID for member-specific caching
 */
export function useStorePersistence<T>(name: string, state: Ref<T>, memberId?: Ref<string | null>) {
    // 0. Capture initial state for resetting
    const initialState = JSON.parse(JSON.stringify(state.value))

    // 1. Computed key for dynamic caching (e.g. member switching)
    const cacheKey = computed(() => {
        const suffix = memberId?.value ? `_${memberId.value}` : ''
        return `wf_cache_${name}${suffix}`
    })

    // 2. Load from localStorage - immediate and on key change
    const loadFromCache = (key: string) => {
        const saved = localStorage.getItem(key)
        if (saved) {
            try {
                const parsed = JSON.parse(saved)
                // Merge or replace based on type
                if (Array.isArray(parsed) && Array.isArray(state.value)) {
                    state.value = parsed as any
                } else if (typeof parsed === 'object' && parsed !== null && typeof state.value === 'object' && state.value !== null) {
                    state.value = { ...state.value, ...parsed }
                } else {
                    state.value = parsed
                }
            } catch (e) {
                console.warn(`[Persistence] Failed to parse cached ${name}`, e)
                state.value = JSON.parse(JSON.stringify(initialState))
            }
        } else {
            // Reset to initial state if no cache found for this key
            state.value = JSON.parse(JSON.stringify(initialState))
        }
    }

    // Initial load
    loadFromCache(cacheKey.value)

    // Reload when member/key changes
    watch(cacheKey, (newKey, oldKey) => {
        if (newKey !== oldKey) {
            loadFromCache(newKey)
        }
    })

    // 3. Watch and save
    watch(state, (newVal) => {
        try {
            localStorage.setItem(cacheKey.value, JSON.stringify(newVal))
        } catch (e) {
            console.error(`[Persistence] Failed to save ${name} to cache`, e)
        }
    }, { deep: true })
}

/**
 * Clears all WealthFam related cache from localStorage.
 */
export function clearStoreCache() {
    const keys = Object.keys(localStorage)
    keys.forEach(key => {
        if (key.startsWith('wf_cache_')) {
            localStorage.removeItem(key)
        }
    })
}
