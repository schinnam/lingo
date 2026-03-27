.PHONY: test test-unit test-integration db-up db-down

# Run all tests
test:
	uv run pytest

# Run unit tests only (no Docker required)
test-unit:
	uv run pytest tests/unit/

# Run integration tests (requires postgres container)
test-integration: db-up
	uv run pytest tests/integration/ -v

# Start the postgres container if not already running
db-up:
	docker compose up -d postgres
	docker compose exec postgres sh -c 'until pg_isready -U lingo; do sleep 1; done'
	docker compose exec postgres psql -U lingo -tc "SELECT 1 FROM pg_database WHERE datname='lingo_test'" | grep -q 1 || \
		docker compose exec postgres psql -U lingo -c "CREATE DATABASE lingo_test"

db-down:
	docker compose down
