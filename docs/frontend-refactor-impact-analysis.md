# Frontend Refactor Impact Analysis

Date: 2026-02-12
Project: `E:\project\valuescan`
Scope: Frontend refactor for config + logging management, remove forecast frontend and legacy `mirofish` / `metacubexd` / clash-related leftovers.

## 1) Current State Summary

- Active frontend app is under `web/` with admin routes for:
  - dashboard
  - configuration
  - logs
  - services
  - forecast
- Forecast capability currently exists in two UIs:
  - Admin forecast page (`/admin/forecast`)
  - Public forecast landing (`/`)
- Frontend logging already exists (`loggerService` + `LogsPage`), but logger runtime config is not fully manageable/persisted as a first-class admin setting.
- Backend/system configuration management is already implemented in `ConfigurationPage`.

## 2) Affected Files (Primary)

- Routing and navigation:
  - `web/src/app/routes.tsx`
  - `web/src/components/layout/Sidebar.tsx`
  - `web/src/features/auth/AdminLoginPage.tsx`
  - `web/src/locales/en.json`
  - `web/src/locales/zh.json`
- Forecast module (to remove):
  - `web/src/features/forecast/ForecastPage.tsx`
  - `web/src/features/public/PublicForecastPage.tsx`
  - `web/src/services/forecastApi.ts`
- Logging system enhancement:
  - `web/src/services/loggerService.ts`
  - `web/src/types/logger.ts`
  - `web/src/features/logs/LogsPage.tsx`
- Tests:
  - `web/src/services/loggerService.test.ts`

## 3) Legacy Module Deletion Targets

Directories confirmed as legacy/non-active frontend stacks:

- `admin-web/`
- `metacubexd/`
- `mirofish/`
- `mirofish_backend/`
- `mirofish_frontend/`
- `mirofish_static/`

Notes:
- Current active app and compose stack do not depend on these for `web` runtime.
- Some historical docs/scripts mention these names; those references will be cleaned only if they block build/tests.

## 4) Risk Assessment

- Medium risk:
  - Route changes from public forecast root (`/`) to admin-first flow may affect bookmarks.
  - Removing legacy directories may affect ad-hoc local workflows not used by current app.
- Low risk:
  - Logger config UI and persistence changes are isolated to frontend service/page.

## 5) Execution Plan (Phase 2/3 Input)

1. Remove forecast pages/service and all route/menu references.
2. Redirect root route to admin flow (`/admin`) and keep auth guard behavior.
3. Upgrade frontend logging system to allow runtime config management and persistence.
4. Add logger config controls to `LogsPage`.
5. Delete legacy frontend directories listed above.
6. Update logger unit tests for new config behavior.
7. Run `npm run test` and `npm run build` in `web/`.

