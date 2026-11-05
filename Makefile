# racket-analytics developer entry points (sre-devops-engineer). `make help` lists targets.
SHELL := /usr/bin/env bash
.DEFAULT_GOAL := help
COMPOSE := docker compose -f infra/compose.yaml
ENV_FILE := infra/.env
# ST-082 (ADR 0058 rule 7): `dev` builds the working tree; any other tag is a release image set.
IMAGE_TAG ?= dev
RELEASE_COMPOSE := $(COMPOSE) -f infra/compose.release.yaml

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
up: $(ENV_FILE) ## Build and start the full stack, wait until healthy (IMAGE_TAG=<release>: start that tag, no build)
ifeq ($(IMAGE_TAG),dev)
	$(COMPOSE) up -d --build --wait
else
	IMAGE_TAG=$(IMAGE_TAG) $(RELEASE_COMPOSE) up -d --no-build --wait
endif

.PHONY: release-images
release-images: $(ENV_FILE) ## Build the release image set racket-<service>:<IMAGE_TAG> from the working tree
	@test "$(IMAGE_TAG)" != dev || { echo "release-images: set IMAGE_TAG=<release>" >&2; exit 2; }
	IMAGE_TAG=$(IMAGE_TAG) $(RELEASE_COMPOSE) build

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

# ---------------------------------------------------------------- demo data (MVP-03)
# The stack's own dev CA (web-tls, ADR 0029): only the public root certificate is copied out.
DEMO_URL ?= https://localhost:3000
DEMO_CA := .local/demo/root.crt

.PHONY: demo
demo: ## Seed a demo match and generate the demo user's plan in the running dev stack (run `make up` first)
	@mkdir -p $(dir $(DEMO_CA))
	@$(COMPOSE) cp web-tls:/data/caddy/pki/authorities/local/root.crt $(DEMO_CA) >/dev/null 2>&1 \
	  || { echo "make demo: the stack's web-tls service is not reachable; run 'make up' first" >&2; exit 1; }
	python3 scripts/demo/seed_demo.py --base-url $(DEMO_URL) --cacert $(DEMO_CA) --env-file $(ENV_FILE)

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
