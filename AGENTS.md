# Repository Guidelines

## Project Structure & Module Organization
`backend/` contains the FastAPI server (`main.py`), job orchestration (`job_manager.py`), and model glue (`image_editor.py`), plus env configs (`.env`, `start.sh`). `frontend/` is the Vite React client: UI lives in `src/components`, API helpers in `src/utils/api.js`, and static assets in `public/`. Long-form notes stay in `docs/`, while repo scripts (`setup.sh`, `start`, `startup.sh`) coordinate installs and multi-service launches. Generated jobs and caches live in `~/qwen-image-editor/` and must remain untracked.

## Build, Test, and Development Commands
- `./setup.sh` – bootstrap the venv, npm deps, and cache directories.
- `./start` – runs health checks, stops stale servers, and starts FastAPI:8000 + Vite:3000.
- `cd backend && source venv/bin/activate && uvicorn main:app --reload` – backend-only debugging.
- `cd frontend && npm run dev` – Vite dev server with hot reload.
- `cd frontend && npm run build && npm run preview` – production bundle plus smoke test.
- `pytest backend/tests` / `cd frontend && npx vitest run` – add these suites to gate merges.

## Coding Style & Naming Conventions
Python: 4-space indentation, snake_case modules, PascalCase Pydantic models, and explicit type hints such as `models.EditJobRequest`; keep route handlers thin and push heavy work into helpers. React: keep components functional, files PascalCase, props camelCase, and prefer Tailwind utility classes over ad-hoc CSS while keeping API helpers pure. Name job folders and derived files in kebab-case for clarity.

## Testing Guidelines
Place backend tests in `backend/tests/` using `pytest` plus FastAPI’s `TestClient`; mock `image_editor` to avoid GPU downloads and name files `test_<area>.py`. Add `vitest` with React Testing Library for UI tests under `frontend/src/__tests__/` or next to each component. Prioritize queue handling, prompt validation, and upload guarding; document intentionally skipped cases inside the PR.

## Commit & Pull Request Guidelines
Follow the existing log style—single-line, imperative subjects under ~70 characters (e.g., “Remove deprecated files...” or “Enhance input/output folder management...”); use bodies only for context or references. PRs must summarize intent, include manual verification evidence (curl output, screenshots), call out config or `.env` changes, and note any model/cache impacts. Keep diffs focused and flag follow-up work explicitly.

## Security & Configuration Tips
Never commit `.env`, cache directories, or real user assets. Use the provided env vars (`HF_HOME`, `TRANSFORMERS_CACHE`, `JOBS_DIR`, `VITE_API_URL`) instead of hard-coded paths, and scrub job folders after debugging to avoid lingering PII. Redact prompt text or filenames when sharing logs, and verify local disk space before downloading large models.
