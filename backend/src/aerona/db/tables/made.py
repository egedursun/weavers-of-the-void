from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH, NAME_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.body import BodyPart
from aerona.domain.enums.made import (
    Attribution,
    AugmentKind,
    AugmentMake,
    AugmentSlot,
    CompanyHoldingKind,
    DataContent,
    EffectTarget,
    IntrusionAim,
    IntrusionApproach,
    IntrusionOutcome,
    IntrusionTarget,
    RealmAwareness,
    RealmEntry,
    RealmPurpose,
    RelicState,
    RelicUse,
    ReplicatorOutput,
    ReplicatorScale,
    ReplicatorStage,
    SurveillanceFocus,
)
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.minds import MindOrigin, MindSeat, MindUpkeep
from aerona.domain.enums.society import Commodity

TIME_RATIO_MAX = 10000


class AugmentRow(Base):
    __tablename__ = "augments"
    __table_args__ = (
        between("quality", 0, 100),
        between("integration", 0, 100),
        between("strain", 0, 100),
        at_least("installed_epoch", 0),
        Index("ix_augments_bearer", "bearer_node_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bearer_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    slot: Mapped[AugmentSlot] = mapped_column(enum_type(AugmentSlot, "slot"), default=AugmentSlot.PART)
    part: Mapped[BodyPart | None] = mapped_column(enum_type(BodyPart, "part"))
    kind: Mapped[AugmentKind] = mapped_column(enum_type(AugmentKind, "kind"), default=AugmentKind.ENHANCEMENT)
    model_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    make: Mapped[AugmentMake] = mapped_column(enum_type(AugmentMake, "make"), default=AugmentMake.MADE)
    quality: Mapped[int] = mapped_column(default=50)
    upkeep: Mapped[MindUpkeep] = mapped_column(enum_type(MindUpkeep, "upkeep"), default=MindUpkeep.MAINTENANCE)
    integration: Mapped[int] = mapped_column(default=70)
    strain: Mapped[int] = mapped_column(default=0)
    installed_by_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    installed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AugmentEffectRow(Base):
    __tablename__ = "augment_effects"
    __table_args__ = (between("amount", -100, 100), Index("ix_augment_effects_augment", "augment_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    augment_id: Mapped[int] = mapped_column(ForeignKey("augments.id", ondelete="CASCADE"))
    target: Mapped[EffectTarget] = mapped_column(enum_type(EffectTarget, "target"))
    target_key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    amount: Mapped[int] = mapped_column(default=10)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MadeRealmRow(Base):
    __tablename__ = "made_realm_profiles"
    __table_args__ = (between("time_ratio_pct", 1, TIME_RATIO_MAX), between("fidelity", 0, 100))

    dimension_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    host_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    keeper_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    realm_purpose: Mapped[RealmPurpose] = mapped_column(enum_type(RealmPurpose, "realm_purpose"), default=RealmPurpose.DWELLING)
    time_ratio_pct: Mapped[int] = mapped_column(default=100)
    fidelity: Mapped[int] = mapped_column(default=70)
    entry: Mapped[RealmEntry] = mapped_column(enum_type(RealmEntry, "entry"), default=RealmEntry.TRANSFER)
    aware_inside: Mapped[RealmAwareness] = mapped_column(enum_type(RealmAwareness, "aware_inside"), default=RealmAwareness.KNOWS)
    upkeep: Mapped[MindUpkeep] = mapped_column(enum_type(MindUpkeep, "upkeep"), default=MindUpkeep.ENERGY)
    frozen_until_epoch: Mapped[int] = mapped_column(default=0)
    sealed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class IntrusionRow(Base):
    __tablename__ = "intrusions"
    __table_args__ = (between("stealth", 0, 100), between("detection", 0, 100), at_least("epoch", 0), Index("ix_intrusions_target", "target_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    target: Mapped[IntrusionTarget] = mapped_column(enum_type(IntrusionTarget, "target"))
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    approach: Mapped[IntrusionApproach] = mapped_column(enum_type(IntrusionApproach, "approach"), default=IntrusionApproach.TECHNICAL)
    aim: Mapped[IntrusionAim] = mapped_column(enum_type(IntrusionAim, "aim"), default=IntrusionAim.READ)
    stealth: Mapped[int] = mapped_column(default=50)
    detection: Mapped[int] = mapped_column(default=0)
    attribution: Mapped[Attribution] = mapped_column(enum_type(Attribution, "attribution"), default=Attribution.UNKNOWN)
    blamed_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    outcome: Mapped[IntrusionOutcome] = mapped_column(enum_type(IntrusionOutcome, "outcome"), default=IntrusionOutcome.SUCCEEDED)
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DataStoreRow(Base):
    __tablename__ = "data_stores"
    __table_args__ = (between("security", 0, 100),)

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    security: Mapped[int] = mapped_column(default=40)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DataStoreContentRow(Base):
    __tablename__ = "data_store_contents"
    __table_args__ = (at_least("epoch", 0), Index("ix_data_store_contents_store", "store_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("data_stores.id", ondelete="CASCADE"))
    content: Mapped[DataContent] = mapped_column(enum_type(DataContent, "content"))
    subject_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    reference: Mapped[int | None]
    epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SurveillanceProfileRow(Base):
    __tablename__ = "surveillance_profiles"
    __table_args__ = (between("capacity", 0, 100), between("reach_pct", 0, 100), at_least("updated_epoch", 0))

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    capacity: Mapped[int] = mapped_column(default=0)
    reach_pct: Mapped[int] = mapped_column(default=0)
    focus: Mapped[SurveillanceFocus] = mapped_column(enum_type(SurveillanceFocus, "focus"), default=SurveillanceFocus.CRIME)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class InformationTrustRow(Base):
    __tablename__ = "information_trust"
    __table_args__ = (between("information_trust", 0, 100), between("shared_account_pct", 0, 100))

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    information_trust: Mapped[int] = mapped_column(default=60)
    shared_account_pct: Mapped[int] = mapped_column(default=60)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CompanyHoldingRow(Base):
    __tablename__ = "company_holdings"
    __table_args__ = (Index("ix_company_holdings_company", "company_entity_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    holding_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    kind: Mapped[CompanyHoldingKind] = mapped_column(enum_type(CompanyHoldingKind, "kind"), default=CompanyHoldingKind.STRUCTURE)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CompanyPresenceRow(Base):
    __tablename__ = "company_presences"
    __table_args__ = (between("influence", 0, 100),)

    company_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    licensed: Mapped[bool] = mapped_column(default=True)
    influence: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class EnclaveRow(Base):
    __tablename__ = "enclaves"
    __table_args__ = (at_least("since_epoch", 0),)

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    company_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReplicatorLineRow(Base):
    __tablename__ = "replicator_lines"
    __table_args__ = (
        between("growth_pct", 0, 100),
        between("error_pct", 0, 100),
        between("containment", 0, 100),
        at_least("founded_epoch", 0),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    scale: Mapped[ReplicatorScale] = mapped_column(enum_type(ReplicatorScale, "scale"), default=ReplicatorScale.MACHINE)
    feedstock: Mapped[MaterialKind] = mapped_column(enum_type(MaterialKind, "feedstock"), default=MaterialKind.IRON)
    output: Mapped[ReplicatorOutput] = mapped_column(enum_type(ReplicatorOutput, "output"), default=ReplicatorOutput.COPIES)
    growth_pct: Mapped[int] = mapped_column(default=10)
    error_pct: Mapped[int] = mapped_column(default=2)
    set_id: Mapped[int | None] = mapped_column(ForeignKey("instruction_sets.id", ondelete="SET NULL"))
    containment: Mapped[int] = mapped_column(default=80)
    kill_switch: Mapped[bool] = mapped_column(default=True)
    owner_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    maker_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    mind_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    stage: Mapped[ReplicatorStage] = mapped_column(enum_type(ReplicatorStage, "stage"), default=ReplicatorStage.CONTAINED)
    drifted_from_id: Mapped[int | None] = mapped_column(ForeignKey("replicator_lines.id", ondelete="SET NULL"))
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ReplicatorPresenceRow(Base):
    __tablename__ = "replicator_presence"
    __table_args__ = (at_least("mass", 0), Index("ix_replicator_presence_line", "line_id"), Index("ix_replicator_presence_place", "place_node_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("replicator_lines.id", ondelete="CASCADE"))
    place_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"))
    mass: Mapped[int] = mapped_column(default=10)
    growth: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MarketScarcityRow(Base):
    __tablename__ = "market_scarcity"
    __table_args__ = (between("scarcity", 0, 100), at_least("updated_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[Commodity] = mapped_column(enum_type(Commodity, "commodity"), primary_key=True)
    scarcity: Mapped[int] = mapped_column(default=100)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PatternRightRow(Base):
    __tablename__ = "pattern_rights"
    __table_args__ = (at_least("licence_fee", 0), at_least("since_epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    commodity: Mapped[Commodity] = mapped_column(enum_type(Commodity, "commodity"))
    holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"), index=True)
    licence_fee: Mapped[int] = mapped_column(default=2)
    open: Mapped[bool] = mapped_column(default=False)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FabricationRow(Base):
    __tablename__ = "fabrication"
    __table_args__ = (between("share_pct", 0, 100), between("dividend_pct", 0, 100), at_least("updated_epoch", 0))

    settlement_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    share_pct: Mapped[int] = mapped_column(default=0)
    dividend_pct: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MadeRelicRow(Base):
    __tablename__ = "made_relics"
    __table_args__ = (between("make_knowledge", 0, 100), between("repair_knowledge", 0, 100), between("understood_pct", 0, 100))

    thing_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), primary_key=True)
    make_knowledge: Mapped[int] = mapped_column(default=0)
    repair_knowledge: Mapped[int] = mapped_column(default=0)
    function_state: Mapped[RelicState] = mapped_column(enum_type(RelicState, "function_state"), default=RelicState.WORKING)
    understood_pct: Mapped[int] = mapped_column(default=100)
    use: Mapped[RelicUse] = mapped_column(enum_type(RelicUse, "use"), default=RelicUse.AS_MADE)
    is_relic: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SalvageSiteRow(Base):
    __tablename__ = "salvage_sites"
    __table_args__ = (at_least("yield_left", 0),)

    site_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    yield_left: Mapped[int] = mapped_column(default=40)
    rights_holder_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    last_salvaged_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class PeopleSubstrateRow(Base):
    __tablename__ = "people_substrates"
    __table_args__ = (between("share_pct", 0, 100),)

    people_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    seat: Mapped[MindSeat] = mapped_column(enum_type(MindSeat, "seat"), primary_key=True)
    origin: Mapped[MindOrigin] = mapped_column(enum_type(MindOrigin, "origin"), primary_key=True)
    share_pct: Mapped[int] = mapped_column(default=100)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
