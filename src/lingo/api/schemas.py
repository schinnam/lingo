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

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Vote schemas
# ---------------------------------------------------------------------------

class VoteResponse(BaseModel):
    vote_count: int
    transition: Optional[str] = None
