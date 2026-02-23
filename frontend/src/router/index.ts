import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

import Dashboard from '@/views/Dashboard.vue'
import Login from '@/views/Login.vue'
import Register from '@/views/Register.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: Dashboard,
      meta: { requiresAuth: true }
    },
    {
      path: '/transactions',
      name: 'transactions',
      component: () => import('@/views/Transactions.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/budgets',
      name: 'budgets',
      component: () => import('@/views/Budgets.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/insights',
      name: 'insights',
      component: () => import('@/views/Insights.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/vault',
      name: 'vault',
      component: () => import('@/views/Vault.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/mutual-funds',
      name: 'mutual-funds',
      component: () => import('@/views/MutualFunds.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/mutual-funds/explore/:id',
      name: 'explore-fund',
      component: () => import('@/views/ExploreFund.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/mutual-funds/:id',
      name: 'fund-details',
      component: () => import('@/views/FundDetails.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/loans',
      name: 'loans',
      component: () => import('@/views/Loans.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/loans/:id',
      name: 'loan-details',
      component: () => import('@/views/LoanDetails.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/Settings.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/views/Categories.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/expense-groups',
      name: 'expense-groups',
      component: () => import('@/views/ExpenseGroups.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/investment-goals',
      name: 'investment-goals',
      component: () => import('@/views/InvestmentGoals.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/merchants/:id',
      name: 'merchant-details',
      component: () => import('@/views/MerchantDetails.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { guest: true }
    },
    {
      path: '/register',
      name: 'register',
      component: Register,
      meta: { guest: true }
    }
  ]
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next('/login')
  } else if (to.meta.guest && authStore.isAuthenticated) {
    next('/')
  } else {
    next()
  }
})

export default router
