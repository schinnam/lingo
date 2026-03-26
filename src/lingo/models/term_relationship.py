import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class RelationshipType(str, enum.Enum):
    depends_on = "depends_on"
    supersedes = "supersedes"
    related_to = "related_to"


class TermRelationship(Base):
    __tablename__ = "term_relationships"

    id: Mapped[object] = uuid_pk()
    term_id: Mapped[object] = mapped_column(ForeignKey("terms.id"), nullable=False)
    related_term_id: Mapped[object] = mapped_column(ForeignKey("terms.id"), nullable=False)
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType), nullable=False
    )
    created_by: Mapped[Optional[object]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
