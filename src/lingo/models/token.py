from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class Token(Base):
    __tablename__ = "tokens"

    id: Mapped[object] = uuid_pk()
    user_id: Mapped[Optional[object]] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )
    name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    token_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    scopes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
