"""GET /api/v1/features — exposes feature flags to the frontend."""

from fastapi import APIRouter

from lingo.config import settings

router = APIRouter(prefix="/api/v1/features", tags=["features"])


@router.get("")
async def get_features() -> dict[str, bool]:
    """Return the current feature flag state. No auth required — this is public config."""
    return {
        "discovery": settings.feature_discovery,
        "relationships": settings.feature_relationships,
        "voting": settings.feature_voting,
        "staleness": settings.feature_staleness,
    }
