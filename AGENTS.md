# AGENTS.md

Agent operating guide for this repository.

## 0. Scope and precedence

- This file applies to the whole repo.
- If a deeper directory later adds its own `AGENTS.md`, the nearest file wins.
- Communication rule: All responses must be in Chinese.
- Existing repo guidance to honor:
  - `docs/standards/DEVELOPMENT.md`
  - `docs/standards/COMMIT_CONVENTION.md`
- Cursor/Copilot rule files check:
  - `.cursor/rules/`: not found
  - `.cursorrules`: not found
  - `.github/copilot-instructions.md`: not found

## 1. Repository layout (quick map)

- `backend/`: Django + DRF API services.
  - Apps: `assets`, `auditlog`, `iam`
  - Entry: `backend/manage.py`
  - Settings: `backend/cmdb_backend/settings.py`
- `frontend/`: React + TypeScript + Vite + Tailwind + shadcn/ui.
  - Entry: `frontend/src/main.tsx`
  - UI base: `frontend/src/components/ui/`
- `docker-compose.yml`: local stack (`frontend`, `backend`, `mysql`).
- `docs/`: architecture/product/standards documents.

## 2. Environment assumptions

- Backend commands require a Python env with Django installed.
- Frontend commands require `npm install` completed in `frontend/`.
- MySQL is required for realistic backend runtime and integration tests.

## 3. Build, lint, test commands

### 3.1 Frontend (verified)

Run from `frontend/`:

- Install deps: `npm install`
- Dev server: `npm run dev`
- Type/lint check: `npm run lint`
- Production build: `npm run build`
- Preview build: `npm run preview`

Notes:

- `npm run lint` is TypeScript check (`tsc --noEmit`), not ESLint.
- No frontend unit test runner is configured yet (no `test` script).

### 3.2 Backend (Django)

Run from `backend/`:

- Install deps: `pip install -r requirements.txt`
- Apply migrations: `python manage.py migrate`
- Start server: `python manage.py runserver 0.0.0.0:8000`
- Run all tests: `python manage.py test`

Single-test patterns (Django test runner):

- Single app: `python manage.py test assets`
- Single module: `python manage.py test assets.tests`
- Single class: `python manage.py test assets.tests.SomeTestCase`
- Single method: `python manage.py test assets.tests.SomeTestCase.test_xxx`

Practical note:

- In this environment, backend command verification failed because Django is not installed in active Python.
- Command patterns above are standard Django and align with this project entrypoint.

### 3.3 Docker Compose

Run from repo root:

- Validate config: `docker compose config`
- Build and start: `docker compose up -d --build`
- Stop: `docker compose down`
- Stop and remove volumes: `docker compose down -v`

## 4. Code style and architecture conventions

## 4.1 Backend conventions (Django/DRF)

- Prefer function-based DRF views with explicit decorators.
  - Pattern in `backend/assets/views.py`, `backend/iam/views.py`.
- Always declare endpoint permissions with `@permission_classes(...)`.
- Keep request validation in serializers.
  - See `backend/assets/serializers.py`, `backend/iam/serializers.py`.
- Keep response payload shape consistent with existing `build_response` convention.
- Keep audit logging behavior for create/update/delete in assets flows.
- Use `transaction.atomic()` for multi-write operations.
- Use `select_related` / `prefetch_related` for relation-heavy queries.

Imports:

- Order: standard library -> third-party -> local app imports.
- Prefer relative imports within same app (`from .models import ...`).
- Use explicit imports; avoid wildcard imports.

Naming:

- Functions/variables: `snake_case`.
- Classes/serializers/permissions: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Endpoint handlers commonly follow `<resource>_list_create` / `<resource>_detail`.

Types and data contracts:

- Add type hints for new helper functions where practical.
- Preserve existing response fields expected by clients.
- Do not introduce ad-hoc response schemas per endpoint.

Error handling:

- Do not swallow exceptions.
- Prefer specific exceptions over broad `except Exception`.
- Return meaningful API errors with correct HTTP status.
- Keep permission-denied and validation errors explicit.

Formatting:

- New Python code should use 4 spaces.
- Some legacy backend files contain tabs; when touching them, keep diffs minimal unless doing explicit normalization.

## 4.2 Frontend conventions (React/TS/shadcn)

- Use TypeScript strict mode as configured.
- Prefer typed props and avoid `any`.
- Keep shared UI primitives in `frontend/src/components/ui/`.
- Keep helpers in `frontend/src/lib/` (for example `cn` utility).
- Use alias imports via `@/` for `src` paths.
- Components: `PascalCase`; hooks: `useXxx`; locals: `camelCase`.
- Favor Tailwind utility classes and existing CSS variables.
- Follow existing shadcn-style composition patterns.

## 4.3 Docs and commit conventions

- Update docs in the same task when behavior changes.
- Keep docs under:
  - `docs/architecture/`
  - `docs/product/`
  - `docs/standards/`
- Commit message format: `<type>: <subject>`.
- Allowed commit types: `feat`, `fix`, `docs`, `refactor`, `style`, `test`, `chore`.

## 5. Agent execution checklist

- Before editing: locate similar code paths and copy local patterns.
- While editing: keep changes scoped and consistent.
- After editing frontend: run `cd frontend && npm run lint && npm run build`.
- After editing backend: run `cd backend && python manage.py test` (or targeted tests).
- After editing deployment/config: run `docker compose config`.
- If a required check cannot run, report exactly what failed and why.

## 6. High-confidence references

- Commands and stack: `README.md`, `frontend/package.json`, `docker-compose.yml`.
- Backend API style: `backend/assets/views.py`, `backend/iam/views.py`.
- Backend permissions: `backend/cmdb_backend/permissions.py`.
- Frontend style baseline: `frontend/src/App.tsx`, `frontend/src/components/ui/button.tsx`.
- Team standards: `docs/standards/DEVELOPMENT.md`, `docs/standards/COMMIT_CONVENTION.md`.
