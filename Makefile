# racket-analytics developer entry points (sre-devops-engineer). `make help` lists targets.
SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
COMPOSE := docker compose -f infra/compose.yaml
ENV_FILE := infra/.env

.PHONY: help
help: ## List targets
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-16s %s\n", $$1, $$2}'

# ---------------------------------------------------------------- Docker Compose stack (ST-001)
$(ENV_FILE):
	cp infra/env.example $(ENV_FILE)
	@echo "created $(ENV_FILE) from infra/env.example (dev-only values)"

.PHONY: env
env: $(ENV_FILE) ## Create infra/.env from infra/env.example

.PHONY: up
up: $(ENV_FILE) ## Build and start the full stack, wait until healthy
	$(COMPOSE) up -d --build --wait

.PHONY: up-deps
up-deps: $(ENV_FILE) ## Start only backing services (Postgres, SeaweedFS, Mailpit, Jaeger)
	$(COMPOSE) up -d --wait postgres objectstore objectstore-init mailpit tracing

.PHONY: down
down: ## Stop the stack and delete its volumes
	$(COMPOSE) down -v

.PHONY: ps logs
ps: ## Show service status
	$(COMPOSE) ps -a
logs: ## Follow service logs
	$(COMPOSE) logs -f --tail=100

# ---------------------------------------------------------------- local services without Docker
.PHONY: local-db local-s3 local-stop
local-db: ## Start a throwaway Postgres 16; prints `export DATABASE_URL=...`
	@scripts/dev-postgres.sh start
local-s3: ## Start a throwaway SeaweedFS S3; prints `export S3_...=...`
	@scripts/dev-objectstore.sh start
local-stop: ## Stop and delete both local services
	@scripts/dev-postgres.sh stop; scripts/dev-objectstore.sh stop

# ---------------------------------------------------------------- checks
.PHONY: test-unit
test-unit: ## Unit suites (same command as the Stop hook)
	scripts/test-unit.sh

.PHONY: test-infra
test-infra: ## Tests for infra, hooks and CI scripts (starts local Postgres and SeaweedFS)
	cd infra && uv run pytest -q

.PHONY: lint
lint: ## Ruff lint + format check (backend), workflow lint
	cd backend && uv run ruff check . && uv run ruff format --check .
	actionlint

.PHONY: fmt
fmt: ## Format and auto-fix the backend
	cd backend && uv run ruff format . && uv run ruff check --fix .

.PHONY: typecheck
typecheck: ## mypy (strict on domain modules)
	cd backend && uv run mypy

.PHONY: fixtures-check
fixtures-check: ## Fixture and gold-set integrity against HEAD's manifests
	scripts/ci/check_fixtures.sh HEAD
