import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, mapped_column, MappedColumn
from sqlalchemy import Uuid


class Base(DeclarativeBase):
    pass


def uuid_pk() -> MappedColumn:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
