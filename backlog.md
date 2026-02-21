# WealthFam Product Backlog

## 🟢 UI/UX Enhancements
*No active tasks.*

## 🟡 Technical Debt & Architecture
1. **Refactor `Transactions.vue`**: This file is currently >2.6k lines. Extract the "Transactions List", "Analytics", "Triage", and "Heatmap" into dedicated sub-components in `@/views/transactions/`.
2. **Mutual Fund Auto-Sync**: Implement a "Background Sync" status indicator and a manual "Refresh All" button in the Top Bar for Mutual Fund NAV updates.
3. **Data Caching Layer**: Implement a Pinia plugin or custom composable to cache frequently accessed data (like Portfolio and Transaction metadata) in `localStorage` to eliminate blank-state flashing.

## 🔵 New Feature Ideas
4. **AI Rebalancing Assistant**: Expand the "Portfolio Intelligence" feature to suggest specific Buy/Sell quantities to achieve a target asset allocation.


## 🟣 Advanced Fintech Features (Long Term)
6. **Family Wealth Dashboard**: A high-level view that aggregates net worth across all family members, with permissions to hide/show specific accounts.
7. **Smart Rule Suggestion**: Implement a local analysis of uncategorized transactions to automatically suggest "Merchant -> Category" rules based on historical frequency.
8. **Goal-Based SIP Tracker**: Match specific SIP (Systematic Investment Plan) mandates from bank accounts to their corresponding Investment Goals.
9. **Document Vault**: A secure space to upload and link PDFs (Insurance policies, property deeds, tax returns) to specific family members or assets.
10. **Financial Health Score**: Create a proprietary "WealthFam Score" based on savings rate, emergency fund status, and debt-to-income ratios.

## ⚪ Quality of Life & Reliability

13. **Session Security**: Implement automatic session timeout and a "Logout from all devices" feature in `Settings.vue`.
