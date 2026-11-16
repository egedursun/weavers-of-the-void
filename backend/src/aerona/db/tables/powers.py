from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.culture import MagicSource, RiteEffectKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.powers import (
    GiftedAttitude,
    GiftedStance,
    Learnability,
    PowerCost,
    PowerHazard,
    PowerOrigin,
    PowerState,
    PowerStructure,
    PowerTrigger,
    PowerVisibility,
    ResistanceKind,
    RestrictionKind,
    SourceAccess,
    SourceLawLevel,
    SourceLocus,
    SourceRelation,
    SourceRenewal,
    SystemRelation,
    TideCycle,
)

STRENGTH_MAX = 10


class PowerSourceRow(Base):
    __tablename__ = "power_sources"
    __table_args__ = (between("stability", 0, 100), Index("ix_power_sources_scope", "scope_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text, default="")
    scope_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    drawn_from: Mapped[SourceLocus] = mapped_column(enum_type(SourceLocus, "drawn_from"))
    renewal: Mapped[SourceRenewal] = mapped_column(enum_type(SourceRenewal, "renewal"), default=SourceRenewal.TIME)
    access: Mapped[SourceAccess] = mapped_column(enum_type(SourceAccess, "access"), default=SourceAccess.ANYONE)
    visibility: Mapped[PowerVisibility] = mapped_column(enum_type(PowerVisibility, "visibility"), default=PowerVisibility.SUBTLE)
    stability: Mapped[int] = mapped_column(default=60)
    built_in: Mapped[MagicSource | None] = mapped_column(enum_type(MagicSource, "built_in"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSourceCostRow(Base):
    __tablename__ = "power_source_costs"
    __table_args__ = (between("weight", 0, 100), UniqueConstraint("source_id", "cost", name="uq_power_source_costs"))

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    cost: Mapped[PowerCost] = mapped_column(enum_type(PowerCost, "cost"))
    weight: Mapped[int] = mapped_column(default=50)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSourceResistanceRow(Base):
    __tablename__ = "power_source_resistances"
    __table_args__ = (UniqueConstraint("source_id", "resistance", name="uq_power_source_resistances"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    resistance: Mapped[ResistanceKind] = mapped_column(enum_type(ResistanceKind, "resistance"))
    material: Mapped[MaterialKind | None] = mapped_column(enum_type(MaterialKind, "material"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSourceHazardRow(Base):
    __tablename__ = "power_source_hazards"
    __table_args__ = (between("weight", 0, 100), UniqueConstraint("source_id", "hazard", name="uq_power_source_hazards"))

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    hazard: Mapped[PowerHazard] = mapped_column(enum_type(PowerHazard, "hazard"))
    weight: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SourceDensityRow(Base):
    __tablename__ = "source_density"
    __table_args__ = (
        between("density", 0, 100),
        between("base_density", 0, 100),
        between("renewal_pct", 0, 100),
        UniqueConstraint("region_entity_id", "source_id", name="uq_source_density"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    density: Mapped[int] = mapped_column(default=50)
    base_density: Mapped[int] = mapped_column(default=50)
    renewal_pct: Mapped[int] = mapped_column(default=10)
    last_drawn_epoch: Mapped[int | None]
    depleted: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSourceInteractionRow(Base):
    __tablename__ = "power_source_interactions"
    __table_args__ = (between("strength", 0, 100), UniqueConstraint("first_source_id", "second_source_id", name="uq_power_source_interactions"))

    id: Mapped[int] = mapped_column(primary_key=True)
    first_source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    second_source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    relation: Mapped[SourceRelation] = mapped_column(enum_type(SourceRelation, "relation"))
    strength: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SourceTideRow(Base):
    __tablename__ = "source_tides"
    __table_args__ = (at_least("period", 1), between("amplitude", 0, 100), at_least("phase", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    cycle: Mapped[TideCycle] = mapped_column(enum_type(TideCycle, "cycle"))
    period: Mapped[int] = mapped_column(default=4)
    amplitude: Mapped[int] = mapped_column(default=30)
    phase: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSourceKnowledgeRow(Base):
    __tablename__ = "power_source_knowledge"
    __table_args__ = (between("level", 0, 100), UniqueConstraint("source_id", "holder_node_id", name="uq_power_source_knowledge"))

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    level: Mapped[int] = mapped_column(default=50)
    learned_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MagicSystemRow(Base):
    __tablename__ = "magic_systems"
    __table_args__ = (
        between("predictability", 0, 100),
        between("prevalence", 0, 100),
        between("cost_severity", 0, 100),
        Index("ix_magic_systems_scope", "scope_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text, default="")
    scope_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    structure: Mapped[PowerStructure] = mapped_column(enum_type(PowerStructure, "structure"))
    predictability: Mapped[int] = mapped_column(default=50)
    prevalence: Mapped[int] = mapped_column(default=50)
    cost_severity: Mapped[int] = mapped_column(default=50)
    visibility: Mapped[PowerVisibility] = mapped_column(enum_type(PowerVisibility, "visibility"), default=PowerVisibility.SUBTLE)
    access: Mapped[SourceAccess] = mapped_column(enum_type(SourceAccess, "access"), default=SourceAccess.ANYONE)
    learnability: Mapped[Learnability] = mapped_column(enum_type(Learnability, "learnability"), default=Learnability.ANYONE)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MagicSystemSourceRow(Base):
    __tablename__ = "magic_system_sources"
    __table_args__ = (UniqueConstraint("system_id", "source_id", name="uq_magic_system_sources"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("magic_systems.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MagicSystemLinkRow(Base):
    __tablename__ = "magic_system_links"
    __table_args__ = (UniqueConstraint("first_system_id", "second_system_id", name="uq_magic_system_links"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    first_system_id: Mapped[int] = mapped_column(ForeignKey("magic_systems.id", ondelete="CASCADE"), index=True)
    second_system_id: Mapped[int] = mapped_column(ForeignKey("magic_systems.id", ondelete="CASCADE"), index=True)
    relation: Mapped[SystemRelation] = mapped_column(enum_type(SystemRelation, "relation"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerRow(Base):
    __tablename__ = "powers"
    __table_args__ = (
        between("strength", 1, STRENGTH_MAX),
        between("control", 0, 100),
        at_least("range_km", 0),
        at_least("duration_days", 0),
        at_least("strain", 0),
        at_least("strain_cap", 1),
        Index("ix_powers_holder", "holder_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    system_id: Mapped[int | None] = mapped_column(ForeignKey("magic_systems.id", ondelete="SET NULL"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("power_sources.id", ondelete="SET NULL"))
    technique: Mapped[SpellTechnique] = mapped_column(enum_type(SpellTechnique, "technique"))
    form: Mapped[SpellForm] = mapped_column(enum_type(SpellForm, "form"))
    range_km: Mapped[int] = mapped_column(default=0)
    duration_days: Mapped[int] = mapped_column(default=0)
    on_others: Mapped[bool] = mapped_column(default=True)
    strength: Mapped[int] = mapped_column(default=3)
    control: Mapped[int] = mapped_column(default=40)
    origin: Mapped[PowerOrigin] = mapped_column(enum_type(PowerOrigin, "origin"), default=PowerOrigin.BORN)
    state: Mapped[PowerState] = mapped_column(enum_type(PowerState, "state"), default=PowerState.LATENT)
    visibility: Mapped[PowerVisibility] = mapped_column(enum_type(PowerVisibility, "visibility"), default=PowerVisibility.SUBTLE)
    strain: Mapped[int] = mapped_column(default=0)
    strain_cap: Mapped[int] = mapped_column(default=30)
    granted_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    item_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    uses: Mapped[int] = mapped_column(default=0)
    gained_epoch: Mapped[int] = mapped_column(default=0)
    last_used_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerRestrictionRow(Base):
    __tablename__ = "power_restrictions"
    __table_args__ = (between("strength_gain_pct", 0, 100),)

    id: Mapped[int] = mapped_column(primary_key=True)
    power_id: Mapped[int] = mapped_column(ForeignKey("powers.id", ondelete="CASCADE"), index=True)
    kind: Mapped[RestrictionKind] = mapped_column(enum_type(RestrictionKind, "kind"))
    ref_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    detail: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    strength_gain_pct: Mapped[int] = mapped_column(default=20)
    broken: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerTriggerRow(Base):
    __tablename__ = "power_triggers"
    __table_args__ = (UniqueConstraint("power_id", "trigger", name="uq_power_triggers"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    power_id: Mapped[int] = mapped_column(ForeignKey("powers.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[PowerTrigger] = mapped_column(enum_type(PowerTrigger, "trigger"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MagicSystemGrammarRow(Base):
    __tablename__ = "magic_system_grammar"
    __table_args__ = (UniqueConstraint("system_id", "technique", "form", name="uq_magic_system_grammar"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("magic_systems.id", ondelete="CASCADE"), index=True)
    technique: Mapped[SpellTechnique | None] = mapped_column(enum_type(SpellTechnique, "technique"))
    form: Mapped[SpellForm | None] = mapped_column(enum_type(SpellForm, "form"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SystemRestrictionRow(Base):
    __tablename__ = "magic_system_restrictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    system_id: Mapped[int] = mapped_column(ForeignKey("magic_systems.id", ondelete="CASCADE"), index=True)
    kind: Mapped[RestrictionKind] = mapped_column(enum_type(RestrictionKind, "kind"))
    detail: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerSpanRow(Base):
    __tablename__ = "power_spans"
    __table_args__ = (at_least("until_epoch", 0), Index("ix_power_spans_until", "until_epoch"))

    id: Mapped[int] = mapped_column(primary_key=True)
    power_id: Mapped[int | None] = mapped_column(ForeignKey("powers.id", ondelete="SET NULL"))
    user_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    effect: Mapped[RiteEffectKind] = mapped_column(enum_type(RiteEffectKind, "effect"))
    amount: Mapped[int] = mapped_column(default=0)
    prior: Mapped[int] = mapped_column(default=0)
    began_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class GiftedAttitudeRow(Base):
    __tablename__ = "gifted_attitudes"
    __table_args__ = (between("gifted_share", 0, 100), between("registered_share", 0, 100))

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    attitude: Mapped[GiftedAttitude] = mapped_column(enum_type(GiftedAttitude, "attitude"), default=GiftedAttitude.ORDINARY)
    gifted_share: Mapped[int] = mapped_column(default=0)
    registered_share: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PowerRegistryRow(Base):
    __tablename__ = "power_registry"
    __table_args__ = (UniqueConstraint("polity_entity_id", "holder_node_id", name="uq_power_registry"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    licensed: Mapped[bool] = mapped_column(default=False)
    conscripted: Mapped[bool] = mapped_column(default=False)
    registered_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SourceLawRow(Base):
    __tablename__ = "source_laws"
    __table_args__ = (UniqueConstraint("polity_entity_id", "source_id", name="uq_source_laws"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    level: Mapped[SourceLawLevel] = mapped_column(enum_type(SourceLawLevel, "level"), default=SourceLawLevel.FREE)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SourceStanceRow(Base):
    __tablename__ = "source_stances"
    __table_args__ = (UniqueConstraint("cult_entity_id", "source_id", name="uq_source_stances"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cult_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("power_sources.id", ondelete="CASCADE"), index=True)
    stance: Mapped[GiftedStance] = mapped_column(enum_type(GiftedStance, "stance"), default=GiftedStance.SILENT)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
