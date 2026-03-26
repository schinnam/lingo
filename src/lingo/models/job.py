import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from lingo.models.base import Base, uuid_pk


class JobType(str, enum.Enum):
    discovery = "discovery"
    staleness = "staleness"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[object] = uuid_pk()
    job_type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus), nullable=False, default=JobStatus.pending
    )
    progress_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    def __init__(self, **kwargs):
        if "status" not in kwargs:
            kwargs["status"] = JobStatus.pending
        super().__init__(**kwargs)
