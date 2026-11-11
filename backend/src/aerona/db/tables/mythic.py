from sqlalchemy import JSON, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.mind import ActKind
from aerona.domain.enums.mythic import (
    CosmicOffice,
    GeasLayer,
    GeasMode,
    GeasState,
    HeroquestBoon,
    HeroquestState,
    MantlingState,
    MythicRealm,
    OfficeChoice,
    ServitorOrigin,
    ServitorRank,
    ServitorRole,
)

HEROQUEST_FIELDS = ("realm", "place_entity_id", "steps", "step", "fidelity", "deviated", "state", "boon", "interference")
MANTLING_FIELDS = ("god_node_id", "deeds", "worship", "progress", "state", "blocked")
SERVITOR_FIELDS = ("god_node_id", "rank", "origin", "role", "post_entity_id", "loyalty", "fallen_to_node_id")
GEAS_FIELDS = ("layer_node_id", "layer", "mode", "act", "state", "favour", "last_kept_epoch")
OFFICE_FIELDS = ("holder_node_id", "chosen_by", "since_epoch", "neglect", "duty")


class HeroquestRow(Base):
    __tablename__ = "heroquests"
    __table_args__ = (
        at_least("steps", 1),
        at_least("step", 0),
        between("fidelity", PERCENT_MIN, PERCENT_MAX),
        between("interference", PERCENT_MIN, PERCENT_MAX),
        at_least("start_epoch", 0),
        Index("ix_heroquests_quester", "quester_entity_id"),
        Index("ix_heroquests_state", "state"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    quester_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    legend_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    god_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    realm: Mapped[MythicRealm] = mapped_column(enum_type(MythicRealm, "realm"), default=MythicRealm.SACRED_SITE)
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    steps: Mapped[int] = mapped_column(default=3)
    step: Mapped[int] = mapped_column(default=0)
    fidelity: Mapped[int] = mapped_column(default=100)
    deviated: Mapped[bool] = mapped_column(default=False)
    state: Mapped[HeroquestState] = mapped_column(enum_type(HeroquestState, "state"), default=HeroquestState.QUESTING)
    boon: Mapped[HeroquestBoon | None] = mapped_column(enum_type(HeroquestBoon, "boon"))
    interference: Mapped[int] = mapped_column(default=0)
    collection_id: Mapped[int | None] = mapped_column(ForeignKey("incident_collections.id", ondelete="SET NULL"))
    start_epoch: Mapped[int] = mapped_column(default=0)
    end_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class HeroquestMemberRow(Base):
    __tablename__ = "heroquest_members"

    heroquest_id: Mapped[int] = mapped_column(Integer, ForeignKey("heroquests.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)


class MantlingRow(Base):
    __tablename__ = "mantlings"
    __table_args__ = (
        at_least("deeds", 0),
        at_least("worship", 0),
        between("progress", PERCENT_MIN, PERCENT_MAX),
        at_least("since_epoch", 0),
        Index("ix_mantlings_god", "god_node_id"),
    )

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    deeds: Mapped[int] = mapped_column(default=0)
    worship: Mapped[int] = mapped_column(default=0)
    progress: Mapped[int] = mapped_column(default=0)
    state: Mapped[MantlingState] = mapped_column(enum_type(MantlingState, "state"), default=MantlingState.WALKING)
    blocked: Mapped[bool] = mapped_column(default=False)
    notified: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ServitorRow(Base):
    __tablename__ = "servitors"
    __table_args__ = (between("loyalty", PERCENT_MIN, PERCENT_MAX), at_least("since_epoch", 0), Index("ix_servitors_god", "god_node_id"))

    spirit_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    god_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    rank: Mapped[ServitorRank] = mapped_column(enum_type(ServitorRank, "rank"), default=ServitorRank.HERALD)
    origin: Mapped[ServitorOrigin] = mapped_column(enum_type(ServitorOrigin, "origin"), default=ServitorOrigin.MADE)
    role: Mapped[ServitorRole] = mapped_column(enum_type(ServitorRole, "role"), default=ServitorRole.MESSENGER)
    post_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    loyalty: Mapped[int] = mapped_column(default=80)
    fallen_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GeasRow(Base):
    __tablename__ = "geasa"
    __table_args__ = (
        at_least("laid_epoch", 0),
        between("favour", PERCENT_MIN, PERCENT_MAX),
        Index("ix_geasa_bearer", "bearer_entity_id"),
        Index("ix_geasa_act", "act"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    layer_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    layer: Mapped[GeasLayer] = mapped_column(enum_type(GeasLayer, "layer"), default=GeasLayer.GOD)
    mode: Mapped[GeasMode] = mapped_column(enum_type(GeasMode, "mode"), default=GeasMode.TABOO)
    act: Mapped[ActKind] = mapped_column(enum_type(ActKind, "act"))
    state: Mapped[GeasState] = mapped_column(enum_type(GeasState, "state"), default=GeasState.KEPT)
    favour: Mapped[int] = mapped_column(default=0)
    laid_epoch: Mapped[int] = mapped_column(default=0)
    last_kept_epoch: Mapped[int] = mapped_column(default=0)
    broken_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CosmicOfficeRow(Base):
    __tablename__ = "cosmic_offices"
    __table_args__ = (between("neglect", PERCENT_MIN, PERCENT_MAX), between("duty", PERCENT_MIN, PERCENT_MAX))

    office: Mapped[CosmicOffice] = mapped_column(enum_type(CosmicOffice, "office"), primary_key=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    chosen_by: Mapped[OfficeChoice] = mapped_column(enum_type(OfficeChoice, "chosen_by"), default=OfficeChoice.CREATOR)
    since_epoch: Mapped[int | None]
    neglect: Mapped[int] = mapped_column(default=0)
    duty: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
