from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[object] = uuid_pk()
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    slack_user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    def __init__(self, **kwargs):
        if "is_active" not in kwargs:
            kwargs["is_active"] = True
        if "role" not in kwargs:
            kwargs["role"] = "member"
        super().__init__(**kwargs)
