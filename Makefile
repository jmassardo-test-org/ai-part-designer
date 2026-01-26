# Makefile for AI Part Designer
# Common development and deployment commands

.PHONY: help dev dev-frontend dev-backend dev-worker test lint format build clean

# Default target
help:
	@echo "AI Part Designer - Development Commands"
	@echo ""
	@echo "Development:"
	@echo "  make dev              Start all services (requires Ollama running locally)"
	@echo "  make dev-detach       Start all services in background"
	@echo "  make dev-infra        Start infrastructure only (DB, Redis, MinIO)"
	@echo ""
	@echo "Individual Services:"
	@echo "  make dev-frontend     Start frontend development server"
	@echo "  make dev-backend      Start backend API server (poetry)"
	@echo "  make dev-worker       Start Celery worker"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all tests"
	@echo "  make test-backend     Run backend tests"
	@echo "  make test-frontend    Run frontend tests"
	@echo "  make test-e2e         Run end-to-end tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run all linters"
	@echo "  make format           Format all code"
	@echo "  make typecheck        Run type checking"
	@echo ""
	@echo "Database:"
	@echo "  make db-migrate       Run database migrations"
	@echo "  make db-rollback      Rollback last migration"
	@echo "  make db-seed          Seed database with templates"
	@echo "  make db-seed-users    Seed database with test users"
	@echo "  make db-seed-all      Seed all data (templates + users)"
	@echo "  make db-reset         Reset database (WARNING: deletes data)"
	@echo ""
	@echo "Build:"
	@echo "  make build            Build all Docker images"
	@echo "  make build-frontend   Build frontend for production"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean            Clean up containers, caches, and artifacts"
	@echo "  make logs             View all service logs"
	@echo "  make shell-api        Open shell in API container"

# ============================================================================
# Development
# ============================================================================

# Full Docker development (all services in containers, Ollama runs locally)
dev:
	@echo "Starting all services..."
	@echo "Note: Ollama must be running locally (ollama serve)"
	docker compose up

dev-detach:
	docker compose up -d

dev-infra:
	docker compose up -d postgres redis minio minio-init

# Local development with Ollama (services run locally, only infra in Docker)
dev-local: dev-local-check dev-local-infra dev-local-setup
	@echo ""
	@echo "=========================================="
	@echo "Local Development Environment Ready!"
	@echo "=========================================="
	@echo ""
	@echo "Services:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Redis: localhost:6379"
	@echo "  - MinIO: localhost:9000 (console: localhost:9001)"
	@echo "  - Ollama: localhost:11434"
	@echo ""
	@echo "Start the backend with:"
	@echo "  make dev-backend-local"
	@echo ""
	@echo "Or run everything at once:"
	@echo "  make dev-local-all"
	@echo ""

dev-local-check:
	@echo "Checking prerequisites..."
	@command -v ollama >/dev/null 2>&1 || (echo "Ollama not found. Install from https://ollama.ai" && exit 1)
	@curl -s http://localhost:11434/api/tags >/dev/null 2>&1 || (echo "Ollama not running. Start with: ollama serve" && exit 1)
	@echo "✓ Ollama is running"

dev-local-infra:
	@echo "Starting infrastructure services..."
	docker compose up -d postgres redis minio
	@echo "Waiting for services to be ready..."
	@sleep 3
	@docker compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1 || (sleep 5)
	@echo "✓ Infrastructure ready"

dev-local-setup:
	@echo "Setting up database..."
	@docker exec ai-part-designer-postgres psql -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'assemblematic_ai'" | grep -q 1 || \
		docker exec ai-part-designer-postgres psql -U postgres -c "CREATE DATABASE assemblematic_ai;"
	@cd backend && source ../.venv/bin/activate && alembic upgrade head 2>/dev/null || true
	@echo "✓ Database ready"

dev-local-all: dev-local
	@cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-backend-local:
	cd backend && source ../.venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && pnpm run dev

dev-backend:
	cd backend && poetry run uvicorn app.main:app --reload --port 8000

dev-worker:
	cd worker && poetry run celery -A app.celery worker --loglevel=info

dev-monitoring:
	docker compose --profile monitoring up -d

# Stop local dev services
dev-local-stop:
	docker compose stop postgres redis minio

# ============================================================================
# Testing
# ============================================================================

test: test-backend test-frontend

test-frontend:
	cd frontend && npm run test

test-backend:
	@echo "Running backend tests in Docker (includes CAD/CadQuery tests)..."
	docker exec ai-part-designer-api python -m pytest tests/ -v --tb=short

test-backend-local:
	cd backend && poetry run pytest -v

