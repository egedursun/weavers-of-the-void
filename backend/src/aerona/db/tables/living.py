from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.ecology import Temperament
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.living import CultivationMethod, Fertility, GrowthStage, HostPlacement, HostRelation, LineOutcome, LineTrait, Metabolism


class LivingLineRow(Base):
    __tablename__ = "living_lines"
    __table_args__ = (between("stability", 0, 100), between("drift_pct", 0, 100), at_least("generation", 0), Index("ix_living_lines_owner", "owner_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    method: Mapped[CultivationMethod] = mapped_column(enum_type(CultivationMethod, "method"))
    outcome: Mapped[LineOutcome] = mapped_column(enum_type(LineOutcome, "outcome"), default=LineOutcome.AS_MEANT)
    stability: Mapped[int] = mapped_column(default=70)
    generation: Mapped[int] = mapped_column(default=0)
    drift_pct: Mapped[int] = mapped_column(default=0)
    fertility: Mapped[Fertility] = mapped_column(enum_type(Fertility, "fertility"), default=Fertility.BREEDS_TRUE)
    metabolism: Mapped[Metabolism] = mapped_column(enum_type(Metabolism, "metabolism"), default=Metabolism.FEEDING)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    maker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    species_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    drifted_from_id: Mapped[int | None] = mapped_column(ForeignKey("living_lines.id", ondelete="SET NULL"))
    licensed: Mapped[bool] = mapped_column(default=False)
    escaped: Mapped[bool] = mapped_column(default=False)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LivingLineSourceRow(Base):
    __tablename__ = "living_line_sources"
    __table_args__ = (UniqueConstraint("line_id", "organism_node_id", name="uq_living_line_sources"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("living_lines.id", ondelete="CASCADE"), index=True)
    organism_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LivingLineTraitRow(Base):
    __tablename__ = "living_line_traits"
    __table_args__ = (between("strength", -100, 100), UniqueConstraint("line_id", "trait", name="uq_living_line_traits"))

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("living_lines.id", ondelete="CASCADE"), index=True)
    trait: Mapped[LineTrait] = mapped_column(enum_type(LineTrait, "trait"))
    strength: Mapped[int] = mapped_column(default=20)
    side_effect: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LivingProfileRow(Base):
    __tablename__ = "living_profiles"
    __table_args__ = (
        between("size_pct", 0, 400),
        between("regeneration", 0, 100),
        between("health", 0, 100),
        between("bond", 0, 100),
        at_least("feed_per_season", 0),
        at_least("lifespan_years", 0),
        at_least("age_seasons", 0),
        Index("ix_living_profiles_line", "line_id"),
    )

    thing_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    line_id: Mapped[int | None] = mapped_column(ForeignKey("living_lines.id", ondelete="SET NULL"))
    metabolism: Mapped[Metabolism] = mapped_column(enum_type(Metabolism, "metabolism"), default=Metabolism.FEEDING)
    feed_commodity: Mapped[CommodityKind | None] = mapped_column(enum_type(CommodityKind, "feed_commodity"))
    feed_per_season: Mapped[int] = mapped_column(default=1)
    growth_stage: Mapped[GrowthStage] = mapped_column(enum_type(GrowthStage, "growth_stage"), default=GrowthStage.SEED)
    size_pct: Mapped[int] = mapped_column(default=20)
    regeneration: Mapped[int] = mapped_column(default=20)
    health: Mapped[int] = mapped_column(default=100)
    temperament: Mapped[Temperament | None] = mapped_column(enum_type(Temperament, "temperament"))
    bonded_to_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    bond: Mapped[int] = mapped_column(default=50)
    fertility: Mapped[Fertility] = mapped_column(enum_type(Fertility, "fertility"), default=Fertility.BREEDS_TRUE)
    lifespan_years: Mapped[int] = mapped_column(default=40)
    age_seasons: Mapped[int] = mapped_column(default=0)
    designed_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    planted_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GeneBankRow(Base):
    __tablename__ = "gene_banks"
    __table_args__ = (at_least("upkeep", 0), at_least("unpaid_epochs", 0))

    structure_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    upkeep: Mapped[int] = mapped_column(default=2)
    unpaid_epochs: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GeneBankSampleRow(Base):
    __tablename__ = "gene_bank_samples"
    __table_args__ = (between("quality", 0, 100), UniqueConstraint("bank_entity_id", "organism_node_id", name="uq_gene_bank_samples"))

    id: Mapped[int] = mapped_column(primary_key=True)
    bank_entity_id: Mapped[int] = mapped_column(ForeignKey("gene_banks.structure_entity_id", ondelete="CASCADE"), index=True)
    organism_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    quality: Mapped[int] = mapped_column(default=80)
    taken_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SymbiontRow(Base):
    __tablename__ = "symbionts"
    __table_args__ = (between("strength", 0, 100), Index("ix_symbionts_host", "host_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    host_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    line_id: Mapped[int | None] = mapped_column(ForeignKey("living_lines.id", ondelete="SET NULL"))
    mind_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    placement: Mapped[HostPlacement] = mapped_column(enum_type(HostPlacement, "placement"))
    relation: Mapped[HostRelation] = mapped_column(enum_type(HostRelation, "relation"), default=HostRelation.MUTUAL)
    strength: Mapped[int] = mapped_column(default=30)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
