# WealthFam: Engineering Practices & Standards

> This document is the single source of truth for all engineering decisions across the WealthFam stack (FastAPI backend, Vue 3 web frontend, Flutter mobile app). Every contributor must read and adhere to these standards before writing code.

---

## Table of Contents
1. [Architecture & Project Structure](#1-architecture--project-structure)
2. [API Design](#2-api-design)
3. [Database & Data Integrity](#3-database--data-integrity)
4. [Authentication & Security](#4-authentication--security)
5. [Error Handling](#5-error-handling)
6. [Business Logic & Services](#6-business-logic--services)
7. [Background Tasks & Scheduling](#7-background-tasks--scheduling)
8. [Real-time (WebSockets)](#8-real-time-websockets)
9. [Frontend Standards (Vue 3)](#9-frontend-standards-vue-3)
10. [Mobile Standards (Flutter)](#10-mobile-standards-flutter)
11. [Coding Style & Naming](#11-coding-style--naming)
12. [Testing](#12-testing)
13. [Configuration & Environment](#13-configuration--environment)
14. [CI/CD & Deployment](#14-cicd--deployment)
15. [Documentation](#15-documentation)

---

## 1. Architecture & Project Structure

### Backend (`backend/app/`)
- **Feature-first modules.** All business domains live under `app/modules/<domain>/`. Each module **must** contain:
  - `models.py` – SQLAlchemy/DuckDB table definitions
  - `schemas.py` – Pydantic V2 request/response models
  - `routers/` – One router file per sub-resource (e.g., `transactions.py`, `categories.py`)
  - `services/` – All business logic; one service class/file per concern
  - `utils/` – Module-scoped pure utility functions (no side effects, no DB access)
- **Core infrastructure** (`app/core/`) contains only: `config.py`, `database.py`, `exceptions.py`, `migration.py`, `scheduler.py`, `seeder.py`, `timezone.py`, `websockets.py`. **Do not add business logic here.**
- **`app/main.py`** is for app factory and router registration only. No business logic, no inline route handlers.

### Frontend (`frontend/src/`)
- Domain-driven layout: `views/`, `components/`, `stores/`, `composables/`, `api/`, `utils/`, `layouts/`, `plugins/`.
- Feature components live in `components/<domain>/`. Avoid flat `components/` dumping.
- Every data-fetching concern must go through a Pinia store or a composable — never directly inside a `<script setup>` block of a page view.

### Mobile (`mobile_app/`)
- Feature-first folder structure mirroring the backend module names.
- Use Bloc/Cubit for all state management. No raw `setState` outside of genuinely local UI state.
- DTOs must mirror backend schemas exactly and be generated/maintained in sync.

---

## 2. API Design

### Versioning & Path Conventions
| Client   | Path Prefix          | Purpose                                       |
|----------|----------------------|-----------------------------------------------|
| Web      | `/api/v1/web/`       | Full payloads, bulk data, dashboard responses |
| Mobile   | `/api/v1/mobile/`    | Lean payloads optimised for low bandwidth     |
| Internal | `/api/v1/internal/`  | Service-to-service or scheduler-triggered     |

- Never cross-pollinate web and mobile routers. Data shape differences must live in separate schemas.
- All endpoints must be **versioned**. Introducing a breaking change requires a new version path, not an in-place modification.

### Request / Response
- **Validation:** Pydantic V2 with `model_config = ConfigDict(strict=True)` on all schemas. No `Optional` fields without explicit defaults.
- **Monetary values:** Always `Decimal`, never `float`. Schema fields use `condecimal(max_digits=18, decimal_places=4)`.
- **Pagination:** All list endpoints that can return more than 50 items **must** accept `skip: int = 0` and `limit: int = Query(50, le=500)`.
- **Timestamps:** Always return UTC ISO-8601 (`datetime` with `timezone.utc`). The frontend converts to local time – the backend never does.
- **Envelope:** Successful responses for lists use `{"data": [...], "total": N}`. Single-resource responses return the object directly.

### HTTP Status Codes
| Scenario                          | Code |
|-----------------------------------|------|
| Success (create)                  | 201  |
| Success (read/update/delete)      | 200  |
| Validation error                  | 422  |
| Authentication failure            | 401  |
| Authorisation failure             | 403  |
| Resource not found                | 404  |
| Duplicate / conflict              | 409  |
| Unhandled server error            | 500  |

---

## 3. Database & Data Integrity

### DuckDB Session Management
- The single DuckDB connection is managed in `app/core/database.py`. **Never** open a raw DuckDB connection outside this module.
- All write operations (INSERT, UPDATE, DELETE) **must** happen inside a context-managed session obtained from `get_db()`.
- **Concurrency:** DuckDB does not support concurrent writers. All write paths must acquire the application-level `db_write_lock` (defined in `app/core/database.py`) before executing. Readers do not need the lock.

### Migrations
- Schema changes are managed by `app/core/migration.py`. **All DDL changes** (new tables, columns, indexes) must be added as a numbered migration step in that file.
- All DB detaisl shoudl be aprt of schema.sql
- Migrations run automatically on startup. They are idempotent — always guard with `IF NOT EXISTS` or column-presence checks.
- **Never alter production schema manually.** All changes must go through the migration module.

### Data Rules
- `Decimal` for all currency arithmetic — no exceptions.
- Soft-delete pattern: use an `is_deleted: bool` / `deleted_at: datetime` column; never hard-delete financial records.
- Foreign key constraints must be declared in the schema SQL and enforced at the application layer (DuckDB FK enforcement is advisory).
- Seed data (`app/core/seeder.py`) is idempotent and safe to run on every deploy.

---

## 4. Authentication & Security

### JWT / Token Handling
- Tokens are validated in `app/modules/auth/`. The `get_current_user` dependency must be applied to every non-public endpoint via `Depends(get_current_user)`.
- Access token lifetime: **≤ 60 minutes**. Refresh tokens: **≤ 7 days**.
- Tokens are **never** logged, stored in browser `localStorage` (web uses `httpOnly` cookies / secure storage), or embedded in URLs.
- Passwords are hashed with **bcrypt** (minimum cost factor 12). Plaintext passwords must never appear in logs or error messages.

### CORS
- Allowed origins are defined in `app/core/config.py` (`Settings.allowed_origins`) and loaded from environment. **No wildcard (`*`) in production.**
- Credentials mode requires explicit `allow_credentials=True` coupled with a non-wildcard origin list.

### Input Sanitisation
- All user-supplied strings that are rendered in the UI must be treated as untrusted. No raw HTML injection from API responses.
- File uploads (Excel/CSV ingestion) must be validated for MIME type and size before processing. Reject anything that does not match the expected format.

### General
- No secrets, credentials, or API keys in source code. Use `.env` (excluded from version control) and reference via `pydantic-settings`.
- Rotate the `SECRET_KEY` in all environments annually or immediately after a credential exposure event.

---

## 5. Error Handling

### Backend
- Define all custom exceptions in `app/core/exceptions.py`. Raise typed exceptions from service layers.
- Register a **single global exception handler** in `app/main.py` for each custom exception type. Return structured JSON: `{"detail": "human-readable message", "code": "MACHINE_CODE"}`.
- Never expose raw stack traces to API clients in production. Use `app.debug = False` and log internally.
- Unhandled exceptions must be caught by the global 500 handler, logged with full traceback (to file/stdout depending on environment), and return a generic `"Internal server error"` response.

### Frontend
- All Pinia store actions that make API calls must wrap them in `try/catch` and dispatch an error state that the UI can react to.
- Use a single Axios response interceptor (in `src/api/`) to handle 401 (redirect to login), 403 (show permission snackbar), and 5xx (show global error banner) responses.
- Never `console.log` sensitive data (tokens, raw financial figures) in production builds.

### Mobile
- All repository calls must return `Either<Failure, Success>`. No raw `throw` in business logic.
- User-visible error messages are localised strings; never expose raw exception messages to users.

---

## 6. Business Logic & Services

- **Rule:** Zero business logic in route handlers (`routers/`). Handlers validate the request (via schema), call a service method, and return a response. Period.
- Services are plain Python classes injected via `Depends()`. They receive a database session and any other dependencies through their constructor or method signatures.
- Service methods must be **single-responsibility**: one public method per distinct operation.
- Pure utility functions (date math, currency formatting, data transformations) live in `<module>/utils/` and are independently testable.
- Cross-module calls: a module's service may depend on another module's service, but never import directly from another module's `models.py` or `routers/`. Dependency flows downward.

---

## 7. Background Tasks & Scheduling

- All scheduled jobs are registered in `app/core/scheduler.py` using APScheduler. **No ad-hoc `BackgroundTasks` for recurring work** — use the scheduler.
- Every scheduled job must:
  1. Acquire the `db_write_lock` if it performs any writes.
  2. Handle its own exceptions and log failures — a crashing job must not crash the scheduler.
  3. Be idempotent: running the job twice must produce the same outcome as running it once.
- Scheduler start/stop is managed in the FastAPI `lifespan` context manager in `app/main.py`.

---

## 8. Real-time (WebSockets)

- The `ConnectionManager` lives in `app/core/websockets.py`. It is the only place that manages WebSocket connections.
- All WebSocket messages are JSON-serialised. Message envelope: `{"type": "EVENT_TYPE", "payload": {...}}`.
- Authentication: WebSocket connections must present a valid token in the query string or initial handshake message. Unauthenticated connections are closed immediately with code `4001`.
- The frontend (`src/composables/useWebSocket.ts` or equivalent) must implement exponential back-off reconnection (cap at 30 s).
- WebSocket events are notifications only — they carry enough data to trigger a store refresh, not replace a full API fetch.

---

## 9. Frontend Standards (Vue 3)

### Component Authoring
- **`<script setup>`** syntax is mandatory for all components. Options API is forbidden in new code.
- **Vuetify 3 components only.** Do not write custom CSS for layout, spacing, typography, or colour. Use Vuetify's design system tokens and utility classes.
- Component file names: `PascalCase.vue`. Composable file names: `useFeatureName.ts`. Store file names: `featureName.ts`.
- Props must be typed with TypeScript interfaces. Avoid `as any`.

### State Management (Pinia)
- One store per domain (e.g., `auth.ts`, `finance.ts`, `notification.ts`). Do not create generic catch-all stores.
- Stores expose: `state` (reactive), `getters` (computed), `actions` (async). No logic in component templates.
- Sensitive state (tokens, raw PII) must not be persisted to `localStorage` via Pinia plugins without explicit encryption.

### API Layer
- All API calls are made through typed functions in `src/api/<domain>.ts`. No direct `axios` calls from components or stores.
- API functions return typed responses matching the backend Pydantic schema (keep DTOs in sync).
- Base URL and auth headers are configured in a single Axios instance in `src/api/axios.ts`.

### TypeScript
- `strict: true` in `tsconfig.json`. No `ts-ignore` comments without a documented justification comment above.
- Prefer `interface` over `type` for object shapes. Use `type` for unions/intersections.

### 9.5 UI Best Practices
- **Design Language:** Adhere strictly to **Material Design** (M3) aesthetics. Focus on depth, surfaces, and meaningful motion.
- **Glassmorphism:** Use subtle glass/blur effects for cards, sidebars, and overlays to create a sense of depth and modern elegance.
- **Micro-animations:** Every button, card, and interactive element **must** have hover and active states (scale, shadow, or color shifts). Use subtle transitions for entering/leaving elements.
- **Premium Aesthetics:** Use vibrant, harmonious color palettes (avoid default primary/secondary). Leverage smooth gradients for headers and primary CTAs. Ensure a consistent "Premium" feel across all views.
- **Searchable Dropdowns:** **All** dropdowns/select components must be searchable. Users should never have to scroll through a long list manually.
- **Iconography:** Use a **consistent icon set** (e.g., Material Design Icons) across the entire application. Do not mix outlined, filled, and sharp styles unless it's a semantic distinction.
- **Tooltips:** **Always** provide tooltips for icon-only buttons, complex labels, and any interactive element where the action is not immediately obvious from text alone.
- **Unified Button Styles:** Use the central design system (Vuetify) for buttons. Ensure consistent padding, border-radius, elevation, and hover states. Variants (Primary, Secondary, Outlined, Ghost, Danger) must be used consistently for their specific semantic purposes.
- **Pagination Consistency:** All paginated views (tables, grids, lists) **must** use a unified footer design mirroring the Material Data Table style. This includes a "Rows per page" autocomplete, an "X-Y of Z" state label, and prev/next navigation controls. Custom grid views must manually implement this footer style to maintain visual parity with standard tables.

---

## 10. Mobile Standards (Flutter)

- `const` constructors everywhere possible. Avoid rebuilding widget trees unnecessarily.
- Widget naming: `PascalCase`. File naming: `snake_case.dart`.
- All network calls go through a `Repository` class. No direct HTTP calls in UI widgets or Blocs.
- Bloc/Cubit events and states are defined in the same feature directory as the Bloc.
- Use `Decimal` (via `decimal` Dart package) for all monetary values. Never `double` for money.
- Mobile API DTOs must be versioned separately if the mobile API path (`/api/v1/mobile/`) has a different schema than the web path.

---

## 11. Coding Style & Naming

### Universal
| Context            | Convention    |
|--------------------|---------------|
| Python identifiers | `snake_case`  |
| JS/TS variables    | `camelCase`   |
| Vue components     | `PascalCase`  |
| Dart classes/widgets | `PascalCase` |
| Dart variables     | `camelCase`   |
| Database columns   | `snake_case`  |
| Environment vars   | `UPPER_SNAKE_CASE` |
| Git branches       | `type/short-description` (e.g., `feat/add-budget-alerts`) |

### Python
- Follow **PEP 8**. Enforced by **Ruff** (`ruff check` and `ruff format` in CI).
- No `float` for monetary values; use `Decimal`.
- Type annotations on all function signatures (parameters and return type).
- Max line length: **100** characters.
- Private helpers: prefix with `_`. Do not expose internal helpers in module `__init__.py`.
- **All imports must appear at the top of the file**, before any module-level code. Inline/deferred `import` statements inside function bodies are only permitted for breaking circular imports — document the reason with a comment.
- **Import order** (enforced by Ruff/isort):
  1. Standard library (`os`, `re`, `datetime`, …)
  2. Third-party packages (`fastapi`, `sqlalchemy`, `pydantic`, …)
  3. Internal application modules (`backend.app.*`)
  - Each group is separated by a blank line. Within a group, `import X` precedes `from X import Y`.
- **No unused imports.** Remove any imports that are not used in the code.
- **No double imports.** Never import the same module/member twice. Consolidate into a single statement.

### TypeScript / Vue
- ESLint + Prettier enforced in CI. Configuration lives in `.eslintrc` / `.prettierrc` at the frontend root.
- **No unused imports.**
- **No double imports.**
- No `var`. Use `const` by default, `let` only when reassignment is necessary.
- Avoid deeply nested ternaries — extract to named constants or computed properties.
- **All imports must appear at the top of the file**, before any component or logic definitions.
- **Import order** (enforced by ESLint `import/order` plugin):
  1. Side-effect imports (`import './style.css'`)
  2. Node built-ins (`path`, `fs`)
  3. Third-party packages (`vue`, `pinia`, `axios`, `vuetify`, …)
  4. Internal aliases (`@/stores/…`, `@/api/…`, `@/components/…`)
  5. Type-only imports (`import type { … }`)
  - Each group separated by a blank line. Alphabetical order within each group.

### Vue SFC Block Order
- All Single File Components must follow this **exact block order**:
  1. `<template>` — HTML structure
  2. `<script setup lang="ts">` — component logic
  3. `<style scoped>` — component-scoped CSS (only if custom styles are needed beyond Vuetify)
- Never place `<script>` before `<template>`. Never place `<style>` before `<script>`.
- Scoped styles are preferred over global styles. Global style overrides belong in `src/assets/`.

### General Quality Rules
- **No dead code.** Remove unused imports, commented-out code blocks, and stale TODO comments. Stale TODOs that cannot be resolved immediately must be converted to tracked issues.
- **No magic numbers.** Named constants or configuration values only.
- **No console.log / print in production paths.** Use structured logging (Python `logging` module; frontend logger utility).
- **Comments must add value.** A comment should explain *why*, not *what*. The following are banned:
  - Obvious restatements of the code: `# increment counter`, `# return the result`, `i += 1  # add 1 to i`
  - AI-generated filler phrases: `# This function handles…`, `# Here we…`, `# Now we…`, `# Let's…`
  - Section dividers that add no information: `# --- Start ---`, `# Logic below`
  - Commented-out code left "just in case"
  - Permitted exceptions: non-obvious algorithmic decisions, deferred import justifications, regulatory/business rule references, and workarounds for known library bugs (must include a link or ticket reference).

---

## 12. Testing

### Backend
- Framework: **pytest** with `pytest-asyncio` for async route tests.
- Test location: `backend/tests/<module>/` mirroring the module structure.
- **Unit tests** cover service methods in isolation (mock the DB session).
- **Integration tests** cover routers end-to-end using a test DuckDB in-memory instance.
- Minimum coverage target: **80%** on service and utility layers.
- All tests must pass before a PR is merged. CI blocks on red tests.

### Frontend
- Framework: **Vitest** for unit/composable tests; **Cypress** (or Playwright) for E2E.
- Critical Pinia stores and composables must have unit tests.
- API mock: use `msw` (Mock Service Worker) for component and store tests.

### Mobile
- **Unit tests** for all Bloc logic using `bloc_test`.
- Repository tests mock the HTTP client.

---

## 13. Configuration & Environment

- All environment variables are declared in `.env.example` with descriptions. Never commit a `.env` file.
- Application settings loaded via `pydantic-settings` (`app/core/config.py`). Access settings only through the `get_settings()` singleton — never `os.getenv()` elsewhere.
- Environment tiers: `development`, `staging`, `production`. Settings class must differentiate behaviours (e.g., debug mode, log level, CORS origins).
- Secrets management: In production (Fly.io / Render / Pi), secrets are set as platform environment variables or Docker secrets. Do not store secrets in `docker-compose.yml` in plaintext.

---

## 14. CI/CD & Deployment

### Branching Strategy
- `main` — production-ready, protected. Direct pushes forbidden.
- `develop` — integration branch. All feature branches merge here first.
- `feat/*`, `fix/*`, `chore/*` — short-lived feature/fix branches off `develop`.

### Pull Request Rules
- PRs require at least one approval.
- CI checks must be green: lint, type-check, and unit tests.
- PR descriptions must reference the relevant issue/ticket and include a brief summary of changes.

### Build & Deploy
- Docker image is built via `build_and_push.sh`. Image tags are `git` SHA-based plus `latest`.
- `entrypoint.sh` runs migrations (`migration.py`) before starting the Uvicorn server.
- The frontend is built (`npm run build`) and served via Nginx (`nginx.conf`). **Never** run Vite dev server in production.
- Health check endpoint: `GET /health` must return `{"status": "ok"}` within 5 seconds. This is the liveness probe for all deployment platforms.
- Zero-downtime deployments: use rolling restarts. The migration step must be backward-compatible with the previous running version.

### Observability
- **Logging:** Python `logging` at `INFO` in production, `DEBUG` in development. Structured JSON logs in production to facilitate log aggregation.
- **Error tracking:** All unhandled exceptions should emit to the configured error tracking sink (e.g., Sentry DSN in environment). Frontend uses a global Vue error handler.
- **Metrics:** Expose `/metrics` (Prometheus-compatible) if performance SLOs are defined.

---

## 15. Documentation

- **This file (`PRACTICES.md`)** is updated whenever a new pattern, library, or architectural decision is introduced. It is reviewed quarterly.
- **`README.md`** covers setup, running locally, and deployment. It must stay accurate.
- **`backlog.md`** tracks known tech debt and future enhancements. Items resolved in a release must be removed.
- Public-facing API documentation is auto-generated via FastAPI's `/docs` (Swagger UI) and `/redoc`. All route handlers must have a `summary` and `description` argument, and all schemas must have `Field(description=...)` on non-obvious fields.
- Architectural decisions that deviate from these standards must be documented in `docs/` with an ADR (Architecture Decision Record) format.

---

## 16. Testing
- If vue files changed buiold and ensure it builds sucessfully.

*Last updated: March 2026 | Maintained by the WealthFam engineering team*