test-backend-cad:
	@echo "Running CAD-specific tests..."
	docker exec ai-part-designer-api python -m pytest tests/cad/ -v

test-e2e:
	cd frontend && npx playwright test --project=chromium

test-coverage:
	docker exec ai-part-designer-api python -m pytest --cov=app --cov-report=html tests/
	cd frontend && npm run test -- --coverage
	@echo "Coverage reports generated:"
	@echo "  Backend:  backend/htmlcov/index.html"
	@echo "  Frontend: frontend/coverage/index.html"

# ============================================================================
# Code Quality
# ============================================================================

lint: lint-frontend lint-backend lint-worker

lint-frontend:
	cd frontend && pnpm run lint

lint-backend:
	cd backend && poetry run ruff check .

lint-worker:
	cd worker && poetry run ruff check .

format: format-frontend format-backend format-worker

format-frontend:
	cd frontend && pnpm run format

format-backend:
	cd backend && poetry run ruff format .

format-worker:
	cd worker && poetry run ruff format .

typecheck: typecheck-frontend typecheck-backend typecheck-worker

typecheck-frontend:
	cd frontend && pnpm run typecheck

typecheck-backend:
	cd backend && poetry run mypy .

typecheck-worker:
	cd worker && poetry run mypy .

# ============================================================================
# Database
# ============================================================================

db-migrate:
	cd backend && poetry run alembic upgrade head

db-rollback:
	cd backend && poetry run alembic downgrade -1

db-revision:
	cd backend && poetry run alembic revision --autogenerate -m "$(msg)"

db-seed:
	cd backend && poetry run python -m app.seeds.templates

db-seed-users:
	cd backend && poetry run python -m app.seeds.users

db-seed-all: db-seed db-seed-users
	@echo "All seed data loaded successfully"

db-reset:
	docker compose down -v
	docker compose up -d postgres
	@sleep 5
	$(MAKE) db-migrate
	$(MAKE) db-seed

db-shell:
	docker compose exec postgres psql -U postgres -d ai_part_designer

# ============================================================================
# Worker
# ============================================================================

worker:
	cd backend && poetry run celery -A app.worker.celery worker --loglevel=info

worker-cad:
	cd backend && poetry run celery -A app.worker.celery worker --queues=cad --loglevel=info

worker-ai:
	cd backend && poetry run celery -A app.worker.celery worker --queues=ai --loglevel=info

worker-beat:
	cd backend && poetry run celery -A app.worker.celery beat --loglevel=info

worker-flower:
	cd backend && poetry run celery -A app.worker.celery flower --port=5555

# ============================================================================
# Data Operations
# ============================================================================

backup:
	cd backend && poetry run python -c "import asyncio; from app.core.backup import db_backup; asyncio.run(db_backup.create_backup())"

export-user-data:
	cd backend && poetry run python -c "import asyncio; from app.core.backup import data_exporter; asyncio.run(data_exporter.export_user_data('$(USER_ID)'))"

analytics-snapshot:
	cd backend && poetry run python -c "import asyncio; from datetime import datetime, timedelta; from app.core.backup import data_exporter; asyncio.run(data_exporter.export_analytics_snapshot(datetime.utcnow() - timedelta(days=7), datetime.utcnow()))"

# ============================================================================
# Build
# ============================================================================

build:
	docker compose build

build-frontend:
	cd frontend && pnpm run build

build-no-cache:
	docker compose build --no-cache

# ============================================================================
# Utilities
# ============================================================================

clean:
	# Stop and remove containers
	docker compose down -v --remove-orphans
	
	# Clean Python caches
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	
	# Clean frontend caches
	rm -rf frontend/node_modules frontend/dist 2>/dev/null || true
	
	# Clean coverage reports
	rm -rf backend/htmlcov frontend/coverage 2>/dev/null || true
	
	@echo "Cleaned up successfully!"

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f api

logs-worker:
	docker compose logs -f worker

shell-api:
	docker compose exec api bash

shell-worker:
	docker compose exec worker bash

shell-db:
	docker compose exec postgres psql -U postgres -d ai_part_designer

# Generate API client from OpenAPI spec
generate-api-client:
	cd frontend && pnpm run generate-api-types

# Check if all services are healthy
health-check:
	@echo "Checking service health..."
	@curl -s http://localhost:8000/health && echo "✅ API is healthy" || echo "❌ API is unhealthy"
	@docker compose exec redis redis-cli ping > /dev/null && echo "✅ Redis is healthy" || echo "❌ Redis is unhealthy"
	@docker compose exec postgres pg_isready -U postgres > /dev/null && echo "✅ Postgres is healthy" || echo "❌ Postgres is unhealthy"
