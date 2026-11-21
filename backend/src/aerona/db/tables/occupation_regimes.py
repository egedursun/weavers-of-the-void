from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.occupation_regimes import CollaborationFate, CollaborationKind, OccupationEnding, OccupationMeasure, OccupationRule


class OccupationRegimeRow(Base):
    __tablename__ = "occupation_regimes"
    __table_args__ = (
        between("tax_pct", PERCENT_MIN, PERCENT_MAX),
        between("levy_pct", PERCENT_MIN, PERCENT_MAX),
        between("labour_pct", PERCENT_MIN, PERCENT_MAX),
        at_least("settlers", 0),
        at_least("begun_epoch", 0),
        Index("ix_occupation_regimes_region", "region_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    occupier_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    owner_polity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    rule: Mapped[OccupationRule] = mapped_column(enum_type(OccupationRule, "rule"), default=OccupationRule.MILITARY)
    administrators: Mapped[list[int]] = mapped_column(JSON, default=list)
    imposed_laws: Mapped[list[int]] = mapped_column(JSON, default=list)
    tax_pct: Mapped[int] = mapped_column(default=50)
    levy_pct: Mapped[int] = mapped_column(default=100)
    labour_pct: Mapped[int] = mapped_column(default=0)
    settlers: Mapped[int] = mapped_column(default=0)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    ending: Mapped[OccupationEnding | None] = mapped_column(enum_type(OccupationEnding, "ending"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CollaborationRow(Base):
    __tablename__ = "collaborations"
    __table_args__ = (
        between("exposure", PERCENT_MIN, PERCENT_MAX),
        at_least("reward", 0),
        Index("ix_collaborations_regime", "regime_id"),
        Index("ix_collaborations_node", "collaborator_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    regime_id: Mapped[int] = mapped_column(ForeignKey("occupation_regimes.id", ondelete="CASCADE"))
    collaborator_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[CollaborationKind] = mapped_column(enum_type(CollaborationKind, "kind"), default=CollaborationKind.ADMINISTRATION)
    reward: Mapped[int] = mapped_column(default=10)
    exposure: Mapped[int] = mapped_column(default=0)
    fate: Mapped[CollaborationFate] = mapped_column(enum_type(CollaborationFate, "fate"), default=CollaborationFate.SERVING)
    begun_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OccupationMeasureRow(Base):
    __tablename__ = "occupation_measures"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        Index("ix_occupation_measures_regime", "regime_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    regime_id: Mapped[int] = mapped_column(ForeignKey("occupation_regimes.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    measure: Mapped[OccupationMeasure] = mapped_column(enum_type(OccupationMeasure, "measure"), default=OccupationMeasure.CURFEW)
    strength: Mapped[int] = mapped_column(default=50)
    epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
