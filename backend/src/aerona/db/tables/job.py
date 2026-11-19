from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import JOB_ID_LENGTH
from aerona.db.base import Base, TimestampMixin
from aerona.db.columns import enum_type
from aerona.db.types import UtcDateTime
from aerona.domain.enums.job import JobKind, JobStatus


class JobRow(TimestampMixin, Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(JOB_ID_LENGTH), primary_key=True)
    kind: Mapped[JobKind] = mapped_column(enum_type(JobKind, "kind"), index=True)
    status: Mapped[JobStatus] = mapped_column(enum_type(JobStatus, "status"), index=True)
    exclusive_group: Mapped[str | None] = mapped_column(String(32))
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    stage: Mapped[str | None] = mapped_column(String(200))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    finished_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
