from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.catalog.chronicle import NOTIFICATION_SEVERITY_MAX, NOTIFICATION_SEVERITY_MIN
from aerona.constants.media import MEDIA_KEY_MAX_LENGTH, ORIGINALS_PREFIX, SHA256_HEX_LENGTH
from aerona.constants.schema import (
    IMAGE_FILE_NAME_MAX_LENGTH,
    JOB_ID_LENGTH,
    MAP_NOTE_COLOR_MAX_LENGTH,
    MAP_NOTE_MAX_LENGTH,
    NOTIFICATION_BODY_MAX_LENGTH,
    NOTIFICATION_TITLE_MAX_LENGTH,
    TITLE_MAX_LENGTH,
)
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, between, enum_type, max_length
from aerona.db.types import PydanticJSON
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.meta import AchievementKey, ImageMime, ImageOrigin, ScenarioKey, ScenarioStatus
from aerona.domain.models.records import MapSnapshotData, ScoreBreakdown


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        CheckConstraint("status = 'running' OR end_epoch IS NOT NULL", name="finished_has_epoch"),
        Index("ux_scenarios_running_key", "key", unique=True, sqlite_where=text("status = 'running'")),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[ScenarioKey] = mapped_column(enum_type(ScenarioKey, "key"))
    status: Mapped[ScenarioStatus] = mapped_column(enum_type(ScenarioStatus, "status"), default=ScenarioStatus.RUNNING)
    start_epoch: Mapped[int]
    end_epoch: Mapped[int | None]
    counter: Mapped[int] = mapped_column(default=0)
    baseline_entity_id: Mapped[int | None]
    baseline_chronicle_id: Mapped[int | None]
    baseline_count: Mapped[int | None]
    baseline_rebel_ids: Mapped[list[int]] = mapped_column(PydanticJSON(list[int]), default=list)
    points_awarded: Mapped[bool] = mapped_column(default=False)
    result: Mapped[str | None] = mapped_column(Text)


class AchievementRow(CreatedAtMixin, Base):
    __tablename__ = "achievements"

    key: Mapped[AchievementKey] = mapped_column(enum_type(AchievementKey, "key"), primary_key=True)
    epoch: Mapped[int]


class ScoreRow(CreatedAtMixin, Base):
    __tablename__ = "scores"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    total: Mapped[int]
    breakdown: Mapped[ScoreBreakdown] = mapped_column(PydanticJSON(ScoreBreakdown))


class NotificationRow(CreatedAtMixin, Base):
    __tablename__ = "notifications"
    __table_args__ = (
        between("severity", NOTIFICATION_SEVERITY_MIN, NOTIFICATION_SEVERITY_MAX),
        max_length("title", NOTIFICATION_TITLE_MAX_LENGTH),
        max_length("body", NOTIFICATION_BODY_MAX_LENGTH),
        Index("ix_notifications_unread", "is_read", "id"),
        Index("ix_notifications_category", "category", "id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int | None]
    category: Mapped[NotificationCategory] = mapped_column(enum_type(NotificationCategory, "category"))
    severity: Mapped[int]
    title: Mapped[str] = mapped_column(String(NOTIFICATION_TITLE_MAX_LENGTH))
    body: Mapped[str | None] = mapped_column(Text)
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    chronicle_id: Mapped[int | None] = mapped_column(ForeignKey("chronicle.id", ondelete="CASCADE"))
    is_read: Mapped[bool] = mapped_column(default=False)
    job_id: Mapped[str | None] = mapped_column(String(JOB_ID_LENGTH))


class MapSnapshotRow(CreatedAtMixin, Base):
    __tablename__ = "map_snapshots"

    epoch: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    data: Mapped[MapSnapshotData] = mapped_column(PydanticJSON(MapSnapshotData))


class MapNoteRow(CreatedAtMixin, Base):
    __tablename__ = "map_notes"
    __table_args__ = (max_length("text", MAP_NOTE_MAX_LENGTH), Index("ix_map_notes_world", "world_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    x: Mapped[float]
    y: Mapped[float]
    text: Mapped[str] = mapped_column(String(MAP_NOTE_MAX_LENGTH))
    color: Mapped[str | None] = mapped_column(String(MAP_NOTE_COLOR_MAX_LENGTH))


class ImageRow(CreatedAtMixin, Base):
    __tablename__ = "images"
    __table_args__ = (
        CheckConstraint("file_name NOT LIKE '%/%' AND file_name NOT LIKE '%..%' AND file_name NOT LIKE '.%'", name="safe_file_name"),
        CheckConstraint(f"object_key LIKE '{ORIGINALS_PREFIX}%' AND object_key NOT LIKE '%..%'", name="original_object_key"),
        CheckConstraint(f"length(sha256) = {SHA256_HEX_LENGTH}", name="sha256_length"),
        at_least("size_bytes", 0),
        Index("ix_images_target", "target_node_id", "is_cover", "id"),
        Index("ix_images_object_key", "object_key"),
        Index("ix_images_sha256", "sha256"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    target_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    file_name: Mapped[str] = mapped_column(String(IMAGE_FILE_NAME_MAX_LENGTH), unique=True)
    object_key: Mapped[str] = mapped_column(String(MEDIA_KEY_MAX_LENGTH))
    sha256: Mapped[str] = mapped_column(String(SHA256_HEX_LENGTH))
    mime: Mapped[ImageMime] = mapped_column(enum_type(ImageMime, "mime"))
    origin: Mapped[ImageOrigin] = mapped_column(enum_type(ImageOrigin, "origin"), default=ImageOrigin.GENERATED)
    caption: Mapped[str | None] = mapped_column(String(TITLE_MAX_LENGTH))
    prompt: Mapped[str | None] = mapped_column(Text)
    is_cover: Mapped[bool] = mapped_column(default=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int | None]
    height: Mapped[int | None]
