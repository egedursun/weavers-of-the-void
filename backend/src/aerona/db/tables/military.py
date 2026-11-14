from sqlalchemy import JSON, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.demography import CohortCondition, MartialStyle
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.military import (
    AgentStatus,
    ArmourType,
    ArmyRole,
    CaptiveFate,
    CasualtyFate,
    CommanderTrait,
    ContractStatus,
    FeudParty,
    FeudStatus,
    Formation,
    MoraleState,
    PeaceTermKind,
    ShieldType,
    SpyCover,
    SpyOwnerKind,
    Stance,
    Tactic,
    TargetClass,
    UnitFamily,
    UnitKind,
    WarAimKind,
)
from aerona.domain.enums.society import SocialClass


class ArmyUnitRow(Base):
    __tablename__ = "army_units"
    __table_args__ = (
        at_least("count", 0),
        at_least("wounded", 0),
        between("quality", PERCENT_MIN, PERCENT_MAX),
        between("experience", PERCENT_MIN, PERCENT_MAX),
        between("morale", PERCENT_MIN, PERCENT_MAX),
        between("fatigue", PERCENT_MIN, PERCENT_MAX),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        between("organisation", PERCENT_MIN, PERCENT_MAX),
        between("discipline", PERCENT_MIN, PERCENT_MAX),
        at_least("ammunition", 0),
        at_least("missing", 0),
        Index("ix_army_units_army", "army_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[UnitKind] = mapped_column(enum_type(UnitKind, "kind"))
    count: Mapped[int] = mapped_column(default=0)
    quality: Mapped[int] = mapped_column(default=50)
    armour: Mapped[ArmourType] = mapped_column(enum_type(ArmourType, "armour"), default=ArmourType.NONE)
    shield: Mapped[ShieldType] = mapped_column(enum_type(ShieldType, "shield"), default=ShieldType.NONE)
    helmet: Mapped[bool] = mapped_column(default=False)
    weapons: Mapped[list[str]] = mapped_column(JSON, default=list)
    material: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    experience: Mapped[int] = mapped_column(default=10)
    morale: Mapped[int] = mapped_column(default=60)
    fatigue: Mapped[int] = mapped_column(default=0)
    wounded: Mapped[int] = mapped_column(default=0)
    condition: Mapped[int] = mapped_column(default=100)
    social_class: Mapped[SocialClass | None] = mapped_column(enum_type(SocialClass, "social_class"))
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    design_id: Mapped[int | None] = mapped_column(ForeignKey("unit_designs.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    organisation: Mapped[int] = mapped_column(default=100)
    discipline: Mapped[int] = mapped_column(default=30)
    ammunition: Mapped[int] = mapped_column(default=0)
    morale_state: Mapped[MoraleState] = mapped_column(enum_type(MoraleState, "morale_state"), default=MoraleState.STEADY)
    formation: Mapped[Formation] = mapped_column(enum_type(Formation, "formation"), default=Formation.LINE)
    echelon_id: Mapped[int | None] = mapped_column(ForeignKey("echelons.id", ondelete="SET NULL"), index=True)
    missing: Mapped[int] = mapped_column(default=0)


class UnitDesignRow(Base):
    __tablename__ = "unit_designs"
    __table_args__ = (
        between("melee", PERCENT_MIN, PERCENT_MAX),
        between("missile", PERCENT_MIN, PERCENT_MAX),
        between("defence", PERCENT_MIN, PERCENT_MAX),
        at_least("speed", 0),
        at_least("mass", 0),
        at_least("cost", 0),
        at_least("upkeep", 0),
        between("terror", PERCENT_MIN, PERCENT_MAX),
        between("discipline", PERCENT_MIN, PERCENT_MAX),
        at_least("training_epochs", 0),
        at_least("crew_per_vehicle", 0),
        Index("ix_unit_designs_world", "world_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    base_kind: Mapped[UnitKind] = mapped_column(enum_type(UnitKind, "base_kind"), default=UnitKind.LEVY)
    family: Mapped[UnitFamily] = mapped_column(enum_type(UnitFamily, "family"), default=UnitFamily.INFANTRY)
    melee: Mapped[int] = mapped_column(default=40)
    missile: Mapped[int] = mapped_column(default=0)
    defence: Mapped[int] = mapped_column(default=40)
    speed: Mapped[int] = mapped_column(default=40)
    mass: Mapped[int] = mapped_column(default=25)
    cost: Mapped[int] = mapped_column(default=2)
    upkeep: Mapped[int] = mapped_column(default=1)
    armour: Mapped[ArmourType] = mapped_column(enum_type(ArmourType, "armour"), default=ArmourType.NONE)
    shield: Mapped[ShieldType] = mapped_column(enum_type(ShieldType, "shield"), default=ShieldType.NONE)
    terror: Mapped[int] = mapped_column(default=0)
    counters_charge: Mapped[bool] = mapped_column(default=False)
    flying: Mapped[bool] = mapped_column(default=False)
    social_class: Mapped[SocialClass | None] = mapped_column(enum_type(SocialClass, "social_class"))
    owner_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    created_epoch: Mapped[int] = mapped_column(default=0)
    retired: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    reach: Mapped[int] = mapped_column(default=0)
    volleys: Mapped[int] = mapped_column(default=0)
    accuracy: Mapped[int] = mapped_column(default=40)
    piercing: Mapped[int] = mapped_column(default=20)
    description: Mapped[str | None] = mapped_column(Text)
    world_id: Mapped[int | None] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    origin_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    doctrine: Mapped[MartialStyle | None] = mapped_column(enum_type(MartialStyle, "doctrine"))
    formation: Mapped[Formation | None] = mapped_column(enum_type(Formation, "formation"))
    discipline: Mapped[int] = mapped_column(default=40, server_default="40")
    training_epochs: Mapped[int] = mapped_column(default=1, server_default="1")
    mount_species_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    vehicle_design_id: Mapped[int | None] = mapped_column(ForeignKey("designs.id", ondelete="SET NULL"))
    crew_per_vehicle: Mapped[int] = mapped_column(default=0, server_default="0")
    parent_design_id: Mapped[int | None] = mapped_column(ForeignKey("unit_designs.id", ondelete="SET NULL"))


class ArmyProfileRow(Base):
    __tablename__ = "army_profiles"
    __table_args__ = (
        between("cohesion", PERCENT_MIN, PERCENT_MAX),
        between("disease", PERCENT_MIN, PERCENT_MAX),
        between("entrenchment", PERCENT_MIN, PERCENT_MAX),
        at_least("supply_days", 0),
        at_least("war_chest", 0),
        at_least("loot", 0),
    )

    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stance: Mapped[Stance] = mapped_column(enum_type(Stance, "stance"), default=Stance.MARCH)
    doctrine: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH), default="shieldwall")
    supply_days: Mapped[int] = mapped_column(default=90)
    supply_line: Mapped[list[int]] = mapped_column(JSON, default=list)
    cohesion: Mapped[int] = mapped_column(default=70)
    war_chest: Mapped[int] = mapped_column(default=0)
    disease: Mapped[int] = mapped_column(default=0)
    loot: Mapped[int] = mapped_column(default=0)
    entrenchment: Mapped[int] = mapped_column(default=0)
    forced_march: Mapped[bool] = mapped_column(default=False)
    baggage: Mapped[int] = mapped_column(default=0)
    blockade_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
    tactic: Mapped[Tactic | None] = mapped_column(enum_type(Tactic, "tactic"))
    drill: Mapped[int] = mapped_column(default=0)
    fodder_days: Mapped[int] = mapped_column(default=90)
    mutiny: Mapped[int] = mapped_column(default=0)
    battle_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    contact_seasons: Mapped[int] = mapped_column(default=0)


class ArmyOfficerRow(Base):
    __tablename__ = "army_officers"
    __table_args__ = (Index("ix_army_officers_army", "army_entity_id"), Index("ix_army_officers_mortal", "mortal_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    role: Mapped[ArmyRole] = mapped_column(enum_type(ArmyRole, "role"))
    office_id: Mapped[int | None] = mapped_column(ForeignKey("offices.id", ondelete="SET NULL"))
    since_epoch: Mapped[int] = mapped_column(default=0)
    until_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class MercenaryContractRow(Base):
    __tablename__ = "mercenary_contracts"
    __table_args__ = (
        at_least("soldiers", 0),
        at_least("pay_per_season", 0),
        at_least("seasons_left", 0),
        at_least("unpaid_seasons", 0),
        between("loyalty", PERCENT_MIN, PERCENT_MAX),
        Index("ix_mercenary_contracts_employer", "employer_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    employer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    company_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    army_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    soldiers: Mapped[int] = mapped_column(default=0)
    pay_per_season: Mapped[int] = mapped_column(default=0)
    seasons_left: Mapped[int] = mapped_column(default=4)
    loyalty: Mapped[int] = mapped_column(default=60)
    unpaid_seasons: Mapped[int] = mapped_column(default=0)
    status: Mapped[ContractStatus] = mapped_column(enum_type(ContractStatus, "status"), default=ContractStatus.ACTIVE)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class LearnedTacticRow(Base):
    __tablename__ = "learned_tactics"

    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    tactic: Mapped[Tactic] = mapped_column(enum_type(Tactic, "tactic"), primary_key=True)
    wins: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)


class BattleStackRow(Base):
    __tablename__ = "battle_stacks"
    __table_args__ = (Index("ix_battle_stacks_battle", "battle_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id", ondelete="CASCADE"))
    side_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    army_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    kind: Mapped[UnitKind] = mapped_column(enum_type(UnitKind, "kind"))
    label: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    start: Mapped[int] = mapped_column(default=0)
    lost: Mapped[int] = mapped_column(default=0)
    wounded: Mapped[int] = mapped_column(default=0)
    routed: Mapped[bool] = mapped_column(default=False)
    killed: Mapped[int] = mapped_column(default=0)
    walking: Mapped[int] = mapped_column(default=0)
    stretcher: Mapped[int] = mapped_column(default=0)
    captured: Mapped[int] = mapped_column(default=0)
    missing: Mapped[int] = mapped_column(default=0)
    deserted: Mapped[int] = mapped_column(default=0)
    reserve: Mapped[bool] = mapped_column(default=False)
    organisation: Mapped[int] = mapped_column(default=0)
    ammunition_spent: Mapped[int] = mapped_column(default=0)
    formation: Mapped[Formation | None] = mapped_column(enum_type(Formation, "formation"))
    morale_state: Mapped[MoraleState | None] = mapped_column(enum_type(MoraleState, "morale_state"))
    target_class: Mapped[TargetClass | None] = mapped_column(enum_type(TargetClass, "target_class"))


class BattleCasualtyRow(Base):
    __tablename__ = "battle_casualties"
    __table_args__ = (Index("ix_battle_casualties_battle", "battle_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id", ondelete="CASCADE"))
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    side_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    fate: Mapped[CasualtyFate] = mapped_column(enum_type(CasualtyFate, "fate"))
    harm: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(Text)


class PeaceTermRow(Base):
    __tablename__ = "peace_terms"
    __table_args__ = (Index("ix_peace_terms_war", "war_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    kind: Mapped[PeaceTermKind] = mapped_column(enum_type(PeaceTermKind, "kind"))
    beneficiary_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    obligor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    treaty_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    params: Mapped[dict[str, int | str | bool]] = mapped_column(JSON, default=dict)
    epoch: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(Text)


class SpyAgentRow(Base):
    __tablename__ = "spy_agents"
    __table_args__ = (between("skill", PERCENT_MIN, PERCENT_MAX), between("exposure", PERCENT_MIN, PERCENT_MAX), Index("ix_spy_agents_network", "network_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    network_id: Mapped[int] = mapped_column(ForeignKey("spy_networks.id", ondelete="CASCADE"))
    mortal_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    cover: Mapped[SpyCover] = mapped_column(enum_type(SpyCover, "cover"), default=SpyCover.MERCHANT)
    skill: Mapped[int] = mapped_column(default=30)
    exposure: Mapped[int] = mapped_column(default=0)
    motive: Mapped[RecruitMotive] = mapped_column(enum_type(RecruitMotive, "motive"), default=RecruitMotive.MONEY, server_default="money")
    loyalty: Mapped[int] = mapped_column(default=50, server_default="50")
    cell_id: Mapped[int | None] = mapped_column(ForeignKey("spy_cells.id", ondelete="SET NULL"))
    status: Mapped[AgentStatus] = mapped_column(enum_type(AgentStatus, "status"), default=AgentStatus.ACTIVE)
    since_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class FeudRow(Base):
    __tablename__ = "feuds"
    __table_args__ = (
        between("intensity", PERCENT_MIN, PERCENT_MAX),
        between("grievance", PERCENT_MIN, PERCENT_MAX),
        at_least("generations", 0),
        Index("ix_feuds_first", "first_entity_id"),
        Index("ix_feuds_second", "second_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    first_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    party: Mapped[FeudParty] = mapped_column(enum_type(FeudParty, "party"), default=FeudParty.COMMUNITY)
    intensity: Mapped[int] = mapped_column(default=40)
    grievance: Mapped[int] = mapped_column(default=40)
    generations: Mapped[int] = mapped_column(default=0)
    status: Mapped[FeudStatus] = mapped_column(enum_type(FeudStatus, "status"), default=FeudStatus.ACTIVE)
    cause: Mapped[str | None] = mapped_column(Text)
    since_epoch: Mapped[int] = mapped_column(default=0)
    last_epoch: Mapped[int | None]
    last_action: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    ended_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArmyMovementRow(Base):
    __tablename__ = "army_movements"
    __table_args__ = (Index("ix_army_movements_army", "army_entity_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    season: Mapped[int]
    from_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    to_region_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    stance: Mapped[Stance] = mapped_column(enum_type(Stance, "stance"))
    supply_days: Mapped[int]
    attrition: Mapped[int] = mapped_column(default=0)
    note: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))


class BattlePhaseRow(Base):
    __tablename__ = "battle_phases"
    __table_args__ = (Index("ix_battle_phases_battle", "battle_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    battle_id: Mapped[int] = mapped_column(ForeignKey("battles.id", ondelete="CASCADE"))
    position: Mapped[int]
    phase: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    attacker_losses: Mapped[int] = mapped_column(default=0)
    defender_losses: Mapped[int] = mapped_column(default=0)
    summary: Mapped[str | None] = mapped_column(Text)
    details: Mapped[dict[str, int | str]] = mapped_column(JSON, default=dict)


class CommanderTraitRow(Base):
    __tablename__ = "commander_traits"

    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    trait: Mapped[CommanderTrait] = mapped_column(enum_type(CommanderTrait, "trait"), primary_key=True)
    since_epoch: Mapped[int] = mapped_column(default=0)


class CampaignFrontRow(Base):
    __tablename__ = "campaign_fronts"
    __table_args__ = (Index("ix_campaign_fronts_war", "war_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    first_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    second_region_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    since_epoch: Mapped[int]
    last_epoch: Mapped[int]


class WarAimRow(Base):
    __tablename__ = "war_aims"
    __table_args__ = (between("achieved", PERCENT_MIN, PERCENT_MAX), Index("ix_war_aims_war", "war_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    side_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[WarAimKind] = mapped_column(enum_type(WarAimKind, "kind"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    params: Mapped[dict[str, int | str | bool]] = mapped_column(JSON, default=dict)
    achieved: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class OccupationRow(Base):
    __tablename__ = "occupations"
    __table_args__ = (between("control", PERCENT_MIN, PERCENT_MAX), between("resistance", PERCENT_MIN, PERCENT_MAX))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    occupier_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    since_epoch: Mapped[int]
    control: Mapped[int] = mapped_column(default=20)
    resistance: Mapped[int] = mapped_column(default=30)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CaptiveCohortRow(Base):
    __tablename__ = "captive_cohorts"
    __table_args__ = (at_least("count", 0), Index("ix_captive_cohorts_captor", "captor_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    captor_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    language_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    count: Mapped[int] = mapped_column(default=0)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), default=SocialClass.FARMER)
    condition: Mapped[CohortCondition] = mapped_column(enum_type(CohortCondition, "condition"), default=CohortCondition.CAPTIVE)
    fate: Mapped[CaptiveFate] = mapped_column(enum_type(CaptiveFate, "fate"), default=CaptiveFate.HELD)
    since_epoch: Mapped[int]
    settled_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SpyNetworkRow(Base):
    __tablename__ = "spy_networks"
    __table_args__ = (
        between("depth", PERCENT_MIN, PERCENT_MAX),
        between("exposure", PERCENT_MIN, PERCENT_MAX),
        at_least("agents", 0),
        Index("ix_spy_networks_target", "target_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    agents: Mapped[int] = mapped_column(default=1)
    agent_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    depth: Mapped[int] = mapped_column(default=10)
    exposure: Mapped[int] = mapped_column(default=0)
    cover: Mapped[SpyCover] = mapped_column(enum_type(SpyCover, "cover"), default=SpyCover.MERCHANT)
    spymaster_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    bond_id: Mapped[int | None] = mapped_column(ForeignKey("bonds.id", ondelete="SET NULL"))
    since_epoch: Mapped[int]
    last_operation: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    last_epoch: Mapped[int | None]
    intel: Mapped[int] = mapped_column(default=0)
    owner_kind: Mapped[SpyOwnerKind] = mapped_column(enum_type(SpyOwnerKind, "owner_kind"), default=SpyOwnerKind.COMMUNITY)
    side_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    revealed_aims: Mapped[list[int]] = mapped_column(JSON, default=list)
    warned_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


register_profile_table("army_units", "army_entity_id")
register_profile_table("unit_designs", "id")
register_profile_table("army_officers", "army_entity_id")
register_profile_table("mercenary_contracts", "employer_entity_id")
register_profile_table("war_aims", "side_entity_id")
register_profile_table("captive_cohorts", "captor_entity_id")
register_profile_table("spy_networks", "owner_entity_id")
register_profile_table("spy_agents", "id")
register_profile_table("feuds", "first_entity_id")


class ArmyTemplateRow(Base):
    __tablename__ = "army_templates"
    __table_args__ = (at_least("created_epoch", 0), Index("ix_army_templates_polity", "polity_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    doctrine: Mapped[MartialStyle] = mapped_column(enum_type(MartialStyle, "doctrine"), default=MartialStyle.SHIELDWALL)
    composition: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(default=True)
    obsolete: Mapped[bool] = mapped_column(default=False)
    created_epoch: Mapped[int] = mapped_column(default=0)
    upgraded_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
