"""Pydantic request/response schemas."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Term schemas
# ---------------------------------------------------------------------------

class TermCreate(BaseModel):
    name: str
    definition: str = Field(..., max_length=2000)
    full_name: Optional[str] = None
    category: Optional[str] = None


class TermUpdate(BaseModel):
    version: int
    definition: Optional[str] = Field(None, max_length=2000)
    full_name: Optional[str] = None
    category: Optional[str] = None
    change_note: Optional[str] = Field(None, max_length=280)


class TermResponse(BaseModel):
    id: UUID
    name: str
    full_name: Optional[str]
    definition: str
    category: Optional[str]
    status: str
    source: str
    is_stale: bool
    version: int
    vote_count: int = 0
    owner_id: Optional[UUID] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Vote schemas
# ---------------------------------------------------------------------------

class VoteResponse(BaseModel):
    vote_count: int
    transition: Optional[str] = None


# ---------------------------------------------------------------------------
# History schemas
# ---------------------------------------------------------------------------

class HistoryResponse(BaseModel):
    id: UUID
    term_id: UUID
    definition: Optional[str]
    full_name: Optional[str]
    category: Optional[str]
    status: Optional[str]
    changed_by: UUID
    change_note: Optional[str]

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
    display_name: Optional[str]
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
    name: Optional[str]
    scopes: Optional[list]
    user_id: Optional[UUID]

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
    progress_json: Optional[dict]
    error: Optional[str]

    model_config = {"from_attributes": True}
