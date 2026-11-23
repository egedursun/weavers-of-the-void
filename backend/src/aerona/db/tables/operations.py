from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aerona.db.base import Base
from aerona.db.columns import at_least, between, enum_type
from aerona.domain.enums.limits import PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.operations import (
    CarrierKind,
    CrewStation,
    EchelonLevel,
    EchelonOrder,
    ExpeditionEvent,
    ExpeditionGround,
    ExpeditionRole,
    ExpeditionStatus,
    PointOfSail,
    QuirkKind,
    ResolveKind,
    ShotKind,
)

NAME = 200
OCTANTS = 7
STRESS_MAX = 200
ECHELON_FIELDS = (
    "name",
    "level",
    "parent_id",
    "commander_entity_id",
    "hq_region_entity_id",
    "staff",
    "command_range",
    "command_points",
    "points_spent",
    "order",
    "in_range",
)
DEPOT_FIELDS = ("region_entity_id", "structure_entity_id", "supplies", "capacity", "field", "cut")
TRANSPORT_FIELDS = ("depot_id", "kind", "count", "capacity", "condition")
FLOW_FIELDS = ("produced", "shipped", "lost", "delivered", "need", "throughput")
OPERATION_FIELDS = ("offensive_seasons", "need", "delivered", "organisation", "culminated", "pause_seasons", "foresight", "standing")
THEATRE_FIELDS = ("front_region_entity_id", "marshal_entity_id", "priority", "believed_threat", "true_threat", "reserves", "levies", "transport", "misjudged")
SHIP_FIELDS = (
    "heading",
    "wind_from",
    "point_of_sail",
    "tacks",
    "shot",
    "leak",
    "fire",
    "magazine",
    "rate_of_fire",
    "rower_fatigue",
    "raked",
    "struck",
    "prize_of_entity_id",
    "prize_crew",
    "prize_money",
)
CREW_FIELDS = ("count", "skill")
ADMIRALTY_FIELDS = ("admiral_entity_id", "budget_share", "requested", "influence", "tonnage", "limit_tonnage", "concealed", "commissioned")
EXPEDITION_FIELDS = (
    "name",
    "leader_entity_id",
    "sponsor_node_id",
    "target_entity_id",
    "ground",
    "status",
    "legs_done",
    "legs_total",
    "provisions",
    "light",
    "air",
    "tools",
    "medicine",
    "darkness",
    "danger",
    "found",
)
MEMBER_FIELDS = ("role", "stress", "resolve", "cold", "wet", "hunger", "fatigue", "fallen", "departed")
LOG_FIELDS = ("event", "leg", "member_entity_id", "provisions_used", "light_used", "stress", "resolve", "quirk")
QUIRK_FIELDS = ("kind", "source_entity_id", "strength")


