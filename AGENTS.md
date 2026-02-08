# Repository Guidelines

## Project Structure & Module Organization
- `api/`: Python REST API server.
- `signal_monitor/`: core Python services.
- `web/`: React + TypeScript dashboard (`web/src` for app code, `web/dist` for builds).
- `provider/`, `mcp/`: Go services and libraries.
- `config/`, `docker/`, `scripts/`: configuration, deployment, and utilities.
- `docs/` and `screenshots/`: documentation and assets.

## Build, Test, and Development Commands
- `make deps` / `make deps-frontend`: install Go or web dependencies.
- `make run` / `make run-frontend`: start Go backend or web dev server.
- `make build` / `make build-frontend`: build backend binary or web bundle.
- `make test` / `make test-backend` / `make test-frontend`: run all or scoped tests.
- `make test-coverage`: Go coverage report (`coverage.html`).
- `docker compose up -d`: bring up the stack in Docker (or `make docker-up`).

## Coding Style & Naming Conventions
- Go: format with `go fmt`, lint with `golangci-lint` when available, and keep idiomatic naming.
- Web: run `npm run lint` and `npm run format`; Prettier handles spacing and wrapping.
- TypeScript: prefer typed interfaces, avoid `any`, and use functional React components.
- Branch names: `feature/`, `fix/`, `docs/`, `refactor/`, `perf/`, `test/`, `chore/`.

## Testing Guidelines
- Go tests are `*_test.go` across modules (for example `api/`, `provider/`, `mcp/`).
- Web tests live in `web/src` as `*.test.ts`/`*.test.tsx` and run with Vitest.
- Aim to add or update tests with each behavior change; include coverage output only when needed.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `perf:`, `test:`, `chore:`, `ci:`, `security:` (optional scope).
- Keep first lines short and imperative; explain what and why if needed.
- Use `.github/PULL_REQUEST_TEMPLATE.md`; include a clear summary, linked issues, test steps, and UI screenshots when applicable.
- Keep PRs focused and small; split large changes when possible.

## Security & Configuration Tips
- Copy `.env.example` to `.env` and keep secrets out of git.
- For deployments, use Docker Compose and keep secrets in `.env`.
