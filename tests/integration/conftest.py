"""Integration test fixtures — real Postgres, no mocks."""
import os
import subprocess
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
import sqlalchemy
from httpx import AsyncClient, ASGITransport
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must be set before lingo modules are imported.
# Root conftest.py already sets LINGO_DEV_MODE=true.
TEST_DATABASE_URL = "postgresql+asyncpg://lingo:lingo@localhost:5432/lingo_test"
os.environ["LINGO_DATABASE_URL"] = TEST_DATABASE_URL

from lingo.db.session import get_session  # noqa: E402
from lingo.main import app  # noqa: E402
from lingo.models import User  # noqa: E402
from lingo.models.base import Base  # noqa: E402


# ---------------------------------------------------------------------------
# Lifespan override — skip scheduler and MCP for integration tests
# ---------------------------------------------------------------------------

@asynccontextmanager
async def _test_lifespan(app):
    yield


app.router.lifespan_context = _test_lifespan


# ---------------------------------------------------------------------------
# Run migrations once per session (sync fixture, no event loop issues)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def run_migrations():
    env = {**os.environ, "LINGO_DATABASE_URL": TEST_DATABASE_URL}
    repo_root = Path(__file__).parent.parent.parent
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
        raise RuntimeError(f"alembic upgrade head failed:\n{result.stderr}")


# ---------------------------------------------------------------------------
# Function-scoped engine (NullPool = no connection sharing across tests)
# ---------------------------------------------------------------------------

_TABLES = ", ".join(
    f'"{t.name}"' for t in reversed(Base.metadata.sorted_tables)
)


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    yield engine
    try:
        # Truncate all tables after each test for isolation
        async with engine.begin() as conn:
            await conn.execute(sqlalchemy.text("SET LOCAL lock_timeout = '5s'"))
            await conn.execute(
                sqlalchemy.text(f"TRUNCATE TABLE {_TABLES} RESTART IDENTITY CASCADE")
            )
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_user: a real member user inserted into Postgres
# ---------------------------------------------------------------------------

@pytest.fixture
async def test_user(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        user = User(email="testuser@example.com", display_name="Test User", role="member")
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


# ---------------------------------------------------------------------------
# client: httpx AsyncClient against the real FastAPI app + real DB
# ---------------------------------------------------------------------------

@pytest.fixture
async def client(db_engine):
    factory = async_sessionmaker(db_engine, expire_on_commit=False, class_=AsyncSession)

    async def _override_get_session():
        async with factory() as session:
            yield session

    original = app.dependency_overrides.get(get_session)
    app.dependency_overrides[get_session] = _override_get_session
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac
    finally:
        if original is None:
            app.dependency_overrides.pop(get_session, None)
        else:
            app.dependency_overrides[get_session] = original
