# Alma Lead Intake -- developer entry points.
# Prerequisites: uv (Python 3.12 toolchain) and pnpm on PATH. See README.md.

API_DIR := api
WEB_DIR := web

.PHONY: help dev api web test lint fmt migrate seed install

help:
	@echo "make install  - install api + web dependencies"
	@echo "make dev      - run api and web together"
	@echo "make api      - run the FastAPI server on :8000"
	@echo "make web      - run the Next.js dev server on :3000"
	@echo "make test     - pytest"
	@echo "make lint     - ruff check + ruff format --check + pnpm lint + tsc --noEmit"
	@echo "make fmt      - ruff format + ruff check --fix"
	@echo "make migrate  - alembic upgrade head"
	@echo "make seed     - seed local data (stub until P0)"

install:
	cd $(API_DIR) && uv sync
	cd $(WEB_DIR) && pnpm install

api:
	cd $(API_DIR) && uv run uvicorn app.main:app --reload --port 8000

web:
	cd $(WEB_DIR) && pnpm dev

# Runs both servers; Ctrl-C stops the pair.
dev:
	@trap 'kill 0' INT TERM; \
	$(MAKE) api & \
	$(MAKE) web & \
	wait

test:
	cd $(API_DIR) && uv run pytest -q

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

# Stage 0 stub: there is no data to seed until the Lead model lands in P0.
seed:
	@echo "seed: nothing to do at Stage 0 (no models yet); implemented in P0"
