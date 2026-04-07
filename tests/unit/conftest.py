"""Shared fixtures for unit tests using async SQLite in-memory DB."""
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from lingo.models.base import Base
from lingo.models import User, Term  # ensure all models registered
from lingo.config import settings


@pytest.fixture(autouse=True)
def enable_all_features():
    """Enable every feature flag for unit tests so existing route tests keep passing."""
    prev = {
        "feature_staleness": settings.feature_staleness,
        "feature_relationships": settings.feature_relationships,
        "feature_voting": settings.feature_voting,
        "feature_discovery": settings.feature_discovery,
    }
    settings.feature_staleness = True
    settings.feature_relationships = True
    settings.feature_voting = True
    settings.feature_discovery = True
    yield
    for k, v in prev.items():
        setattr(settings, k, v)


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
