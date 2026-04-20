from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class DefinitionSuggestion(Base):
    __tablename__ = "definition_suggestions"

    id: Mapped[object] = uuid_pk()
    term_id: Mapped[object] = mapped_column(ForeignKey("terms.id"), nullable=False)
    definition: Mapped[str] = mapped_column(String(2000), nullable=False)
    comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    suggested_by: Mapped[object] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )

    def __init__(self, **kwargs):
        if "status" not in kwargs:
            kwargs["status"] = "pending"
        super().__init__(**kwargs)
