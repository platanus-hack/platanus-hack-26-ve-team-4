COMPOSE := docker compose -f infra/compose.yaml

.PHONY: install dev-backend dev-frontend format lint typecheck test check up down logs smoke

install:
	cd backend && uv sync
	cd frontend && pnpm install

dev-backend:
	cd backend && uv run uvicorn agent_zero.main:create_app --factory --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm format

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src tests
	cd frontend && pnpm typecheck

test:
	cd backend && uv run pytest
	cd frontend && pnpm test

check: lint typecheck test

up:
	$(COMPOSE) up --build --detach --wait

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs --follow

smoke:
	./infra/scripts/smoke.sh
