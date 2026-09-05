# Alma Lead Intake -- developer entry points.
# Prerequisites: uv (Python 3.12 toolchain) and pnpm on PATH. See README.md.

API_DIR := api
WEB_DIR := web

.PHONY: help setup doctor dev api web test e2e lint fmt migrate seed install export-reqs verify-clone

help:
	@echo "make setup    - one-command bootstrap for a fresh clone"
	@echo "make doctor   - diagnose tools, config, database and chosen adapters"
	@echo "make install  - install api + web dependencies"
	@echo "make dev      - run api and web together"
	@echo "make api      - run the FastAPI server on :8000"
	@echo "make web      - run the Next.js dev server on :3000"
	@echo "make test     - pytest + web unit tests (vitest)"
	@echo "make lint     - ruff check + ruff format --check + pnpm lint + tsc --noEmit"
	@echo "make fmt      - ruff format + ruff check --fix"
	@echo "make migrate  - alembic upgrade head"
	@echo "make e2e      - playwright browser smoke test (boots both servers)"
	@echo "make seed     - load 4 demo leads across PENDING/REACHED_OUT/QUALIFIED"
	@echo "make export-reqs  - regenerate api/requirements.txt from uv.lock"
	@echo "make verify-clone - clone into a temp dir and prove setup works hands-free"

setup:
	./scripts/setup.sh

doctor:
	@cd $(API_DIR) && uv run python ../scripts/doctor.py

install:
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && pnpm install

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --port 8000

web:
	cd $(WEB_DIR) && pnpm dev

# Runs both servers; Ctrl-C stops the pair.
# Kills only its own two children: `kill 0` would signal the whole process group,
# which takes down whatever invoked make (scripts/verify-clone.sh found this).
dev:
	@$(MAKE) api & api_pid=$$!; \
	$(MAKE) web & web_pid=$$!; \
	trap 'kill $$api_pid $$web_pid 2>/dev/null' INT TERM EXIT; \
	wait $$api_pid $$web_pid

# Both suites: the API's pytest and the web layer's Vitest units. `make e2e` is kept
# separate because it boots servers and a browser.
test:
	cd $(API_DIR) && uv run pytest -q
	cd $(WEB_DIR) && pnpm test

# Boots the API and the web app itself, so this works from a cold start.
# Runs against a throwaway database that is deleted first, so a smoke run never
# touches the developer's data and never depends on what is already in it.
E2E_DB_FILE := data/e2e.db
E2E_DATABASE_URL := sqlite:///./$(E2E_DB_FILE)

e2e:
	rm -f $(E2E_DB_FILE)
	mkdir -p data
	cd $(API_DIR) && DATABASE_URL=$(E2E_DATABASE_URL) uv run alembic upgrade head
	cd $(WEB_DIR) && E2E_DATABASE_URL=$(E2E_DATABASE_URL) pnpm exec playwright test

lint:
	cd $(API_DIR) && uv run ruff check .
	cd $(API_DIR) && uv run ruff format --check .
	cd $(WEB_DIR) && pnpm lint
	cd $(WEB_DIR) && pnpm exec tsc --noEmit

fmt:
	cd $(API_DIR) && uv run ruff format .
	cd $(API_DIR) && uv run ruff check --fix .

migrate:
	cd $(API_DIR) && uv run alembic upgrade head

# Refuses to run outside ENVIRONMENT=local; safe to run repeatedly.
seed:
	@cd $(API_DIR) && uv run python ../scripts/seed.py

# api/requirements.txt exists only for reviewers who prefer pip; uv.lock is the
# source of truth, and CI fails if the export drifts.
export-reqs:
	@cd $(API_DIR) && printf '%s\n' "# GENERATED from uv.lock by make export-reqs — do not edit" > requirements.txt
	@cd $(API_DIR) && uv export --format requirements-txt --no-dev --no-hashes --no-emit-project >> requirements.txt
	@echo "wrote api/requirements.txt"

# The proof that a fresh clone works hands-free. Repeatable on any machine.
verify-clone:
	./scripts/verify-clone.sh $(ARGS)
