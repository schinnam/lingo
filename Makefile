.PHONY: test test-unit test-integration test-ui db-up db-down ui-install ui-build ui-dev

# Run all tests
test: test-unit test-ui

# Run unit tests only (no Docker required)
test-unit:
	uv run pytest tests/unit/

# Run integration tests (requires postgres container)
test-integration: db-up
	uv run pytest tests/integration/ -v

# Run frontend tests
test-ui: ui-install
	cd frontend && npm test

# Install frontend dependencies
ui-install:
	cd frontend && npm install

# Build frontend production assets
ui-build: ui-install
	cd frontend && npm run build

# Start frontend dev server
ui-dev: ui-install
	cd frontend && npm run dev

# Start the postgres container if not already running
db-up:
	docker compose up -d postgres
	docker compose exec postgres sh -c 'until pg_isready -U lingo; do sleep 1; done'
	docker compose exec postgres psql -U lingo -tc "SELECT 1 FROM pg_database WHERE datname='lingo_test'" | grep -q 1 || \
		docker compose exec postgres psql -U lingo -c "CREATE DATABASE lingo_test"

db-down:
	docker compose down
