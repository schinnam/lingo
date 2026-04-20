from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[object] = uuid_pk()
    name: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String, nullable=True)
    definition: Mapped[str] = mapped_column(String(2000), nullable=False)
    category: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_channel_id: Mapped[str | None] = mapped_column(String, nullable=True)
    occurrences_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    owner_id: Mapped[object | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    owned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_stale: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[object | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now(), nullable=True
    )

    def __init__(self, **kwargs):
        if "is_stale" not in kwargs:
            kwargs["is_stale"] = False
        if "version" not in kwargs:
            kwargs["version"] = 1
        super().__init__(**kwargs)