class EchelonRow(Base):
    __tablename__ = "echelons"
    __table_args__ = (
        between("staff", PERCENT_MIN, PERCENT_MAX),
        at_least("command_range", 0),
        at_least("command_points", 0),
        at_least("points_spent", 0),
        at_least("formed_epoch", 0),
        Index("ix_echelons_owner", "owner_entity_id"),
        Index("ix_echelons_army", "army_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    army_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("echelons.id", ondelete="SET NULL"), index=True)
    level: Mapped[EchelonLevel] = mapped_column(enum_type(EchelonLevel, "level"))
    name: Mapped[str] = mapped_column(String(NAME))
    commander_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    hq_region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    staff: Mapped[int] = mapped_column(default=30)
    command_range: Mapped[int] = mapped_column(default=2)
    command_points: Mapped[int] = mapped_column(default=3)
    points_spent: Mapped[int] = mapped_column(default=0)
    order: Mapped[EchelonOrder] = mapped_column(enum_type(EchelonOrder, "order"), default=EchelonOrder.STANDING)
    in_range: Mapped[bool] = mapped_column(default=True)
    formed_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class DepotRow(Base):
    __tablename__ = "depots"
    __table_args__ = (at_least("supplies", 0), at_least("capacity", 0), at_least("founded_epoch", 0), Index("ix_depots_owner", "owner_entity_id"))

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"), index=True)
    structure_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    supplies: Mapped[int] = mapped_column(default=0)
    capacity: Mapped[int] = mapped_column(default=600)
    field: Mapped[bool] = mapped_column(default=False)
    cut: Mapped[bool] = mapped_column(default=False)
    founded_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TransportAssetRow(Base):
    __tablename__ = "transport_assets"
    __table_args__ = (
        at_least("count", 0),
        at_least("capacity", 0),
        between("condition", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("owner_entity_id", "kind", name="uq_transport_assets_owner_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    depot_id: Mapped[int | None] = mapped_column(ForeignKey("depots.id", ondelete="SET NULL"))
    kind: Mapped[CarrierKind] = mapped_column(enum_type(CarrierKind, "kind"))
    count: Mapped[int] = mapped_column(default=0)
    capacity: Mapped[int] = mapped_column(default=10)
    condition: Mapped[int] = mapped_column(default=100)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class SupplyFlowRow(Base):
    __tablename__ = "supply_flows"
    __table_args__ = (
        at_least("produced", 0),
        at_least("shipped", 0),
        at_least("lost", 0),
        at_least("delivered", 0),
        at_least("need", 0),
        at_least("throughput", 0),
        Index("ix_supply_flows_army", "army_entity_id"),
        Index("ix_supply_flows_owner_epoch", "owner_entity_id", "epoch"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    epoch: Mapped[int] = mapped_column(default=0)
    season: Mapped[int] = mapped_column(default=0)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    depot_id: Mapped[int | None] = mapped_column(ForeignKey("depots.id", ondelete="SET NULL"))
    produced: Mapped[int] = mapped_column(default=0)
    shipped: Mapped[int] = mapped_column(default=0)
    lost: Mapped[int] = mapped_column(default=0)
    delivered: Mapped[int] = mapped_column(default=0)
    need: Mapped[int] = mapped_column(default=0)
    throughput: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ArmyOperationRow(Base):
    __tablename__ = "army_operations"
    __table_args__ = (
        at_least("offensive_seasons", 0),
        at_least("need", 0),
        at_least("delivered", 0),
        between("organisation", PERCENT_MIN, PERCENT_MAX),
        at_least("pause_seasons", 0),
        at_least("foresight", 0),
        at_least("updated_epoch", 0),
    )

    army_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    offensive_seasons: Mapped[int] = mapped_column(default=0)
    need: Mapped[int] = mapped_column(default=0)
    delivered: Mapped[int] = mapped_column(default=0)
    organisation: Mapped[int] = mapped_column(default=100)
    culminated: Mapped[bool] = mapped_column(default=False)
    culminated_epoch: Mapped[int | None]
    pause_seasons: Mapped[int] = mapped_column(default=0)
    foresight: Mapped[int] = mapped_column(default=0)
    standing: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class TheatreRow(Base):
    __tablename__ = "theatres"
    __table_args__ = (
        between("priority", PERCENT_MIN, PERCENT_MAX),
        between("believed_threat", PERCENT_MIN, PERCENT_MAX),
        between("true_threat", PERCENT_MIN, PERCENT_MAX),
        at_least("reserves", 0),
        at_least("levies", 0),
        at_least("transport", 0),
        at_least("updated_epoch", 0),
        UniqueConstraint("owner_entity_id", "war_id", name="uq_theatres_owner_war"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    war_id: Mapped[int] = mapped_column(ForeignKey("wars.id", ondelete="CASCADE"))
    front_region_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    marshal_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    priority: Mapped[int] = mapped_column(default=50)
    believed_threat: Mapped[int] = mapped_column(default=50)
    true_threat: Mapped[int] = mapped_column(default=50)
    reserves: Mapped[int] = mapped_column(default=0)
    levies: Mapped[int] = mapped_column(default=0)
    transport: Mapped[int] = mapped_column(default=0)
    misjudged: Mapped[bool] = mapped_column(default=False)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ShipStateRow(Base):
    __tablename__ = "ship_states"
    __table_args__ = (
        between("heading", 0, OCTANTS),
        between("wind_from", 0, OCTANTS),
        at_least("tacks", 0),
        between("leak", PERCENT_MIN, PERCENT_MAX),
        between("fire", PERCENT_MIN, PERCENT_MAX),
        between("rate_of_fire", PERCENT_MIN, PERCENT_MAX),
        between("rower_fatigue", PERCENT_MIN, PERCENT_MAX),
        at_least("raked", 0),
        at_least("prize_crew", 0),
        at_least("prize_money", 0),
        at_least("updated_epoch", 0),
    )

    vessel_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    heading: Mapped[int] = mapped_column(default=0)
    wind_from: Mapped[int] = mapped_column(default=0)
    point_of_sail: Mapped[PointOfSail] = mapped_column(enum_type(PointOfSail, "point_of_sail"), default=PointOfSail.REACHING)
    tacks: Mapped[int] = mapped_column(default=0)
    shot: Mapped[ShotKind] = mapped_column(enum_type(ShotKind, "shot"), default=ShotKind.ROUND)
    leak: Mapped[int] = mapped_column(default=0)
    fire: Mapped[int] = mapped_column(default=0)
    magazine: Mapped[bool] = mapped_column(default=True)
    rate_of_fire: Mapped[int] = mapped_column(default=50)
    rower_fatigue: Mapped[int] = mapped_column(default=0)
    raked: Mapped[int] = mapped_column(default=0)
    struck: Mapped[bool] = mapped_column(default=False)
    prize_of_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    prize_crew: Mapped[int] = mapped_column(default=0)
    prize_money: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ShipCrewRow(Base):
    __tablename__ = "ship_crews"
    __table_args__ = (at_least("count", 0), between("skill", PERCENT_MIN, PERCENT_MAX))

    vessel_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    station: Mapped[CrewStation] = mapped_column(enum_type(CrewStation, "station"), primary_key=True)
    count: Mapped[int] = mapped_column(default=0)
    skill: Mapped[int] = mapped_column(default=40)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class AdmiraltyRow(Base):
    __tablename__ = "admiralties"
    __table_args__ = (
        between("budget_share", PERCENT_MIN, PERCENT_MAX),
        between("requested", PERCENT_MIN, PERCENT_MAX),
        between("influence", PERCENT_MIN, PERCENT_MAX),
        at_least("tonnage", 0),
        at_least("concealed", 0),
        at_least("commissioned", 0),
        at_least("updated_epoch", 0),
    )

    polity_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"), primary_key=True)
    admiral_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    budget_share: Mapped[int] = mapped_column(default=25)
    requested: Mapped[int] = mapped_column(default=25)
    influence: Mapped[int] = mapped_column(default=40)
    tonnage: Mapped[int] = mapped_column(default=0)
    limit_tonnage: Mapped[int | None]
    concealed: Mapped[int] = mapped_column(default=0)
    commissioned: Mapped[int] = mapped_column(default=0)
    updated_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExpeditionRow(Base):
    __tablename__ = "expeditions"
    __table_args__ = (
        at_least("legs_done", 0),
        at_least("legs_total", 1),
        at_least("provisions", 0),
        at_least("light", 0),
        at_least("air", 0),
        at_least("tools", 0),
        at_least("medicine", 0),
        between("darkness", PERCENT_MIN, PERCENT_MAX),
        between("danger", PERCENT_MIN, PERCENT_MAX),
        at_least("found", 0),
        at_least("started_epoch", 0),
        Index("ix_expeditions_leader", "leader_entity_id"),
        Index("ix_expeditions_target", "target_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(NAME))
    leader_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    sponsor_node_id: Mapped[int | None] = mapped_column(ForeignKey("nodes.id", ondelete="SET NULL"))
    target_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    ground: Mapped[ExpeditionGround] = mapped_column(enum_type(ExpeditionGround, "ground"), default=ExpeditionGround.WILDS)
    status: Mapped[ExpeditionStatus] = mapped_column(enum_type(ExpeditionStatus, "status"), default=ExpeditionStatus.UNDERWAY)
    legs_done: Mapped[int] = mapped_column(default=0)
    legs_total: Mapped[int] = mapped_column(default=4)
    provisions: Mapped[int] = mapped_column(default=12)
    light: Mapped[int] = mapped_column(default=8)
    air: Mapped[int] = mapped_column(default=0)
    tools: Mapped[int] = mapped_column(default=2)
    medicine: Mapped[int] = mapped_column(default=2)
    darkness: Mapped[int] = mapped_column(default=0)
    danger: Mapped[int] = mapped_column(default=20)
    found: Mapped[int] = mapped_column(default=0)
    started_epoch: Mapped[int] = mapped_column(default=0)
    ended_epoch: Mapped[int | None]
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExpeditionMemberRow(Base):
    __tablename__ = "expedition_members"
    __table_args__ = (
        between("stress", 0, STRESS_MAX),
        between("cold", PERCENT_MIN, PERCENT_MAX),
        between("wet", PERCENT_MIN, PERCENT_MAX),
        between("hunger", PERCENT_MIN, PERCENT_MAX),
        between("fatigue", PERCENT_MIN, PERCENT_MAX),
        UniqueConstraint("expedition_id", "mortal_entity_id", name="uq_expedition_members_mortal"),
        Index("ix_expedition_members_mortal", "mortal_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    role: Mapped[ExpeditionRole] = mapped_column(enum_type(ExpeditionRole, "role"))
    stress: Mapped[int] = mapped_column(default=0)
    resolve: Mapped[ResolveKind] = mapped_column(enum_type(ResolveKind, "resolve"), default=ResolveKind.STEADY)
    cold: Mapped[int] = mapped_column(default=0)
    wet: Mapped[int] = mapped_column(default=0)
    hunger: Mapped[int] = mapped_column(default=0)
    fatigue: Mapped[int] = mapped_column(default=0)
    fallen: Mapped[bool] = mapped_column(default=False)
    departed: Mapped[bool] = mapped_column(default=False)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class ExpeditionLogRow(Base):
    __tablename__ = "expedition_logs"
    __table_args__ = (at_least("leg", 0), at_least("provisions_used", 0), at_least("light_used", 0), at_least("epoch", 0))

    id: Mapped[int] = mapped_column(primary_key=True)
    expedition_id: Mapped[int] = mapped_column(ForeignKey("expeditions.id", ondelete="CASCADE"), index=True)
    member_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    epoch: Mapped[int] = mapped_column(default=0)
    leg: Mapped[int] = mapped_column(default=0)
    event: Mapped[ExpeditionEvent] = mapped_column(enum_type(ExpeditionEvent, "event"))
    provisions_used: Mapped[int] = mapped_column(default=0)
    light_used: Mapped[int] = mapped_column(default=0)
    stress: Mapped[int] = mapped_column(default=0)
    resolve: Mapped[ResolveKind | None] = mapped_column(enum_type(ResolveKind, "resolve"))
    quirk: Mapped[QuirkKind | None] = mapped_column(enum_type(QuirkKind, "quirk"))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id", ondelete="SET NULL"))
    step_id: Mapped[int | None] = mapped_column(ForeignKey("incident_steps.id", ondelete="SET NULL"))
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)


class QuirkRow(Base):
    __tablename__ = "quirks"
    __table_args__ = (
        between("strength", 1, 3),
        at_least("gained_epoch", 0),
        UniqueConstraint("mortal_entity_id", "kind", name="uq_quirks_mortal_kind"),
        Index("ix_quirks_mortal", "mortal_entity_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    mortal_entity_id: Mapped[int] = mapped_column(ForeignKey("entities.id", ondelete="CASCADE"))
    kind: Mapped[QuirkKind] = mapped_column(enum_type(QuirkKind, "kind"))
    source_entity_id: Mapped[int | None] = mapped_column(ForeignKey("entities.id", ondelete="SET NULL"))
    expedition_id: Mapped[int | None] = mapped_column(ForeignKey("expeditions.id", ondelete="SET NULL"))
    strength: Mapped[int] = mapped_column(default=1)
    gained_epoch: Mapped[int] = mapped_column(default=0)
    locked: Mapped[list[str]] = mapped_column(JSON, default=list)
