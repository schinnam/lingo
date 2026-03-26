"""Shared fixtures for unit tests using async SQLite in-memory DB."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from lingo.models.base import Base
from lingo.models import User, Term  # ensure all models registered


@pytest.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def session(engine):
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as sess:
        yield sess


@pytest.fixture
async def admin_user(session):
    user = User(email="admin@example.com", display_name="Admin", role="admin")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
async def member_user(session):
    user = User(email="member@example.com", display_name="Member", role="member")
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user
