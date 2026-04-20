from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class TermDefinition(Base):
    __tablename__ = "term_definitions"

    id: Mapped[object] = uuid_pk()
    term_id: Mapped[object] = mapped_column(ForeignKey("terms.id"), nullable=False)
    definition: Mapped[str] = mapped_column(String(2000), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    added_by: Mapped[object] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
