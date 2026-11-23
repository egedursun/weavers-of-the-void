from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.constants.schema import NAME_MAX_LENGTH
from aerona.db.base import Base, CreatedAtMixin
from aerona.db.columns import at_least, enum_type
from aerona.db.profile_guard import register_profile_table
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.environment import TerrainKind, WeatherKind
from aerona.domain.enums.military import DefenderAction, OutcomeClass, SackChoice, SiegeAction, StarvationStage, Tactic
from aerona.domain.enums.quests import QuestAim, QuestObstacle, QuestReward, QuestScale, QuestTargetKind
from aerona.domain.enums.settlement import BuildMaterial
from aerona.domain.enums.war import (
    BattleOutcome,
    CaptiveStatus,
    CasusBelliKind,
    HeroQuestStatus,
    SiegeStatus,
    TributeStatus,
    WarCause,
    WarEnding,
    WarSide,
    WarStatus,
)


class WarRow(CreatedAtMixin, Base):
    __tablename__ = "wars"
    __table_args__ = (
        CheckConstraint("status <> 'ended' OR (ended_epoch IS NOT NULL AND ending IS NOT NULL)", name="ended_has_outcome"),
        CheckConstraint("ended_epoch IS NULL OR ended_epoch >= started_epoch", name="ends_after_start"),
        CheckConstraint("victor_entity_id IS NULL OR loser_entity_id IS NULL OR victor_entity_id <> loser_entity_id", name="distinct_victor_loser"),
        at_least("battles", 0),
        Index("ix_wars_status", "status"),
        Index("ix_wars_world_status", "world_id", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    event_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), unique=True)
    world_id: Mapped[int] = mapped_column(ForeignKey("worlds.id", ondelete="CASCADE"))
    status: Mapped[WarStatus] = mapped_column(enum_type(WarStatus, "status"), default=WarStatus.ONGOING)
    cause: Mapped[WarCause] = mapped_column(enum_type(WarCause, "cause"))
    cause_text: Mapped[str | None] = mapped_column(Text)
    started_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    last_clash_epoch: Mapped[int | None]
    battles: Mapped[int] = mapped_column(default=0)
    score: Mapped[int] = mapped_column(default=0)
    violence: Mapped[int | None]
    ending: Mapped[WarEnding | None] = mapped_column(enum_type(WarEnding, "ending"))
    victor_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    loser_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    incited_by_son_id: Mapped[int | None] = mapped_column(ForeignKey("sons.id", ondelete="SET NULL"))
    casus_belli_id: Mapped[int | None] = mapped_column(ForeignKey("casus_belli.id", ondelete="SET NULL", use_alter=True))
    justified: Mapped[bool] = mapped_column(default=True)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class CasusBelliRow(Base):
    __tablename__ = "casus_belli"
    __table_args__ = (
        CheckConstraint("justification >= 0 AND justification <= 100", name="justification_range"),
        Index("ix_casus_belli_holder", "holder_entity_id", "target_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    holder_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    target_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    kind: Mapped[CasusBelliKind] = mapped_column(enum_type(CasusBelliKind, "kind"))
    source_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    justification: Mapped[int] = mapped_column(default=0)
    since_epoch: Mapped[int] = mapped_column(default=0)
    expires_epoch: Mapped[int | None]
    used_war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WarProductionRow(Base):
    __tablename__ = "war_production"
    __table_args__ = (CheckConstraint("efficiency >= 0", name="efficiency_min"),)

    community_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    commodity: Mapped[CommodityKind] = mapped_column(enum_type(CommodityKind, "commodity"))
    efficiency: Mapped[int] = mapped_column(default=0)
    converted: Mapped[bool] = mapped_column(default=True)
    since_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class WarSideRow(Base):
    __tablename__ = "war_sides"
    __table_args__ = (UniqueConstraint("war_id", "side", "entity_id", name="uq_war_sides_side_entity"),)

    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"), primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True, index=True)
    side: Mapped[WarSide] = mapped_column(enum_type(WarSide, "side"))
    joined_epoch: Mapped[int]
    left_epoch: Mapped[int | None]
    weariness: Mapped[int] = mapped_column(default=0)
    support: Mapped[int] = mapped_column(default=60)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArmyRow(Base):
    __tablename__ = "armies"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"), index=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    commander_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    raised_epoch: Mapped[int]
    disbanded_epoch: Mapped[int | None]


class SiegeRow(Base):
    __tablename__ = "sieges"
    __table_args__ = (at_least("rounds", 0), Index("ix_sieges_war_status", "war_id", "status"))

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    besieged_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    besieger_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    status: Mapped[SiegeStatus] = mapped_column(enum_type(SiegeStatus, "status"), default=SiegeStatus.ONGOING)
    started_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]
    rounds: Mapped[int] = mapped_column(default=0)
    walls_level: Mapped[int] = mapped_column(default=0)
    breaches: Mapped[int] = mapped_column(default=0)
    supplies: Mapped[int] = mapped_column(default=180)
    water: Mapped[int] = mapped_column(default=120)
    disease_inside: Mapped[int] = mapped_column(default=0)
    disease_outside: Mapped[int] = mapped_column(default=0)
    works: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    sallies: Mapped[int] = mapped_column(default=0)
    starvation: Mapped[StarvationStage] = mapped_column(enum_type(StarvationStage, "starvation"), default=StarvationStage.NONE)
    last_action: Mapped[SiegeAction | None] = mapped_column(enum_type(SiegeAction, "last_action"))
    last_defence: Mapped[DefenderAction | None] = mapped_column(enum_type(DefenderAction, "last_defence"))
    wall_material: Mapped[BuildMaterial | None] = mapped_column(enum_type(BuildMaterial, "wall_material"))
    relief_army_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    choice: Mapped[SackChoice | None] = mapped_column(enum_type(SackChoice, "choice"))
    ordered_epoch: Mapped[int | None]
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class BattleRow(Base):
    __tablename__ = "battles"
    __table_args__ = (Index("ix_battles_war_epoch", "war_id", "epoch"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    epoch: Mapped[int]
    sequence: Mapped[int]
    record_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    place_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    winner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    loser_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    outcome: Mapped[BattleOutcome] = mapped_column(enum_type(BattleOutcome, "outcome"))
    gap: Mapped[float]
    siege_id: Mapped[int | None] = mapped_column(ForeignKey("sieges.id", ondelete="SET NULL"))
    weather: Mapped[WeatherKind | None] = mapped_column(enum_type(WeatherKind, "weather"))
    season_name: Mapped[str | None] = mapped_column(String(NAME_MAX_LENGTH))
    terrain: Mapped[TerrainKind | None] = mapped_column(enum_type(TerrainKind, "terrain"))
    year: Mapped[int | None]
    night: Mapped[bool] = mapped_column(default=False)
    tactics_attacker: Mapped[Tactic | None] = mapped_column(enum_type(Tactic, "tactics_attacker"))
    tactics_defender: Mapped[Tactic | None] = mapped_column(enum_type(Tactic, "tactics_defender"))
    outcome_class: Mapped[OutcomeClass | None] = mapped_column(enum_type(OutcomeClass, "outcome_class"))
    casualties_by_kind: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    winner_losses: Mapped[int] = mapped_column(default=0)
    loser_losses: Mapped[int] = mapped_column(default=0)
    tactic_factors: Mapped[dict[str, float]] = mapped_column(JSON, default=dict)
    morale: Mapped[dict[str, dict[str, int]]] = mapped_column(JSON, default=dict)
    magic: Mapped[dict[str, int]] = mapped_column(JSON, default=dict)
    width: Mapped[int] = mapped_column(default=0)
    reserves_committed: Mapped[int] = mapped_column(default=0)
    command_collapsed_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    planned_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    trap_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    feint: Mapped[bool] = mapped_column(default=False)
    salvaged: Mapped[int] = mapped_column(default=0)
    standard_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))


class CaptiveRow(Base):
    __tablename__ = "captives"
    __table_args__ = (
        CheckConstraint("captive_entity_id <> captor_entity_id", name="distinct_parties"),
        Index("ix_captives_status", "status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    captive_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    captor_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    home_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    bond_id: Mapped[int | None] = mapped_column(ForeignKey("bonds.id", ondelete="SET NULL"))
    status: Mapped[CaptiveStatus] = mapped_column(enum_type(CaptiveStatus, "status"), default=CaptiveStatus.HELD)
    taken_epoch: Mapped[int]
    released_epoch: Mapped[int | None]
    ransom_paid: Mapped[int | None]
    loyalty: Mapped[int] = mapped_column(default=0)
    married_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    oath_id: Mapped[int | None] = mapped_column(ForeignKey("oaths.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TributeRow(Base):
    __tablename__ = "tributes"
    __table_args__ = (
        CheckConstraint("payer_entity_id <> receiver_entity_id", name="distinct_parties"),
        Index("ix_tributes_status", "status"),
        Index("ix_tributes_pair", "payer_entity_id", "receiver_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    payer_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    receiver_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    war_id: Mapped[int | None] = mapped_column(ForeignKey("wars.id", ondelete="SET NULL"))
    bond_id: Mapped[int | None] = mapped_column(ForeignKey("bonds.id", ondelete="SET NULL"))
    status: Mapped[TributeStatus] = mapped_column(enum_type(TributeStatus, "status"), default=TributeStatus.ACTIVE)
    since_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]


class HeroQuestRow(Base):
    __tablename__ = "hero_quests"
    __table_args__ = (Index("ix_hero_quests_hero_status", "hero_entity_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    hero_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    aim: Mapped[QuestAim] = mapped_column("kind", enum_type(QuestAim, "kind"))
    target_kind: Mapped[QuestTargetKind] = mapped_column(enum_type(QuestTargetKind, "target_kind"), default=QuestTargetKind.PERSON, server_default="person")
    obstacle: Mapped[QuestObstacle] = mapped_column(enum_type(QuestObstacle, "obstacle"), default=QuestObstacle.DISTANCE, server_default="distance")
    reward: Mapped[QuestReward] = mapped_column(enum_type(QuestReward, "reward"), default=QuestReward.RENOWN, server_default="renown")
    scale: Mapped[QuestScale] = mapped_column(enum_type(QuestScale, "scale"), default=QuestScale.PERSONAL, server_default="personal")
    locked: Mapped[list[str]] = mapped_column(JSON, default=list, server_default="[]")
    target_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    thread_id: Mapped[int | None] = mapped_column(ForeignKey("threads.id", ondelete="SET NULL"))
    bond_id: Mapped[int | None] = mapped_column(ForeignKey("bonds.id", ondelete="SET NULL"))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[HeroQuestStatus] = mapped_column(enum_type(HeroQuestStatus, "status"), default=HeroQuestStatus.ACTIVE)
    started_epoch: Mapped[int]
    ended_epoch: Mapped[int | None]


register_profile_table("sieges", "besieged_entity_id")
register_profile_table("captives", "captive_entity_id")
