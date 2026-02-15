import {
    ShoppingBag,
    Utensils,
    Home,
    Car,
    Zap,
    HeartPulse,
    Tv,
    Layers,
    Coffee,
    Smartphone,
    CreditCard,
    DollarSign,
    TrendingUp,
    Shield,
    Briefcase,
    Gift,
    ArrowRightLeft,
    Tag
} from 'lucide-vue-next'

const iconMap: Record<string, any> = {
    'Shopping': ShoppingBag,
    'Food': Utensils,
    'Dining': Utensils,
    'Housing': Home,
    'Rent': Home,
    'Transport': Car,
    'Travel': Car,
    'Utilities': Zap,
    'Bills': Zap,
    'Health': HeartPulse,
    'Medical': HeartPulse,
    'Entertainment': Tv,
    'Education': Layers,
    'Food & Drink': Coffee,
    'Electronics': Smartphone,
    'Subscription': CreditCard,
    'Investment': TrendingUp,
    'Income': DollarSign,
    'Salary': DollarSign,
    'Insurance': Shield,
    'Business': Briefcase,
    'Gift': Gift,
    'Transfer': ArrowRightLeft,
    'Uncategorized': Tag
}

/**
 * Returns the Lucide icon component for a given category name.
 * Falls back to Tag icon if not found.
 */
export function getCategoryLucideIcon(categoryName: string) {
    if (!categoryName) return Tag

    // Check direct match
    if (iconMap[categoryName]) return iconMap[categoryName]

    // Check partial case-insensitive match
    const lowerName = categoryName.toLowerCase()
    const match = Object.keys(iconMap).find(k =>
        lowerName.includes(k.toLowerCase()) || k.toLowerCase().includes(lowerName)
    )

    return match ? iconMap[match] : Tag
}
