from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Uuid

from lingo.models.base import Base


class Vote(Base):
    __tablename__ = "votes"

    term_id: Mapped[object] = mapped_column(
        Uuid, ForeignKey("terms.id"), primary_key=True
    )
    user_id: Mapped[object] = mapped_column(
        Uuid, ForeignKey("users.id"), primary_key=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
