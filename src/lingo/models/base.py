import uuid
from datetime import UTC, datetime

from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase, MappedColumn, mapped_column


class Base(DeclarativeBase):
    pass


def uuid_pk() -> MappedColumn:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


def now_utc() -> datetime:
    return datetime.now(UTC)
