# WealthFam Product Backlog

## 🟢 UI/UX Enhancements
1. **Transactions List Polish**: Since category icons are already shown, remove the "Category Name" text from the Description column to reduce clutter. Show the name on hover via tooltip.
2. **Top Bar Alignment**: Fix vertical center alignment for all top bar contents (User profile, Member switcher, etc.).
3. **Skeleton Loaders**: Replace general spinners with standard `v-skeleton-loader` components across all data-heavy views (Portfolio, Transactions, Loans) for a smoother loading experience.
4. **Global Toast System**: Implement a standardized snackbar notification system to provide user feedback on API success/failure (e.g., "Transaction Saved", "Sync Failed").
5. **Budget Progress Visualization**: Add high-fidelity progress bars to `Budgets.vue` showing actual spend vs. limit with color coding (Green -> Yellow -> Red).

## 🟡 Technical Debt & Architecture
6. **Refactor `Transactions.vue`**: This file is currently >2.6k lines. Extract the "Transactions List", "Analytics", "Triage", and "Heatmap" into dedicated sub-components in `@/views/transactions/`.
7. **Mutual Fund Auto-Sync**: Implement a "Background Sync" status indicator and a manual "Refresh All" button in the Top Bar for Mutual Fund NAV updates.
8. **Reactivity Audit**: Deep audit of all props in `Settings.vue` sub-pages to ensure one-way data flow and proper event emission (Standardizing `v-model` usage).
9. **Data Caching Layer**: Implement a Pinia plugin or custom composable to cache frequently accessed data (like Portfolio and Transaction metadata) in `localStorage` to eliminate blank-state flashing.

## 🔵 New Feature Ideas
10. **Transaction KPIs**: In the transactions page header, show high-level summaries: **Total Expense**, **Total Income**, and **Net Worth Delta** (with options to toggle/view items excluded from reports).
11. **Loan Amortization Chart**: Add a visual breakdown of projected interest vs. principal payments over time in `LoanDetails.vue`.
12. **PWA Support**: Configure manifest and service workers to allow the app to be installed on mobile devices with a native look and feel.
13. **AI Rebalancing Assistant**: Expand the "Portfolio Intelligence" feature to suggest specific Buy/Sell quantities to achieve a target asset allocation.

## 🟣 Advanced Fintech Features (Long Term)
14. **Tax Planner (India Focused)**: Calculate Unrealized Capital Gains (LTCG/STCG) for the current portfolio to help with tax-harvesting decisions.
15. **Family Wealth Dashboard**: A high-level view that aggregates net worth across all family members, with permissions to hide/show specific accounts.
16. **Smart Rule Suggestion**: Implement a local analysis of uncategorized transactions to automatically suggest "Merchant -> Category" rules based on historical frequency.
17. **Goal-Based SIP Tracker**: Match specific SIP (Systematic Investment Plan) mandates from bank accounts to their corresponding Investment Goals.
18. **Document Vault**: A secure space to upload and link PDFs (Insurance policies, property deeds, tax returns) to specific family members or assets.
19. **Financial Health Score**: Create a proprietary "WealthFam Score" based on savings rate, emergency fund status, and debt-to-income ratios.
20. **Multi-Currency Support**: Allow tracking of offshore investments (e.g., US Stocks) with automatic exchange rate conversion.
## ⚪ Quality of Life & Reliability
22. **Data Export**: Add a "Export to CSV/Excel" button in the Transactions and Portfolio views for external accounting.
23. **Theme Switcher**: Implement a robust Dark/Light mode toggle in the Top Bar using Vuetify's theme system.
24. **Session Security**: Implement automatic session timeout and a "Logout from all devices" feature in `Settings.vue`.
25. **Automated Testing Suite**: Set up Vitest for unit testing core logic (e.g., currency formatting, portfolio aggregation) and Playwright for E2E testing of the "Add Transaction" flow.
26. **Global Search (Cmd+K)**: Implement a spotlight-style global search to quickly jump to specific funds, goals, or transactions from anywhere in the app.
