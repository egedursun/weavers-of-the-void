from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import KEY_MAX_LENGTH
from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.military import ArmourType, CaptiveFate, CommanderTrait, ShieldType, SpyCover, Stance, UnitKind, WarAimKind
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
    summary: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH * 4))
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


class OccupationRow(Base):
    __tablename__ = "occupations"
    __table_args__ = (between("control", PERCENT_MIN, PERCENT_MAX), between("resistance", PERCENT_MIN, PERCENT_MAX))

    region_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    occupier_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    since_epoch: Mapped[int]
    control: Mapped[int] = mapped_column(default=20)
    resistance: Mapped[int] = mapped_column(default=30)


class CaptiveCohortRow(Base):
    __tablename__ = "captive_cohorts"
    __table_args__ = (at_least("count", 0), Index("ix_captive_cohorts_captor", "captor_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    captor_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    origin_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    count: Mapped[int] = mapped_column(default=0)
    social_class: Mapped[SocialClass] = mapped_column(enum_type(SocialClass, "social_class"), default=SocialClass.FARMER)
    condition: Mapped[CohortCondition] = mapped_column(enum_type(CohortCondition, "condition"), default=CohortCondition.CAPTIVE)
    fate: Mapped[CaptiveFate] = mapped_column(enum_type(CaptiveFate, "fate"), default=CaptiveFate.HELD)
    since_epoch: Mapped[int]
    settled_epoch: Mapped[int | None]


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
