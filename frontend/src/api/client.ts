import axios, { type AxiosInstance } from 'axios'
import { useNotificationStore } from '@/stores/notification'

declare module 'axios' {
    export interface AxiosRequestConfig {
        skipNotification?: boolean;
    }
}

// Create Axios instance
const apiClient: AxiosInstance = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor for API calls
apiClient.interceptors.request.use(
    async (config) => {
        const token = localStorage.getItem('access_token')
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

// Response interceptor for API calls
apiClient.interceptors.response.use(
    (response) => {
        const method = response.config.method?.toLowerCase()
        if (['post', 'put', 'delete'].includes(method || '')) {
            // Show success for some non-GET requests if needed, 
            // but usually specific components handle success messages.
            // We'll focus on global error handling for now.
        }
        return response
    },
    async (error) => {
        const notification = useNotificationStore()

        // Handle 401 Unauthorized (e.g., token expired)
        if (error.response && error.response.status === 401) {
            // Clear token and redirect to login if not already there
            localStorage.removeItem('access_token')
            window.location.href = '/login'
            notification.error('Session expired. Please login again.')
        } else if (error.response) {
            // Check for skipNotification in the config
            // Axios 1.x uses error.config, but we also check error.response.config for safety
            const config = error.config || error.response.config
            if (config?.skipNotification) {
                return Promise.reject(error)
            }

            const message = error.response.data?.detail || error.response.data?.message || 'Server error occurred'
            notification.error(message)
        } else {
            notification.error('Network error or server unreachable')
        }
        return Promise.reject(error)
    }
)

export default apiClient

export interface AccountCreate {
    name: string;
    type: string;
    currency: string;
    account_mask?: string;
    balance?: number;

}

export interface AccountUpdate {
    name?: string;
    type?: string;
    currency?: string;
    account_mask?: string;
    import_config?: string;
}

export interface TransactionUpdate {
    description?: string;
    recipient?: string;
    category?: string;
    amount?: number;
    date?: string;
    account_id?: string;
    is_transfer?: boolean;
    to_account_id?: string;
    linked_transaction_id?: string;
    exclude_from_reports?: boolean;
    is_emi?: boolean;
    loan_id?: string;
    expense_group_id?: string;
}

export const financeApi = {
    getAccounts: (userId?: string, includeUnverified?: boolean) => apiClient.get('/finance/accounts', { params: { user_id: userId, include_unverified: includeUnverified } }),
    globalSearch: (q: string, userId?: string) => apiClient.get('/finance/search', { params: { q, user_id: userId } }),
    createAccount: (data: AccountCreate) => apiClient.post('/finance/accounts', data),
    updateAccount: (id: string, data: AccountUpdate) => apiClient.put(`/finance/accounts/${id}`, data),
    deleteAccount: (id: string) => apiClient.delete(`/finance/accounts/${id}`),
    getAccountTransactionCount: (id: string) => apiClient.get(`/finance/accounts/${id}/transaction-count`),
    overrideAccountBalance: (id: string, data: { balance: number, credit_limit?: number | null, timestamp: string, source?: string }) =>
        apiClient.put(`/finance/accounts/${id}/balance`, { ...data, account_id: id }),
    getTransactions: (accountId?: string, page: number = 1, limit: number = 50, startDate?: string, endDate?: string, search?: string, category?: string, sortBy: string = 'date', sortOrder: string = 'desc', userId?: string) =>
        apiClient.get('/finance/transactions', { params: { account_id: accountId, page, limit, start_date: startDate, end_date: endDate, search, category, sort_by: sortBy, sort_order: sortOrder, user_id: userId } }),
    searchTransactions: (q: string, limit: number = 10) =>
        apiClient.get('/finance/transactions', { params: { search: q, limit, page: 1, sort_by: 'date', sort_order: 'desc' } }),
    createTransaction: (data: any) => apiClient.post('/finance/transactions', data),
    updateTransaction: (id: string, data: TransactionUpdate) => apiClient.put(`/finance/transactions/${id}`, data),
    smartCategorize: (data: { transaction_id: string, category: string, create_rule: boolean, apply_to_similar: boolean, exclude_from_reports?: boolean }) =>
        apiClient.post('/finance/transactions/smart-categorize', data),
    bulkDeleteTransactions: (ids: string[]) => apiClient.post('/finance/transactions/bulk-delete', { transaction_ids: ids }),
    getMetrics: (accountId?: string, startDate?: string, endDate?: string, userId?: string) => apiClient.get('/finance/analytics/metrics', { params: { account_id: accountId, start_date: startDate, end_date: endDate, user_id: userId } }),
    getDetailedAnalytics: (accountId?: string, startDate?: string, endDate?: string, userId?: string, category?: string) => apiClient.get('/finance/analytics/detailed', { params: { account_id: accountId, start_date: startDate, end_date: endDate, user_id: userId, category } }),
    getRules: () => apiClient.get('/finance/rules'),
    getRuleSuggestions: () => apiClient.get('/finance/rules/suggestions'),
    createRule: (data: any) => apiClient.post('/finance/rules', data),
    ignoreSuggestion: (data: { pattern: string }) => apiClient.post('/finance/rules/suggestions/ignore', data),
    updateRule: (id: string, data: any) => apiClient.put(`/finance/rules/${id}`, data),
    deleteRule: (id: string) => apiClient.delete(`/finance/rules/${id}`),
    applyRuleRetrospectively: (id: string, override: boolean = false) => apiClient.post(`/finance/transactions/rules/${id}/apply-retrospective`, null, { params: { override } }),
    getMatchCount: (keywords: string[], onlyUncategorized: boolean = true) => apiClient.post('/finance/transactions/match-count', { keywords, only_uncategorized: onlyUncategorized }),
    getMatchPreview: (keywords: string[], onlyUncategorized: boolean = true, page: number = 1, limit: number = 5) => apiClient.post('/finance/transactions/match-preview', { keywords, only_uncategorized: onlyUncategorized }, { params: { page, limit } }),
    bulkRename: (old_name: string, new_name: string, sync_to_parser: boolean) => apiClient.post('/finance/transactions/bulk-rename', { old_name, new_name, sync_to_parser }),
    importRules: (data: any[]) => apiClient.post('/finance/rules/import', data),
    exportRules: () => apiClient.get<any[]>('/finance/rules/export'),

    getCategories: (tree: boolean = false) => apiClient.get('/finance/categories', { params: { tree } }),
    createCategory: (data: any) => apiClient.post('/finance/categories', data),
    updateCategory: (id: string, data: any) => apiClient.put(`/finance/categories/${id}`, data),
    deleteCategory: (id: string) => apiClient.delete(`/finance/categories/${id}`),
    importCategories: (data: any[]) => apiClient.post('/finance/categories/import', data),
    exportCategories: () => apiClient.get<any[]>('/finance/categories/export'),

    getExpenseGroups: (userId?: string) => apiClient.get('/finance/expense-groups', { params: { user_id: userId } }),
    createExpenseGroup: (data: any) => apiClient.post('/finance/expense-groups', data),
    updateExpenseGroup: (id: string, data: any) => apiClient.put(`/finance/expense-groups/${id}`, data),
    deleteExpenseGroup: (id: string) => apiClient.delete(`/finance/expense-groups/${id}`),
    linkExpenseGroupTransactions: (groupId: string, transactionIds: string[]) => apiClient.post(`/finance/expense-groups/${groupId}/transactions`, { transaction_ids: transactionIds }),

    getBudgets: (year?: number, month?: number, userId?: string) => apiClient.get('/finance/budgets', { params: { year, month, user_id: userId } }),
    getBudgetOverview: (year?: number, month?: number, userId?: string) => apiClient.get('/finance/budgets/overview', { params: { year, month, user_id: userId } }),
    getBudgetsInsights: (year?: number, month?: number, userId?: string, forceRefresh?: boolean) => apiClient.get('/finance/budgets/insights', { params: { year, month, user_id: userId, force_refresh: forceRefresh } }),
    setBudget: (data: any) => apiClient.post('/finance/budgets', data),
    deleteBudget: (id: string) => apiClient.delete(`/finance/budgets/${id}`),
    getVendorStats: (vendorName: string, skip: number = 0, limit: number = 10) => apiClient.get('/finance/transactions/stats/vendor', { params: { vendor_name: vendorName, skip, limit } }),

    // Recurring Transactions
    getRecurringTransactions: (userId?: string) => apiClient.get('/finance/recurring', { params: { user_id: userId } }),
    createRecurringTransaction: (data: any) => apiClient.post('/finance/recurring', data),
    updateRecurring: (id: string, data: any) => apiClient.put(`/finance/recurring/${id}`, data),
    deleteRecurring: (id: string) => apiClient.delete(`/finance/recurring/${id}`),
    processRecurring: () => apiClient.post('/finance/recurring/process'),
    getForecast: (accountId?: string, days: number = 30, userId?: string) =>
        apiClient.get('/finance/analytics/forecast', { params: { account_id: accountId, days, user_id: userId } }),
    getNetWorthTimeline: (days: number = 30, userId?: string) =>
        apiClient.get('/finance/analytics/net-worth-timeline', { params: { days, user_id: userId } }),
    getSpendingTrend: (userId?: string) =>
        apiClient.get('/finance/analytics/spending-trend', { params: { user_id: userId } }),
    getSpendingForecast: (startDate?: string, endDate?: string, userId?: string) =>
        apiClient.get('/finance/analytics/spending-forecast', { params: { start_date: startDate, end_date: endDate, user_id: userId } }),
    getBudgetHistory: (months: number = 6, userId?: string) =>
        apiClient.get('/finance/analytics/budget-history', { params: { months, user_id: userId } }),
    getHeatmapData: (startDate?: string, endDate?: string, userId?: string) =>
        apiClient.get('/finance/analytics/heatmap', { params: { start_date: startDate, end_date: endDate, user_id: userId } }),
    getMerchantBreakdown: (category?: string, startDate?: string, endDate?: string, userId?: string) =>
        apiClient.get('/finance/analytics/merchant-breakdown', { params: { category, start_date: startDate, end_date: endDate, user_id: userId } }),
    getFamilyWealth: () => apiClient.get('/finance/analytics/family-wealth'),
    getRecurringSuggestions: () => apiClient.get('/finance/recurring/suggestions'),
    ignoreRecurringSuggestion: (pattern: string) => apiClient.post('/finance/recurring/suggestions/ignore', { pattern }),

    // Document Vault
    uploadDocument: (formData: FormData) => apiClient.post('/finance/vault/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    uploadVersion: (id: string, formData: FormData) => apiClient.post(`/finance/vault/${id}/version`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    createFolder: (formData: FormData) => apiClient.post('/finance/vault/folders', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    getDocuments: (params?: { transaction_id?: string, parent_id?: string, file_type?: string, search?: string, skip?: number, limit?: number }) =>
        apiClient.get('/finance/vault', { params }),
    updateDocument: (id: string, formData: FormData) => apiClient.put(`/finance/vault/${id}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    listVersions: (id: string) => apiClient.get(`/finance/vault/${id}/versions`),
    deleteDocument: (id: string) => apiClient.delete(`/finance/vault/${id}`),
    linkDocToTransaction: (docId: string, transactionId: string | null) =>
        apiClient.patch(`/finance/vault/${docId}/link-transaction`, { transaction_id: transactionId }),
    syncVault: () => apiClient.post('/finance/vault/sync'),
    getDocument: (id: string) => apiClient.get(`/finance/vault/${id}`),

    getDocumentDownloadUrl: (id: string, version?: number) => {
        const token = localStorage.getItem('access_token')
        let url = `${apiClient.defaults.baseURL}/finance/vault/${id}/download?token=${token}`
        if (version) url += `&version=${version}`
        return url
    },
    getDocumentViewUrl: (id: string, version?: number) => {
        const token = localStorage.getItem('access_token')
        let url = `${apiClient.defaults.baseURL}/finance/vault/${id}/view?token=${token}`
        if (version) url += `&version=${version}`
        return url
    },
    getDocumentThumbnailUrl: (id: string, version?: number) => {
        const token = localStorage.getItem('access_token')
        let url = `${apiClient.defaults.baseURL}/finance/vault/${id}/thumbnail?token=${token}`
        if (version) url += `&version=${version}`
        return url
    },
    getDocumentBlob: (id: string, version?: number) => {
        let url = `/finance/vault/${id}/view`
        if (version) url += `?version=${version}`
        return apiClient.get(url, { responseType: 'blob' })
    },
    getVaultSettings: () => apiClient.get('/finance/vault/settings'),
    saveVaultSettings: (credentials_json: string) => apiClient.post('/finance/vault/settings', { credentials_json }),
    clearVaultSettings: () => apiClient.delete('/finance/vault/settings'),
    testVaultConnection: () => apiClient.post('/finance/vault/settings/test'),
    getVaultAuthUrl: (client_id: string, client_secret: string) =>
        apiClient.post('/finance/vault/settings/auth-url', { client_id, client_secret }),
    exchangeVaultCode: (code: string) =>
        apiClient.post('/finance/vault/settings/callback', { code }),
    getVaultHistory: (limit: number = 10) => apiClient.get('/finance/vault/history', { params: { limit } }),

    // Ingestion
    analyzeCsv: (formData: FormData) => apiClient.post('/ingestion/csv/analyze', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    parseCsv: (formData: FormData) => apiClient.post('/ingestion/csv/parse', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    importCsv: (data: any) => apiClient.post('/ingestion/csv/import', data),

    // Email Automations
    getEmailConfigs: () => apiClient.get('/ingestion/email/configs'),
    createEmailConfig: (data: any) => apiClient.post('/ingestion/email/configs', data),
    deleteEmailConfig: (id: string) => apiClient.delete(`/ingestion/email/configs/${id}`),
    updateEmailConfig: (id: string, data: any) => apiClient.put(`/ingestion/email/configs/${id}`, data),
    getEmailSyncLogs: (id: string) => apiClient.get(`/ingestion/email/configs/${id}/logs`),
    syncEmailConfig: (id: string) => apiClient.post(`/ingestion/email/sync/${id}`),

    // Tenants / Management
    getTenants: () => apiClient.get('/auth/tenants'),
    updateTenant: (id: string, data: any) => apiClient.put(`/auth/tenants/${id}`, data),
    logoutAll: () => apiClient.post('/auth/logout-all'),

    // Triage & Training
    getTriage: (params?: { limit?: number, skip?: number, sort_by?: string, sort_order?: string }) => apiClient.get('/ingestion/triage', { params }),
    approveTriage: (id: string, data: { category?: string, is_transfer?: boolean, to_account_id?: string, create_rule?: boolean, exclude_from_reports?: boolean }) => apiClient.post(`/ingestion/triage/${id}/approve`, data),
    rejectTriage: (id: string, createIgnoreRule: boolean = false) => apiClient.delete(`/ingestion/triage/${id}`, { params: { create_ignore_rule: createIgnoreRule } }),
    bulkRejectTriage: (ids: string[], createIgnoreRules: boolean = false) => apiClient.post('/ingestion/triage/bulk-reject', { pending_ids: ids, create_ignore_rules: createIgnoreRules }),
    getTraining: (params?: any) => apiClient.get('/ingestion/training', { params }),
    labelMessage: (id: string, data: any) => apiClient.post(`/ingestion/training/${id}/label`, data),
    dismissTrainingMessage: (id: string, createRule: boolean = false) => apiClient.post(`/ingestion/training/${id}/dismiss`, { create_rule: createRule }),
    bulkDismissTraining: (ids: string[], createRule: boolean = false) => apiClient.post('/ingestion/training/bulk-dismiss', { ids, create_rule: createRule }),
    markAsSpam: (id: string) => apiClient.post(`/ingestion/training/${id}/mark-as-spam`),
    getSpamFilters: async (params?: { limit?: number, skip?: number }) => {
        const response = await apiClient.get('/ingestion/training/spam', { params })
        return response.data.data // Extract array from envelope
    },
    deleteSpamFilter: (id: string) => apiClient.delete(`/ingestion/training/spam/${id}`),
    syncAiToParser: () => apiClient.post('/ingestion/ai/sync-to-parser'),
    getIngestionEvents: (params?: { limit?: number, skip?: number, device_id?: string }) => apiClient.get('/ingestion/events', { params }),
    bulkDeleteEvents: (ids: string[]) => apiClient.post('/ingestion/events/bulk-delete', { event_ids: ids }),
    getEmailLogs: (params?: { limit?: number, skip?: number, config_id?: string }) => apiClient.get('/ingestion/email/logs', { params }),

    // User Management
    getMe: () => apiClient.get<any>('/auth/me'),
    getUsers: () => apiClient.get<any[]>('/auth/users'),
    createUser: (data: any) => apiClient.post('/auth/users', data),
    updateUser: (id: string, data: any) => apiClient.put(`/auth/users/${id}`, data),

    // Mutual Funds
    searchFunds: (query?: string, category?: string, amc?: string, limit: number = 20, offset: number = 0, sortBy: string = 'relevance') =>
        apiClient.get('/finance/mutual-funds/search', { params: { q: query, category, amc, limit, offset, sort_by: sortBy } }),

    getMarketIndices: () => apiClient.get('/finance/mutual-funds/indices'),
    getPortfolio: (userId?: string) => apiClient.get('/finance/mutual-funds/portfolio', { params: { user_id: userId } }),
    getMutualFundSyncStatus: () => apiClient.get('/finance/mutual-funds/sync/status'),
    triggerMutualFundSync: () => apiClient.post('/finance/mutual-funds/sync/refresh'),
    getHoldingDetails: (id: string) => apiClient.get(`/finance/mutual-funds/holdings/${id}`),
    getSchemeDetails: (schemeCode: string) => apiClient.get(`/finance/mutual-funds/schemes/${schemeCode}/details`),
    getSchemeInfo: (schemeCode: string) => apiClient.get(`/finance/mutual-funds/schemes/${schemeCode}/info`),
    updateHolding: (id: string, data: any) => apiClient.patch(`/finance/mutual-funds/holdings/${id}`, data),
    getAnalytics: (userId?: string) => apiClient.get('/finance/mutual-funds/analytics', { params: { user_id: userId } }),
    getPerformanceTimeline: (period: string = '1y', granularity: string = '1w', userId?: string, schemeCode?: string, holdingId?: string) =>
        apiClient.get('/finance/mutual-funds/analytics/performance-timeline', { params: { period, granularity, user_id: userId, scheme_code: schemeCode, holding_id: holdingId } }),
    deleteCacheTimeline: () => apiClient.delete('/finance/mutual-funds/analytics/cache'),
    cleanupDuplicateOrders: () => apiClient.post('/finance/mutual-funds/cleanup-duplicates'),
    createFundTransaction: (data: any) => apiClient.post('/finance/mutual-funds/transaction', data),
    delete: (url: string) => apiClient.delete(url), // Generic delete helper or specific method
    deleteHolding: (id: string) => apiClient.delete(`/finance/mutual-funds/holdings/${id}`),
    importCAS: (formData: FormData) => apiClient.post('/finance/mutual-funds/import-cas', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    importCASEmail: (formData: FormData) => apiClient.post('/finance/mutual-funds/import-cas-email', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    previewCAS: (formData: FormData) => apiClient.post('/finance/mutual-funds/preview-cas-pdf', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    previewCASEmail: (formData: FormData) => apiClient.post('/finance/mutual-funds/preview-cas-email', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    }),
    confirmImport: (transactions: any[], userId?: string) => apiClient.post('/finance/mutual-funds/confirm-import', transactions, {
        params: { user_id: userId }
    }),
    getNav: (schemeCode: string) => apiClient.get(`/finance/mutual-funds/${schemeCode}/nav`),
    getLoans: (userId?: string) => apiClient.get('/finance/loans', { params: { user_id: userId } }),
    getLoanDetails: (id: string) => apiClient.get(`/finance/loans/${id}`),
    getLoanInsights: (id: string) => apiClient.post(`/finance/loans/${id}/insights`, {}),
    getPortfolioInsights: (userId?: string) => apiClient.post('/finance/loans/portfolio/insights', {}, { params: { user_id: userId } }),
    createLoan: (data: any) => apiClient.post('/finance/loans', data),
    recordLoanRepayment: (loanId: string, data: any) => apiClient.post(`/finance/loans/${loanId}/repayment`, data),

    // Merchant Aliases
    getAliases: () => apiClient.get('/ingestion/aliases'),
    createAlias: (data: any) => apiClient.post('/ingestion/aliases', data),
    updateAlias: (id: string, data: any) => apiClient.put(`/ingestion/aliases/${id}`, data),
    deleteAlias: (id: string) => apiClient.delete(`/ingestion/aliases/${id}`),
    previewAliasImpact: (pattern: string) => apiClient.post('/ingestion/aliases/preview', { pattern }),

    // Investment Goals
    getInvestmentGoals: (userId?: string) => apiClient.get('/finance/investment-goals', { params: { user_id: userId } }),
    createInvestmentGoal: (data: any) => apiClient.post('/finance/investment-goals', data),
    updateInvestmentGoal: (id: string, data: any) => apiClient.put(`/finance/investment-goals/${id}`, data),
    deleteInvestmentGoal: (id: string) => apiClient.delete(`/finance/investment-goals/${id}`),
    linkHoldingToGoal: (goalId: string, holdingId: string) => apiClient.post(`/finance/investment-goals/${goalId}/holdings/${holdingId}`),
    unlinkHoldingFromGoal: (goalId: string, holdingId: string) => apiClient.delete(`/finance/investment-goals/${goalId}/holdings/${holdingId}`),
    addGoalAsset: (goalId: string, data: any) => apiClient.post(`/finance/investment-goals/${goalId}/assets`, data),
    removeGoalAsset: (assetId: string) => apiClient.delete(`/finance/investment-goals/assets/${assetId}`),
}

const parserClient = axios.create({
    baseURL: import.meta.env.VITE_PARSER_API_URL || '/parser',
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor for Parser calls
parserClient.interceptors.request.use(
    async (config) => {
        const token = localStorage.getItem('access_token')
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

export const parserApi = {
    getHealth: () => parserClient.get('/health'),
    getStats: () => parserClient.get('/stats'),
    getLogs: (params?: { limit?: number, offset?: number, source?: string, status?: string }) =>
        parserClient.get('/logs', { params }),
    getLogDetail: (id: string) => parserClient.get(`/logs/${id}`),
    getAiConfig: () => parserClient.get('/config/ai'),
    updateAiConfig: (data: any) => parserClient.post('/config/ai', data),
    getAliases: () => parserClient.get('/config/aliases'),
    createAlias: (pattern: string, alias: string) => parserClient.post('/config/aliases', { pattern, alias }),
    deleteAlias: (id: string) => parserClient.delete(`/config/aliases/${id}`),
    getPatterns: (params?: { limit?: number, skip?: number }) => parserClient.get('/patterns', { params }),
    createPattern: (data: any) => parserClient.post('/patterns', data),
    updatePattern: (id: string, data: any) => parserClient.put(`/patterns/${id}`, data),
    deletePattern: (id: string) => parserClient.delete(`/patterns/${id}`),
}

export const aiApi = {
    getSettings: () => apiClient.get('/ingestion/ai/settings'),
    updateSettings: (data: any) => apiClient.post('/ingestion/ai/settings', data),
    testConnection: (content: string) => apiClient.post('/ingestion/ai/test', { content }),
    listModels: (provider: string, apiKey?: string) => apiClient.get('/ingestion/ai/models', { params: { provider, api_key: apiKey } }),
    generateSummaryInsights: (summary_data: any) => apiClient.post('/ingestion/ai/generate-insights', { summary_data }, { skipNotification: true }),
    getAliases: () => apiClient.get('/ingestion/ai/aliases'),
    createAlias: (pattern: string, alias: string) => apiClient.post('/ingestion/ai/aliases', { pattern, alias }),
    deleteAlias: (id: string) => apiClient.delete(`/ingestion/ai/aliases/${id}`),
    autoParseTrainingMessage: (id: string) => apiClient.post(`/ingestion/ai/training/${id}/auto-parse`)
}

export const mobileApi = {
    getDevices: () => apiClient.get('/mobile/devices'),
    toggleApproval: (id: string, is_approved: boolean) => apiClient.patch(`/mobile/devices/${id}/approve`, { is_approved }),
    toggleEnabled: (id: string, is_enabled: boolean) => apiClient.patch(`/mobile/devices/${id}/enable`, null, { params: { enabled: is_enabled } }),
    toggleIgnored: (id: string, is_ignored: boolean) => apiClient.patch(`/mobile/devices/${id}/ignore`, null, { params: { ignored: is_ignored } }),
    assignUser: (id: string, userId: string | null) => apiClient.patch(`/mobile/devices/${id}/assign`, { user_id: userId }),
    updateDevice: (id: string, data: { device_name?: string, is_enabled?: boolean, is_ignored?: boolean, user_id?: string | null }) =>
        apiClient.patch(`/mobile/devices/${id}`, data),
    testNotification: (id: string) => apiClient.post(`/mobile/devices/${id}/test-notification`),
    deleteDevice: (id: string) => apiClient.delete(`/mobile/devices/${id}`),
    getAlerts: () => apiClient.get<any[]>('/mobile/alerts'),
}
