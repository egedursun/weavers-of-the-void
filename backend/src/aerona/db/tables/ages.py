from sqlalchemy import JSON, ForeignKey, Index, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.ages import (
    ArcOutcome,
    ArcRole,
    ArcStage,
    ArcTemplate,
    FormationZone,
    GiantMigration,
    PayoffKind,
    SeasonCause,
    SeasonSpell,
    SetupKind,
)
from aerona.domain.enums.cosmography import ApocalypseVariant
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN

FORMATION_FIELDS = ("zone", "migration", "bombardment", "craters", "core_share", "mantle_heat", "water_delivered", "exotic_delivered")
SEASON_FIELDS = ("cause", "spell", "spell_started_epoch", "spell_length", "severity")
FORECAST_FIELDS = ("scholar_entity_id", "predicted_end_epoch", "heeded")
TRANSFORMATION_FIELDS = ("target_moisture", "target_forest", "target_fertility", "regions_changed", "resistance", "sabotage")
AGE_FIELDS = ("number", "began_epoch", "ended_epoch", "variant", "carried")
ECHO_FIELDS = ("template", "role", "source_node_id", "echo_node_id", "weight")
ARC_FIELDS = ("template", "stage", "outcome", "beats", "drama", "ended_epoch")
FIGURE_FIELDS = ("role",)
BEAT_FIELDS = ("stage", "text")
SETUP_FIELDS = ("kind", "subject_node_id", "payoff", "paid_epoch", "payoff_text")


class FormationHistoryRow(Base):
    __tablename__ = "formation_histories"
    __table_args__ = (
        between("bombardment", PERCENT_MIN, PERCENT_MAX),
        at_least("craters", 0),
        between("core_share", PERCENT_MIN, PERCENT_MAX),
        between("mantle_heat", PERCENT_MIN, PERCENT_MAX),
        between("water_delivered", PERCENT_MIN, PERCENT_MAX),
        between("exotic_delivered", PERCENT_MIN, PERCENT_MAX),
    )

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    zone: Mapped[FormationZone] = mapped_column(enum_type(FormationZone, "zone"), default=FormationZone.INNER)
    migration: Mapped[GiantMigration] = mapped_column(enum_type(GiantMigration, "migration"), default=GiantMigration.NONE)
    bombardment: Mapped[int] = mapped_column(default=30)
    craters: Mapped[int] = mapped_column(default=0)
    core_share: Mapped[int] = mapped_column(default=30)
    mantle_heat: Mapped[int] = mapped_column(default=50)
    water_delivered: Mapped[int] = mapped_column(default=30)
    exotic_delivered: Mapped[int] = mapped_column(default=0)
    shaped: Mapped[bool] = mapped_column(default=False)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"), index=True)


