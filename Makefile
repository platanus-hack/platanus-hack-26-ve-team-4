COMPOSE := docker compose --env-file .env -f infra/compose.yaml

.PHONY: install dev-backend dev-frontend format lint typecheck test check up down logs smoke smoke-exercise fleet-server fleet-walkthrough arena-server evaluate

install:
	cd backend && uv sync
	cd frontend && pnpm install

dev-backend:
	cd backend && set -a && . ../.env && set +a && \
	uv run uvicorn agent_zero.main:create_app --factory --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

format:
	cd backend && uv run ruff format . && uv run ruff check --fix .
	cd frontend && pnpm format

lint:
	cd backend && uv run ruff check . && uv run ruff format --check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src tests scripts
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

smoke-exercise:
	set -a && . ./.env && set +a && ./infra/scripts/smoke.sh --exercise

ARENA_MODE ?= demo
ARENA_PORT ?= 8000
ARENA_DATA ?= ./data/arena

arena-server:
	cd backend && set -a && . ../.env && set +a && \
	AGENT_ZERO_LLM_MODE=$(ARENA_MODE) AGENT_ZERO_DATA_DIR=$(ARENA_DATA) \
	uv run uvicorn agent_zero.main:create_app --factory --port $(ARENA_PORT)

AFTER ?= 3
EVIDENCE ?= ../artifacts/core-evaluation/comparison.json

evaluate:
	cd backend && set -a && . ../.env && set +a && \
	uv run python -m agent_zero.evals --base-url http://localhost:$(ARENA_PORT) \
	--after $(AFTER) --repetitions 3 --max-calls 1200 --output $(EVIDENCE)

FLEET_PORT ?= 8000
FLEET_MODE ?= live
FLEET_DATA ?= ./data/fleet

fleet-server:
	cd backend && set -a && . ../.env && set +a && \
	AGENT_ZERO_LLM_MODE=$(FLEET_MODE) AGENT_ZERO_OTEL_EXPORTER=memory AGENT_ZERO_DATA_DIR=$(FLEET_DATA) \
	uv run uvicorn agent_zero.main:create_app --factory --port $(FLEET_PORT)

fleet-walkthrough:
	cd backend && set -a && . ../.env && set +a && \
	uv run python -m agent_zero.walkthrough --base-url http://localhost:$(FLEET_PORT) --save $(FLEET_DATA)/recorrido.json
