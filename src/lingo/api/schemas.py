"""Pydantic request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Term schemas
# ---------------------------------------------------------------------------


class TermCreate(BaseModel):
    name: str
    definition: str = Field(..., max_length=2000)
    full_name: str | None = None
    category: str | None = None


class TermUpdate(BaseModel):
    version: int
    definition: str | None = Field(None, max_length=2000)
    full_name: str | None = None
    category: str | None = None
    change_note: str | None = Field(None, max_length=280)


class DisputeRequest(BaseModel):
    comment: str | None = Field(None, max_length=500)


class TermResponse(BaseModel):
    id: UUID
    name: str
    full_name: str | None
    definition: str
    category: str | None
    status: str
    source: str
    is_stale: bool
    is_disputed: bool = False
    version: int
    vote_count: int = 0
    owner_id: UUID | None = None

    model_config = {"from_attributes": True}


class TermsListResponse(BaseModel):
    items: list[TermResponse]
    total: int
    offset: int
    limit: int
    counts_by_status: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Vote schemas
# ---------------------------------------------------------------------------


class VoteResponse(BaseModel):
    vote_count: int
    transition: str | None = None


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------


class HistoryResponse(BaseModel):
    id: UUID
    term_id: UUID
    definition: str | None
    full_name: str | None
    category: str | None
    status: str | None
    changed_by: UUID
    change_note: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Relationship schemas
# ---------------------------------------------------------------------------

VALID_RELATIONSHIP_TYPES = {"depends_on", "supersedes", "related_to"}


class RelationshipCreate(BaseModel):
    related_term_id: UUID
    relationship_type: str = Field(..., pattern="^(depends_on|supersedes|related_to)$")


class RelationshipResponse(BaseModel):
    id: UUID
    term_id: UUID
    related_term_id: UUID
    relationship_type: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# User schemas
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class RolePatch(BaseModel):
    role: str = Field(..., pattern="^(member|editor|admin)$")


# ---------------------------------------------------------------------------
# Token schemas
# ---------------------------------------------------------------------------


class TokenCreate(BaseModel):
    name: str
    scopes: list[str] = Field(default_factory=lambda: ["read"])


class TokenResponse(BaseModel):
    id: UUID
    name: str | None
    scopes: list | None
    user_id: UUID | None

    model_config = {"from_attributes": True}


class TokenCreateResponse(TokenResponse):
    token: str  # raw token shown once


# ---------------------------------------------------------------------------
# Admin schemas
# ---------------------------------------------------------------------------


class StatsResponse(BaseModel):
    total_terms: int
    by_status: dict[str, int]
    total_users: int
    total_votes: int


class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: str
    progress_json: dict | None
    error: str | None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Audit schemas
# ---------------------------------------------------------------------------


class AuditEventResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    action: str
    target_type: str | None
    target_id: UUID | None
    payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
