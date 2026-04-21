.PHONY: install setup dev serve worker app init db frontend backend clean help

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------

install: ## Install backend (editable) + frontend dependencies
	cd backend && uv sync && uv pip install -e .
	cd frontend && npm ci

setup: db install ## Full setup: start postgres, install deps

init: ## Generate ~/.maestro/config.yaml
	maestro init

# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

app: ## Start backend + frontend (maestro app)
	maestro app

serve: ## Start API server only with auto-reload
	maestro serve --reload

worker: ## Start agent worker process
	maestro worker

backend: ## Start backend only (uvicorn directly)
	cd backend && uv run uvicorn maestro.app:app --reload --port 8000

frontend: ## Start frontend only
	cd frontend && npm run dev

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

db: ## Start PostgreSQL via docker compose
	docker compose up -d

db-stop: ## Stop PostgreSQL
	docker compose down

db-reset: ## Reset PostgreSQL (destroy data)
	docker compose down -v && docker compose up -d

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------

clean: ## Remove build artifacts and caches
	rm -rf backend/.venv frontend/.next frontend/node_modules
