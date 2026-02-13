import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import { h } from 'vue'
import * as lucideIcons from 'lucide-vue-next'

/**
 * Custom Lucide Icon Set for Vuetify 3
 */
const lucide: any = {
    component: (props: any) => {
        const { icon, tag, ...rest } = props
        // Handle mdi- prefix by converting to PascalCase for Lucide
        // e.g. mdi-pencil -> Pencil, mdi-chevron-down -> ChevronDown
        let iconName = icon
        if (typeof icon === 'string' && icon.startsWith('mdi-')) {
            iconName = icon
                .replace('mdi-', '')
                .split('-')
                .map((word: string) => word.charAt(0).toUpperCase() + word.slice(1))
                .join('')
        }
        const iconComponent = (lucideIcons as any)[iconName]
        return iconComponent ? h(iconComponent, { ...rest }) : h('span', { class: 'mdi ' + icon })
    }
}

export default createVuetify({
    components,
    directives,
    icons: {
        defaultSet: 'lucide',
        sets: {
            lucide,
        },
        aliases: {
            // Map standard Vuetify internal icons to Lucide icons
            'collapse': 'ChevronUp',
            'complete': 'Check',
            'cancel': 'X',
            'close': 'X',
            'delete': 'Trash2',
            'clear': 'XCircle',
            'success': 'CheckCircle2',
            'info': 'Info',
            'warning': 'AlertTriangle',
            'error': 'AlertCircle',
            'prev': 'ChevronLeft',
            'next': 'ChevronRight',
            'checkboxOn': 'CheckSquare',
            'checkboxOff': 'Square',
            'checkboxIndeterminate': 'MinusSquare',
            'delimiter': 'Circle',
            'sort': 'ArrowUpDown',
            'sortAsc': 'SortAsc',
            'sortDesc': 'SortDesc',
            'expand': 'ChevronDown',
            'menu': 'Menu',
            'subgroup': 'ChevronDown',
            'dropdown': 'ChevronDown',
            'radioOn': 'CircleDot',
            'radioOff': 'Circle',
            'edit': 'Pencil',
            'ratingEmpty': 'Star',
            'ratingFull': 'Star',
            'ratingHalf': 'StarHalf',
            'loading': 'Loader2',
            'first': 'ChevronsLeft',
            'last': 'ChevronsRight',
            'unfold': 'ChevronsUpDown',
            'file': 'FileText',
            'plus': 'Plus',
            'minus': 'Minus',
        }
    },
    theme: {
        defaultTheme: 'wealthFamTheme',
        themes: {
            wealthFamTheme: {
                dark: false,
                colors: {
                    primary: '#4f46e5',
                    secondary: '#8b5cf6',
                    accent: '#0ea5e9',
                    error: '#ef4444',
                    info: '#3b82f6',
                    success: '#10b981',
                    warning: '#f59e0b',
                    background: '#f8fafc',
                    surface: '#ffffff',
                },
            },
            wealthFamDark: {
                dark: true,
                colors: {
                    primary: '#6366f1',
                    secondary: '#a78bfa',
                    accent: '#38bdf8',
                    error: '#f87171',
                    info: '#60a5fa',
                    success: '#34d399',
                    warning: '#fbbf24',
                    background: '#0f172a',
                    surface: '#1e293b',
                },
            },
        },
    },
})
