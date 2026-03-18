import { computed, type Ref } from 'vue'

/**
 * Transaction Helper Functions Composable
 * Provides formatting and display utilities for transactions
 */
export function useTransactionHelpers(
    accounts: Ref<any[]>,
    categories: Ref<any[]>,
    expenseGroups: Ref<any[]>
) {
    /**
     * Format a timestamp into a 'time ago' string
     * @param timestamp - ISO date string
     * @returns Relative time string (e.g., '2h ago')
     */
    function formatTimeAgo(timestamp: string) {
        if (!timestamp) return 'Now'
        const date = new Date(timestamp)
        const now = new Date()
        const diff = now.getTime() - date.getTime()

        if (diff < 60000) return 'Just now'
        if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
        if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
        return date.toLocaleDateString()
    }

    /**
     * Format a date string into a human-readable format
     * @param dateStr - ISO date string
     * @returns Object with day and meta (time) information
     */
    function formatDate(dateStr: string) {
        if (!dateStr) return { day: 'N/A', meta: '' }

        const d = new Date(dateStr)
        if (isNaN(d.getTime())) {
            return { day: '?', meta: dateStr.split('T')[0] || dateStr }
        }

        const today = new Date()
        const yesterday = new Date(today)
        yesterday.setDate(yesterday.getDate() - 1)

        const time = d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })

        // Check if today or yesterday
        if (d.toDateString() === today.toDateString()) {
            return { day: 'Today', meta: time }
        }
        if (d.toDateString() === yesterday.toDateString()) {
            return { day: 'Yesterday', meta: time }
        }

        // Regular date - show day number with time and YEAR if different
        const currentYear = today.getFullYear()
        const txnYear = d.getFullYear()

        let formatOptions: Intl.DateTimeFormatOptions = { month: 'short', day: 'numeric' }
        if (txnYear !== currentYear) {
            formatOptions.year = 'numeric'
        }

        const monthDay = d.toLocaleDateString('en-US', formatOptions)
        return {
            day: monthDay,
            meta: time
        }
    }

    /**
     * Get account name by ID
     * @param id - Account ID
     * @returns Account name or 'Unknown Account'
     */
    function getAccountName(id: string) {
        const acc = accounts.value.find(a => a.id === id)
        return acc ? acc.name : 'Unknown Account'
    }

    /**
     * Get category display information (icon, text, color)
     * @param name - Category name
     * @returns Category display object
     */
    function getCategoryDisplay(name: string) {
        if (!name || name === 'Uncategorized') {
            return { icon: '🏷️', text: 'Uncategorized', color: '#9ca3af' }
        }

        // Find category in the flat list
        const cat = categories.value.find(c => c.name === name)
        if (cat) {
            let text = cat.name
            // If it has a parent, show a bit of hierarchy in the list
            if (cat.parent_name) {
                text = `${cat.parent_name} › ${cat.name}`
            }
            return { icon: cat.icon || '🏷️', text: text, color: cat.color || '#3B82F6' }
        }

        // Fallback for categories without matched object
        return { icon: '🏷️', text: name, color: '#9ca3af' }
    }

    /**
     * Get expense group name by ID
     * @param id - Expense group ID
     * @returns Group name or null
     */
    function getExpenseGroupName(id: string) {
        if (!id) return null
        const group = expenseGroups.value.find(g => g.id === id)
        return group ? group.name : null
    }

    /**
     * Computed property for account dropdown options
     */
    const accountOptions = computed(() => {
        return accounts.value.map(a => ({ title: a.name, value: a.id }))
    })

    /**
     * Computed property for category dropdown options (flattened hierarchy)
     */
    const categoryOptions = computed(() => {
        const options: Array<{ title: string; value: string }> = []

        // Assuming categories.value is a flat list with parent_id/parent_name
        categories.value.forEach(cat => {
            if (!cat.parent_id) {
                // Top-level category
                options.push({ title: `${cat.icon || '🏷️'} ${cat.name}`, value: cat.name })

                // Add subcategories with parent prefix to ensure uniqueness in display
                const subcats = categories.value.filter(c => c.parent_id === cat.id)
                subcats.forEach(sub => {
                    options.push({
                        title: `　└ ${sub.icon || '🏷️'} ${cat.name} › ${sub.name}`,
                        value: `${cat.name} › ${sub.name}` // Unique value for subcategories
                    })
                })
            }
        })

        // Ensure Uncategorized is an option if not present
        return options
    })

    /**
     * Computed property for expense group dropdown options
     */
    const expenseGroupOptions = computed(() => {
        return expenseGroups.value.map(g => ({ title: g.name, value: g.id }))
    })

    /**
     * Generic sorting function for arrays
     * @param items - Array to sort
     * @param key - Property key to sort by
     * @param order - Sort order (asc/desc)
     * @returns Sorted array
     */
    function sortArray<T>(items: T[], key: string, order: 'asc' | 'desc') {
        return [...items].sort((a: any, b: any) => {
            // Handle nested keys safely
            const valA = key.split('.').reduce((o, i) => o?.[i], a)
            const valB = key.split('.').reduce((o, i) => o?.[i], b)

            let cmpA = valA
            let cmpB = valB

            // Special handling for date strings
            if (key === 'date' || key === 'created_at') {
                cmpA = new Date(valA || 0).getTime()
                cmpB = new Date(valB || 0).getTime()
            } else if (key === 'amount' || key === 'balance') {
                cmpA = Number(valA || 0)
                cmpB = Number(valB || 0)
            } else if (typeof valA === 'string') {
                cmpA = valA.toLowerCase()
                cmpB = (valB || '').toLowerCase()
            }

            if (cmpA < cmpB) return order === 'asc' ? -1 : 1
            if (cmpA > cmpB) return order === 'asc' ? 1 : -1
            return 0
        })
    }

    return {
        // Functions
        formatDate,
        formatTimeAgo,
        getAccountName,
        getCategoryDisplay,
        getExpenseGroupName,
        sortArray,

        // Computed
        accountOptions,
        categoryOptions,
        expenseGroupOptions
    }
}
