import { Building2, LandmarkIcon, ShieldCheck, Globe, Layers, Gem, Zap, CreditCard } from 'lucide-vue-next'

/**
 * Dashboard Helpers Composable
 * Contains Dashboard-specific presentation logic and utilities
 */
export function useDashboardHelpers() {
    /**
     * Get time-based greeting
     */
    function getGreeting() {
        const hour = new Date().getHours()
        if (hour < 12) return 'Good Morning'
        if (hour < 18) return 'Good Afternoon'
        return 'Good Evening'
    }

    /**
     * Get bank branding with rich visuals & icons
     * Returns gradient, logo, colors, and icon for a given bank name
     */
    function getBankBrand(name: string) {
        const n = name.toLowerCase()

        // HDFC: Classic Blue/Red split or Deep Blue
        if (n.includes('hdfc')) return {
            gradient: 'linear-gradient(135deg, #004a9e 0%, #002e63 100%)',
            logoColor: '#fff',
            logo: 'HDFC',
            textColor: 'rgba(255,255,255,0.9)',
            icon: Building2,
            color: '#004a9e'
        }

        // SBI: Teal/Blue signature
        if (n.includes('sbi')) return {
            gradient: 'linear-gradient(135deg, #2ea6dc 0%, #1e5c91 100%)',
            logoColor: '#fff',
            logo: 'SBI',
            textColor: 'rgba(255,255,255,0.95)',
            icon: LandmarkIcon,
            color: '#2ea6dc'
        }

        // ICICI: Orange branding
        if (n.includes('icici')) return {
            gradient: 'linear-gradient(135deg, #f58220 0%, #a84600 100%)',
            logoColor: '#fff',
            logo: 'ICICI',
            textColor: 'rgba(255,255,255,0.95)',
            icon: ShieldCheck,
            color: '#f58220'
        }

        // AMEX: Centurion/Royal styles
        if (n.includes('amex') || n.includes('american express')) return {
            gradient: 'linear-gradient(135deg, #006fcf 0%, #00264d 100%)',
            logoColor: '#fff',
            logo: 'AMEX',
            textColor: 'rgba(255,255,255,0.9)',
            icon: Globe,
            color: '#006fcf'
        }

        // AXIS: Burgundy
        if (n.includes('axis')) return {
            gradient: 'linear-gradient(135deg, #ae285d 0%, #5e0b2e 100%)',
            logoColor: '#fff',
            logo: 'AXIS',
            textColor: 'rgba(255,255,255,0.9)',
            icon: Layers,
            color: '#ae285d'
        }

        // KOTAK: Red
        if (n.includes('kotak')) return {
            gradient: 'linear-gradient(135deg, #ed1c24 0%, #990005 100%)',
            logoColor: '#fff',
            logo: 'KOTAK',
            textColor: 'rgba(255,255,255,0.95)',
            icon: Gem,
            color: '#ed1c24'
        }

        // ONECARD: Metal Black
        if (n.includes('onecard')) return {
            gradient: 'linear-gradient(135deg, #1a1a1a 0%, #000000 100%)',
            logoColor: '#fff',
            logo: 'One',
            textColor: 'rgba(255,255,255,0.9)',
            icon: Zap,
            color: '#1a1a1a'
        }

        // Default: Sleek Grey
        return {
            gradient: 'linear-gradient(135deg, #475569 0%, #1e293b 100%)',
            logoColor: '#fff',
            logo: 'CARD',
            textColor: 'rgba(255,255,255,0.8)',
            icon: CreditCard,
            color: '#64748b'
        }
    }

    return {
        getGreeting,
        getBankBrand
    }
}
