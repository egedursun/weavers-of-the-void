from sqlalchemy import JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.city_rules import ConurbationGovernance, LandUseRule, MunicipalService, RuleMaker
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN


class LandUseRuleRow(Base):
    __tablename__ = "land_use_rules"
    __table_args__ = (
        between("strength", PERCENT_MIN, PERCENT_MAX),
        between("enforcement", PERCENT_MIN, PERCENT_MAX),
        between("evasion", PERCENT_MIN, PERCENT_MAX),
        Index("ix_land_use_rules_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id", ondelete="CASCADE"))
    ring: Mapped[int | None]
    rule: Mapped[LandUseRule] = mapped_column(enum_type(LandUseRule, "rule"), default=LandUseRule.FIRE_SPACING)
    values: Mapped[dict[str, int | str | list[str]]] = mapped_column(JSON, default=dict)
    maker: Mapped[RuleMaker] = mapped_column(enum_type(RuleMaker, "maker"), default=RuleMaker.COUNCIL)
    maker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=50)
    enforcement: Mapped[int] = mapped_column(default=50)
    evasion: Mapped[int] = mapped_column(default=0)
    set_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MunicipalServiceRow(Base):
    __tablename__ = "municipal_services"
    __table_args__ = (
        between("quality", PERCENT_MIN, PERCENT_MAX),
        at_least("budget", 0),
        at_least("cost", 0),
        Index("ix_municipal_services_settlement", "settlement_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    service: Mapped[MunicipalService] = mapped_column(enum_type(MunicipalService, "service"), default=MunicipalService.REFUSE)
    provider_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    coverage: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    budget: Mapped[int] = mapped_column(default=0)
    cost: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int] = mapped_column(default=50)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    failed_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ConurbationRow(Base):
    __tablename__ = "conurbations"
    __table_args__ = (Index("ix_conurbations_core", "core_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    core_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    members: Mapped[list[int]] = mapped_column(JSON, default=list)
    governance: Mapped[ConurbationGovernance] = mapped_column(enum_type(ConurbationGovernance, "governance"), default=ConurbationGovernance.FEDERATED_COUNCILS)
    imposed_laws: Mapped[list[int]] = mapped_column(JSON, default=list)
    joined_epoch: Mapped[int] = mapped_column(default=0)
    split_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
