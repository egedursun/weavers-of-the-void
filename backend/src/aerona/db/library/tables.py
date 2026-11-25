from datetime import datetime

from sqlalchemy import JSON, BigInteger, Index, MetaData, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from aerona.constants.library import UNIVERSE_ID_LENGTH, UNIVERSE_NAME_MAX_LENGTH
from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import NAMING_CONVENTION
from aerona.db.columns import at_least, enum_type
from aerona.db.types import UtcDateTime
from aerona.domain.enums.library import LibraryEventKind, UniverseOrigin, UniverseStatus


class LibraryBase(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UniverseRow(LibraryBase):
    __tablename__ = "universes"
    __table_args__ = (
        at_least("epoch", 0),
        at_least("population", 0),
        at_least("sons", 0),
        at_least("size_bytes", 0),
        Index("ix_universes_status", "status"),
        Index("ix_universes_opened_at", "opened_at"),
    )

    id: Mapped[str] = mapped_column(String(UNIVERSE_ID_LENGTH), primary_key=True)
    name: Mapped[str] = mapped_column(String(UNIVERSE_NAME_MAX_LENGTH))
    summary: Mapped[str] = mapped_column(Text, default="", server_default="")
    notes: Mapped[str] = mapped_column(Text, default="", server_default="")
    cover_path: Mapped[str | None] = mapped_column(Text)
    status: Mapped[UniverseStatus] = mapped_column(enum_type(UniverseStatus, "status"), default=UniverseStatus.ACTIVE)
    pinned: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    opened_at: Mapped[datetime | None] = mapped_column(UtcDateTime())
    updated_at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    epoch: Mapped[int] = mapped_column(default=0)
    year: Mapped[int] = mapped_column(default=0)
    population: Mapped[int] = mapped_column(BigInteger, default=0)
    sons: Mapped[int] = mapped_column(default=0)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    schema_revision: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")
    app_version: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")
    origin: Mapped[UniverseOrigin] = mapped_column(enum_type(UniverseOrigin, "origin"), default=UniverseOrigin.CREATED)
    origin_note: Mapped[str] = mapped_column(Text, default="", server_default="")
    tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    media_prefix: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="", server_default="")


class LibraryEventRow(LibraryBase):
    __tablename__ = "library_events"
    __table_args__ = (Index("ix_library_events_universe_id", "universe_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    at: Mapped[datetime] = mapped_column(UtcDateTime(), server_default=func.now())
    kind: Mapped[LibraryEventKind] = mapped_column(enum_type(LibraryEventKind, "kind"))
    universe_id: Mapped[str] = mapped_column(String(UNIVERSE_ID_LENGTH))
    universe_name: Mapped[str] = mapped_column(String(UNIVERSE_NAME_MAX_LENGTH))
    detail: Mapped[str] = mapped_column(Text, default="", server_default="")