class IrregularSeasonRow(Base):
    __tablename__ = "irregular_seasons"
    __table_args__ = (at_least("spell_started_epoch", 0), at_least("spell_length", 1), between("severity", PERCENT_MIN, PERCENT_MAX))

    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"), primary_key=True)
    cause: Mapped[SeasonCause] = mapped_column(enum_type(SeasonCause, "cause"), default=SeasonCause.ORBIT)
    spell: Mapped[SeasonSpell] = mapped_column(enum_type(SeasonSpell, "spell"), default=SeasonSpell.SUMMER)
    spell_started_epoch: Mapped[int] = mapped_column(default=0)
    spell_length: Mapped[int] = mapped_column(default=2)
    severity: Mapped[int] = mapped_column(default=50)
    by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WinterForecastRow(Base):
    __tablename__ = "winter_forecasts"
    __table_args__ = (
        UniqueConstraint("world_id", "people_entity_id", name="uq_winter_forecasts_world_people"),
        Index("ix_winter_forecasts_people", "people_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    scholar_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    predicted_end_epoch: Mapped[int] = mapped_column(default=0)
    heeded: Mapped[bool] = mapped_column(default=False)
    made_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EcoTransformationRow(Base):
    __tablename__ = "eco_transformations"
    __table_args__ = (
        between("target_moisture", PERCENT_MIN, PERCENT_MAX),
        between("target_forest", PERCENT_MIN, PERCENT_MAX),
        between("target_fertility", PERCENT_MIN, PERCENT_MAX),
        at_least("regions_changed", 0),
        between("resistance", PERCENT_MIN, PERCENT_MAX),
        at_least("sabotage", 0),
    )

    plan_id: Mapped[int] = mapped_column(ForeignKey("long_plans.id", ondelete="CASCADE"), primary_key=True)
    target_moisture: Mapped[int] = mapped_column(default=60)
    target_forest: Mapped[int] = mapped_column(default=50)
    target_fertility: Mapped[int] = mapped_column(default=60)
    regions_changed: Mapped[int] = mapped_column(default=0)
    resistance: Mapped[int] = mapped_column(default=0)
    sabotage: Mapped[int] = mapped_column(default=0)
    last_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AgeRow(Base):
    __tablename__ = "ages"
    __table_args__ = (at_least("number", 1), at_least("began_epoch", 0), between("carried", PERCENT_MIN, PERCENT_MAX))

    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[int] = mapped_column(default=1)
    began_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    variant: Mapped[ApocalypseVariant | None] = mapped_column(enum_type(ApocalypseVariant, "variant"))
    carried: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AgeEchoRow(Base):
    __tablename__ = "age_echoes"
    __table_args__ = (between("weight", PERCENT_MIN, PERCENT_MAX), Index("ix_age_echoes_age", "age_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    age_id: Mapped[int] = mapped_column(ForeignKey("ages.id", ondelete="CASCADE"))
    template: Mapped[ArcTemplate] = mapped_column(enum_type(ArcTemplate, "template"))
    role: Mapped[ArcRole | None] = mapped_column(enum_type(ArcRole, "role"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    echo_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    weight: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArcRow(Base):
    __tablename__ = "arcs"
    __table_args__ = (
        at_least("beats", 0),
        between("drama", PERCENT_MIN, PERCENT_MAX),
        Index("ix_arcs_subject", "subject_node_id", "outcome"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    template: Mapped[ArcTemplate] = mapped_column(enum_type(ArcTemplate, "template"))
    stage: Mapped[ArcStage] = mapped_column(enum_type(ArcStage, "stage"), default=ArcStage.INCITING)
    outcome: Mapped[ArcOutcome] = mapped_column(enum_type(ArcOutcome, "outcome"), default=ArcOutcome.OPEN)
    beats: Mapped[int] = mapped_column(default=0)
    drama: Mapped[int] = mapped_column(default=0)
    echo_id: Mapped[int | None] = mapped_column(ForeignKey("age_echoes.id", ondelete="SET NULL"))
    started_epoch: Mapped[int] = mapped_column(default=0)
    last_beat_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArcFigureRow(Base):
    __tablename__ = "arc_figures"
    __table_args__ = (Index("ix_arc_figures_node", "node_id"),)

    arc_id: Mapped[int] = mapped_column(ForeignKey("arcs.id", ondelete="CASCADE"), primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[ArcRole] = mapped_column(enum_type(ArcRole, "role"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArcBeatRow(Base):
    __tablename__ = "arc_beats"
    __table_args__ = (Index("ix_arc_beats_arc", "arc_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    arc_id: Mapped[int] = mapped_column(ForeignKey("arcs.id", ondelete="CASCADE"))
    stage: Mapped[ArcStage] = mapped_column(enum_type(ArcStage, "stage"))
    text: Mapped[str] = mapped_column(Text, default="")
    line_id: Mapped[int | None] = mapped_column(ForeignKey("chronicle.id", ondelete="SET NULL"), index=True)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SetupRow(Base):
    __tablename__ = "setups"
    __table_args__ = (Index("ix_setups_subject", "subject_node_id", "payoff"), Index("ix_setups_source", "kind", "source_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[SetupKind] = mapped_column(enum_type(SetupKind, "kind"))
    source_id: Mapped[int] = mapped_column(default=0)
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    payoff: Mapped[PayoffKind] = mapped_column(enum_type(PayoffKind, "payoff"), default=PayoffKind.OPEN)
    opened_epoch: Mapped[int] = mapped_column(default=0)
    paid_epoch: Mapped[int | None]
    payoff_text: Mapped[str] = mapped_column(Text, default="")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
