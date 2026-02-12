import axios, { type AxiosInstance } from 'axios'

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
    (response) => response,
    async (error) => {
        // Handle 401 Unauthorized (e.g., token expired)
        if (error.response && error.response.status === 401) {
            // Clear token and redirect to login if not already there
            localStorage.removeItem('access_token')
            window.location.href = '/login'
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
    category?: string;
    amount?: number;
    date?: string;
    is_transfer?: boolean;
    to_account_id?: string;
    exclude_from_reports?: boolean;
}

export const financeApi = {
    getAccounts: (userId?: string) => apiClient.get('/finance/accounts', { params: { user_id: userId } }),
    createAccount: (data: AccountCreate) => apiClient.post('/finance/accounts', data),
    updateAccount: (id: string, data: AccountUpdate) => apiClient.put(`/finance/accounts/${id}`, data),
    deleteAccount: (id: string) => apiClient.delete(`/finance/accounts/${id}`),
    getAccountTransactionCount: (id: string) => apiClient.get(`/finance/accounts/${id}/transaction-count`),
    getTransactions: (accountId?: string, page: number = 1, limit: number = 50, startDate?: string, endDate?: string, search?: string, category?: string, sortBy: string = 'date', sortOrder: string = 'desc', userId?: string) =>
        apiClient.get('/finance/transactions', { params: { account_id: accountId, page, limit, start_date: startDate, end_date: endDate, search, category, sort_by: sortBy, sort_order: sortOrder, user_id: userId } }),
    createTransaction: (data: any) => apiClient.post('/finance/transactions', data),
    updateTransaction: (id: string, data: TransactionUpdate) => apiClient.put(`/finance/transactions/${id}`, data),
    smartCategorize: (data: { transaction_id: string, category: string, create_rule: boolean, apply_to_similar: boolean, exclude_from_reports?: boolean }) =>
        apiClient.post('/finance/transactions/smart-categorize', data),
    bulkDeleteTransactions: (ids: string[]) => apiClient.post('/finance/transactions/bulk-delete', { transaction_ids: ids }),
    getMetrics: (accountId?: string, startDate?: string, endDate?: string, userId?: string) =>
        apiClient.get('/finance/metrics', { params: { account_id: accountId, start_date: startDate, end_date: endDate, user_id: userId } }),
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

    getExpenseGroups: () => apiClient.get('/finance/expense-groups'),
    createExpenseGroup: (data: any) => apiClient.post('/finance/expense-groups', data),
    updateExpenseGroup: (id: string, data: any) => apiClient.put(`/finance/expense-groups/${id}`, data),
    deleteExpenseGroup: (id: string) => apiClient.delete(`/finance/expense-groups/${id}`),

    getBudgets: (year?: number, month?: number, userId?: string) => apiClient.get('/finance/budgets', { params: { year, month, user_id: userId } }),
    getBudgetOverview: (year?: number, month?: number, userId?: string) => apiClient.get('/finance/budgets/overview', { params: { year, month, user_id: userId } }),
    getBudgetsInsights: (year?: number, month?: number, userId?: string) => apiClient.get('/finance/budgets/insights', { params: { year, month, user_id: userId } }),
    setBudget: (data: any) => apiClient.post('/finance/budgets', data),
    deleteBudget: (id: string) => apiClient.delete(`/finance/budgets/${id}`),

    // Recurring Transactions
    getRecurringTransactions: (userId?: string) => apiClient.get('/finance/recurring', { params: { user_id: userId } }),
    createRecurringTransaction: (data: any) => apiClient.post('/finance/recurring', data),
    updateRecurring: (id: string, data: any) => apiClient.put(`/finance/recurring/${id}`, data),
    deleteRecurring: (id: string) => apiClient.delete(`/finance/recurring/${id}`),
    processRecurring: () => apiClient.post('/finance/recurring/process'),
    getForecast: (accountId?: string, days: number = 30, userId?: string) =>
        apiClient.get('/finance/forecast', { params: { account_id: accountId, days, user_id: userId } }),
    getNetWorthTimeline: (days: number = 30, userId?: string) =>
        apiClient.get('/finance/net-worth-timeline', { params: { days, user_id: userId } }),
    getSpendingTrend: (userId?: string) =>
        apiClient.get('/finance/spending-trend', { params: { user_id: userId } }),
    getBudgetHistory: (months: number = 6, userId?: string) =>
        apiClient.get('/finance/budget-history', { params: { months, user_id: userId } }),
    getHeatmapData: (startDate?: string, endDate?: string, userId?: string) =>
        apiClient.get('/finance/heatmap', { params: { start_date: startDate, end_date: endDate, user_id: userId } }),

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

    // Triage & Training
    getTriage: (params?: { limit?: number, skip?: number, sort_by?: string, sort_order?: string }) => apiClient.get('/ingestion/triage', { params }),
    approveTriage: (id: string, data: { category?: string, is_transfer?: boolean, to_account_id?: string, create_rule?: boolean, exclude_from_reports?: boolean }) => apiClient.post(`/ingestion/triage/${id}/approve`, data),
    rejectTriage: (id: string, createIgnoreRule: boolean = false) => apiClient.delete(`/ingestion/triage/${id}`, { params: { create_ignore_rule: createIgnoreRule } }),
    bulkRejectTriage: (ids: string[], createIgnoreRules: boolean = false) => apiClient.post('/ingestion/triage/bulk-reject', { pending_ids: ids, create_ignore_rules: createIgnoreRules }),
    getTraining: (params?: { limit?: number, skip?: number }) => apiClient.get('/ingestion/training', { params }),
    labelMessage: (id: string, data: any) => apiClient.post(`/ingestion/training/${id}/label`, data),
    dismissTrainingMessage: (id: string, createIgnoreRule: boolean = false) => apiClient.delete(`/ingestion/training/${id}`, { params: { create_ignore_rule: createIgnoreRule } }),
    bulkDismissTraining: (ids: string[], createIgnoreRules: boolean = false) => apiClient.post('/ingestion/training/bulk-dismiss', { message_ids: ids, create_ignore_rules: createIgnoreRules }),
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
    getHoldingDetails: (id: string) => apiClient.get(`/finance/mutual-funds/holdings/${id}`),
    getSchemeDetails: (schemeCode: string) => apiClient.get(`/finance/mutual-funds/schemes/${schemeCode}/details`),
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

// Parser Microservice API (Port 8001)
const parserClient = axios.create({
    baseURL: import.meta.env.VITE_PARSER_API_URL || '/parser',
    headers: {
        'Content-Type': 'application/json',
    },
})

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
    getPatterns: () => parserClient.get('/config/patterns'),
    createPattern: (data: any) => parserClient.post('/config/patterns', data),
    deletePattern: (id: string) => parserClient.delete(`/config/patterns/${id}`),
}

export const aiApi = {
    getSettings: () => apiClient.get('/ingestion/ai/settings'),
    updateSettings: (data: any) => apiClient.post('/ingestion/ai/settings', data),
    testConnection: (content: string) => apiClient.post('/ingestion/ai/test', { content }),
    listModels: (provider: string, apiKey?: string) => apiClient.get('/ingestion/ai/models', { params: { provider, api_key: apiKey } }),
    generateSummaryInsights: (summary_data: any) => apiClient.post('/ingestion/ai/generate-insights', { summary_data }),
    getAliases: () => apiClient.get('/ingestion/ai/aliases'),
    createAlias: (pattern: string, alias: string) => apiClient.post('/ingestion/ai/aliases', { pattern, alias }),
    deleteAlias: (id: string) => apiClient.delete(`/ingestion/ai/aliases/${id}`)
}

export const mobileApi = {
    getDevices: () => apiClient.get('/mobile/devices'),
    toggleApproval: (id: string, is_approved: boolean) => apiClient.patch(`/mobile/devices/${id}/approve`, { is_approved }),
    toggleEnabled: (id: string, is_enabled: boolean) => apiClient.patch(`/mobile/devices/${id}/enable`, null, { params: { enabled: is_enabled } }),
    toggleIgnored: (id: string, is_ignored: boolean) => apiClient.patch(`/mobile/devices/${id}/ignore`, null, { params: { ignored: is_ignored } }),
    assignUser: (id: string, userId: string | null) => apiClient.patch(`/mobile/devices/${id}/assign`, { user_id: userId }),
    updateDevice: (id: string, data: { device_name?: string, is_enabled?: boolean, is_ignored?: boolean, user_id?: string | null }) =>
        apiClient.patch(`/mobile/devices/${id}`, data),
    deleteDevice: (id: string) => apiClient.delete(`/mobile/devices/${id}`)
}
