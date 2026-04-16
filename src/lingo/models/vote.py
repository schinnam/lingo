from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base


class Vote(Base):
    __tablename__ = "votes"

    term_id: Mapped[object] = mapped_column(Uuid, ForeignKey("terms.id"), primary_key=True)
    user_id: Mapped[object] = mapped_column(Uuid, ForeignKey("users.id"), primary_key=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
