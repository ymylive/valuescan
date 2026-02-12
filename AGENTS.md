# AGENTS.md

This file is the operating guide for coding agents working in `E:\project\valuescan`.
Use this as the repo-specific source of truth before editing code.

## 1) Repository Layout

- `api/`: Flask-based Python API.
- `signal_monitor/`: Python signal ingestion, AI analysis, scheduling, Telegram delivery.
- `web/`: React + TypeScript frontend (Vite, Vitest, ESLint).
- `market/`, `store/`, `provider/`, `mcp/`: Go modules/services.
- `scripts/`: deployment/ops utilities.
- `docker-compose.yml`, `Dockerfile.*`, `nginx/`: Docker and reverse proxy runtime.
- `tests/`: Python tests discovered by pytest (`pytest.ini`).

Notes on noisy folders:
- Ignore `web/node_modules/`, `.tmp_git_submit/`, `tmp_*`, and `.github_export/` for normal development guidance.

## 2) Commands: Build, Lint, Test

Run commands from repo root unless noted.

### 2.1 Backend / Go

- Install/download deps: `go mod download`
- Build: `go build -o nofx`
- Format: `go fmt ./...`
- Vet: `go vet ./...`
- Test all: `go test ./...`
- Test single package: `go test ./market`
- Test single test function: `go test ./market -run TestGetKlinesSkipsInvalidRowsAndParsesValidRows`

### 2.2 API + Signal Monitor / Python

- Install API deps: `pip install -r api/requirements.txt`
- Install monitor deps: `pip install -r signal_monitor/requirements.txt`
- Run API locally: `python -m api.server`
- Run monitor scheduler locally: `python -m signal_monitor.ai_signal_scheduler`
- Run all pytest-discovered tests: `python -m pytest`
- Run single test file: `python -m pytest tests/test_admin_api.py`
- Run single test case: `python -m pytest tests/test_admin_api.py::TestControlAPI::test_start_scheduler`
- Run targeted monitor tests: `python -m pytest signal_monitor/test_macro_features.py signal_monitor/test_fundamentals_integration.py`

### 2.3 Frontend / Web

Run from `web/` directory:

- Install deps: `npm install`
- Dev server: `npm run dev`
- Build: `npm run build` (runs `tsc && vite build`)
- Lint: `npm run lint`
- Test all: `npm run test` (Vitest run mode)
- Test watch: `npm run test:watch`
- Test single file: `npm run test -- src/features/auth/AdminGuard.test.tsx`
- Test by name: `npm run test -- -t "renders"`

### 2.4 Docker

- Start stack: `docker compose up -d --build`
- Logs: `docker compose logs -f <service>`
- Stop stack: `docker compose down`

## 3) Style and Conventions

## 3.1 Python

- Follow existing style in `api/*.py` and `signal_monitor/*.py`.
- Prefer module-level `logger = logging.getLogger(__name__)` over `print` for runtime code.
- Use explicit error handling; do not silently swallow exceptions.
- Add type hints on public functions where practical; keep signatures readable.
- Keep functions focused; avoid unrelated refactors in bugfixes.
- Imports: stdlib first, third-party second, local modules last.
- Security-sensitive values must come from env/config, never hardcoded.

## 3.2 Go

- Always run `go fmt ./...` before finalizing changes.
- Keep names idiomatic and descriptive (avoid abbreviations unless standard).
- Return wrapped errors with context (`fmt.Errorf("...: %w", err)`).
- Handle all errors explicitly; avoid ignoring parse/IO errors unless intentional and documented.
- Keep package boundaries clear (`market`, `store`, `mcp`, etc.).

## 3.3 TypeScript / React

- TS is strict (`web/tsconfig*.json`): keep types explicit.
- Avoid `any`; prefer interfaces/types and narrowed unknown handling.
- Use functional components and hooks.
- Keep API calls in service layer (`web/src/services/*`) when possible.
- Lint must pass via `npm run lint`.
- Prefer absolute alias `@/*` where existing code uses it.

## 3.4 Naming and Branching

- Branch prefixes: `feature/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`, `chore/`.
- Use meaningful variable/function names; prioritize readability.
- Keep commit messages in Conventional Commits format:
  - `feat(scope): ...`
  - `fix(scope): ...`
  - `docs: ...`
  - `refactor: ...`
  - `perf: ...`
  - `test: ...`
  - `chore: ...`
  - `security: ...`

## 4) Testing Expectations

- Add or update tests for behavior changes.
- For bugfixes, prefer a regression test near the changed area.
- Do not delete tests to make CI pass.
- If a test is flaky or external-network-dependent, document that clearly in PR notes.

## 5) Error Handling Rules

- Fail safely with actionable logs.
- Return stable API response shapes for Flask endpoints.
- For retries/timeouts, use explicit bounds (no unbounded waits).
- Never suppress type/lint issues with blanket ignores unless already established in the file.

## 6) Security and Config Rules

- Copy `.env.example` to `.env` for local config.
- Never commit live secrets/tokens/credentials.
- Treat JSON config files under `signal_monitor/` as potentially sensitive.
- Prefer placeholders like `<SET_IN_ENV>` for committed examples.
- Validate user-provided limits/inputs at API boundaries.

## 7) Agent Workflow Checklist

Before coding:
- Read nearby files and existing patterns.
- Identify minimal change set.

During coding:
- Keep edits scoped to request.
- Preserve existing behavior unless task requests change.

Before final response:
- Run relevant lint/tests for touched areas.
- Report command results and any known limitations.

## 8) Rule Files (Cursor / Copilot / Other)

- No `.cursor/rules/` directory found.
- No `.cursorrules` file found.
- No `.github/copilot-instructions.md` found.
- Additional repo rule file exists: `.windsurfrules` (Chinese):
  - `每次对话完毕都必须调用askcontinue mcp`
  - If your runtime supports that MCP action, comply.

## 9) Known Drift to Avoid Confusion

- Some legacy docs/scripts mention `make` targets, but no root `Makefile` is present.
- `scripts/pr-check.sh` references `npm run type-check`, but `web/package.json` does not define `type-check`.
- Prefer the actual runnable commands in Section 2 of this file.
