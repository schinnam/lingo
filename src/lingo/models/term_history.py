from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class TermHistory(Base):
    __tablename__ = "term_history"

    id: Mapped[object] = uuid_pk()
    term_id: Mapped[object] = mapped_column(ForeignKey("terms.id"), nullable=False)
    definition: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    owner_id: Mapped[Optional[object]] = mapped_column(ForeignKey("users.id"), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    changed_by: Mapped[object] = mapped_column(ForeignKey("users.id"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    change_note: Mapped[Optional[str]] = mapped_column(String(280), nullable=True)
