# Task Checklist - Refined Implementation Plan (Phase 4 & Refactoring)

## Phase 1: Planning & Setup
- [x] Audit existing Document Vault code in `finance` module
- [x] Create implementation plan for dedicated `vault` module
- [x] Initialize `backend/app/modules/vault` directory

## Phase 2: Implementation (Backend)
- [x] Create `vault/models.py` and migrate `DocumentVault`, `DocumentVersion`, `DocumentType`
- [x] Create `vault/service.py` and migrate `VaultService` logic
- [x] Create `vault/gdrive.py` and migrate sync logic
- [x] Create `vault/router.py` with standalone API endpoints
- [x] Create `vault/schemas.py` for pydantic validation
- [x] Update `backend/app/main.py` to register `vault_router` with `/finance/vault` prefix
- [x] Update `backend/app/core/migration.py` and `schema.sql` with new table definitions

## Phase 3: Cleanup & Refinement
- [x] Remove vault-related code from `finance/models.py`
- [x] Remove vault-related code from `finance/routers/`
- [x] Remove legacy service files in `finance/services/`
- [x] Verify API endpoint parity for frontend compatibility

## Phase 4: Verification
- [x] Ensure backend starts successfully (Resolved `parent_id` BinderException)
- [x] Verify frontend `client.ts` points to correct endpoints
- [x] Comprehensive audit of module isolation

- [x] **Refactor Document Vault to its own module `backend/app/modules/vault`**

## Upcoming Tasks
- [ ] **Goal-Based SIP Tracker (Item 8)**
- [ ] **Session Security (Item 13)**
