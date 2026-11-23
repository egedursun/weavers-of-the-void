from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.site import (
    BattlefieldFeature,
    ExcavationFind,
    ExcavationRisk,
    ExcavationStage,
    ExcavationStatus,
    RoomContentKind,
    SiteChallenge,
    SiteRoomKind,
)

ROOM_FIELDS = ("kind", "challenge", "difficulty", "cleared_epoch", "position")
EXCAVATION_FIELDS = ("stage", "status", "progress", "leader_entity_id", "sponsor_node_id")
STAGE_FIELDS = ("skill", "technique", "difficulty", "risk", "find")
FEATURE_FIELDS = ("strength",)


class SiteRoomRow(Base):
    __tablename__ = "site_rooms"
    __table_args__ = (
        between("difficulty", PERCENT_MIN, PERCENT_MAX),
        at_least("position", 0),
        Index("ix_site_rooms_site", "site_entity_id", "position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    site_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(default=0)
    kind: Mapped[SiteRoomKind] = mapped_column(enum_type(SiteRoomKind, "kind"))
    challenge: Mapped[SiteChallenge] = mapped_column(enum_type(SiteChallenge, "challenge"), default=SiteChallenge.NONE)
    difficulty: Mapped[int] = mapped_column(default=0)
    cleared_epoch: Mapped[int | None]
    cleared_by_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class RoomContentRow(Base):
    __tablename__ = "room_contents"
    __table_args__ = (Index("ix_room_contents_room", "room_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("site_rooms.id", ondelete="CASCADE"))
    kind: Mapped[RoomContentKind] = mapped_column(enum_type(RoomContentKind, "kind"))
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    strength: Mapped[int] = mapped_column(default=0)
    locked: Mapped[bool] = mapped_column(default=False)


class SiteHolderRow(Base):
    __tablename__ = "site_holders"
    __table_args__ = (at_least("from_epoch", 0), Index("ix_site_holders_site", "site_entity_id", "from_epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    site_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    from_epoch: Mapped[int]
    to_epoch: Mapped[int | None]
    how: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class ExcavationRow(Base):
    __tablename__ = "excavations"
    __table_args__ = (
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("started_epoch", 0),
        at_least("idle_epochs", 0),
        Index("ix_excavations_site", "site_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    site_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    stage: Mapped[ExcavationStage] = mapped_column(enum_type(ExcavationStage, "stage"), default=ExcavationStage.SURVEY)
    status: Mapped[ExcavationStatus] = mapped_column(enum_type(ExcavationStatus, "status"), default=ExcavationStatus.OPEN)
    progress: Mapped[int] = mapped_column(default=0)
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sponsor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    started_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    idle_epochs: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(Text)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExcavationStageRow(Base):
    __tablename__ = "excavation_stages"
    __table_args__ = (between("difficulty", PERCENT_MIN, PERCENT_MAX), Index("ix_excavation_stages_dig", "excavation_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    excavation_id: Mapped[int] = mapped_column(ForeignKey("excavations.id", ondelete="CASCADE"))
    stage: Mapped[ExcavationStage] = mapped_column(enum_type(ExcavationStage, "stage"))
    skill: Mapped[SkillKind] = mapped_column(enum_type(SkillKind, "skill"))
    technique: Mapped[Technique | None] = mapped_column(enum_type(Technique, "technique"))
    difficulty: Mapped[int] = mapped_column(default=0)
    risk: Mapped[ExcavationRisk] = mapped_column(enum_type(ExcavationRisk, "risk"), default=ExcavationRisk.NONE)
    find: Mapped[ExcavationFind] = mapped_column(enum_type(ExcavationFind, "find"), default=ExcavationFind.NOTHING)
    find_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    resolved_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BattlefieldFeatureRow(Base):
    __tablename__ = "battlefield_features"
    __table_args__ = (between("strength", PERCENT_MIN, PERCENT_MAX), Index("ix_battlefield_features_place", "place_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    place_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    feature: Mapped[BattlefieldFeature] = mapped_column(enum_type(BattlefieldFeature, "feature"))
    strength: Mapped[int] = mapped_column(default=0)
    battle_id: Mapped[int | None] = mapped_column(ForeignKey("battles.id", ondelete="SET NULL"))
    remnant_id: Mapped[int | None] = mapped_column(ForeignKey("war_remnants.id", ondelete="SET NULL"))
    epoch: Mapped[int]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
