from typing import Any

from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.military import DuelContext, HullClass, PeaceTermKind, VesselArmament, WarAimKind
from aerona.domain.enums.war import WarCause
from aerona.engine.military import orders, records
from aerona.engine.military.shipyard import Commission, commission
from aerona.engine.phases.warfare import Theatre, duel, force_battle
from aerona.engine.primitives.queries import living_entity
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

KIND_PATTERN = r"^[a-z][a-z_]*$"
DUEL_CONTEXTS = frozenset({DuelContext.HONOUR, DuelContext.TRIAL, DuelContext.GOD, DuelContext.CHAMPION, DuelContext.WAR})


class RecordCreate(Command):
    kind: str = Field(pattern=KIND_PATTERN)
    values: dict[str, Any] = Field(default_factory=dict)


class RecordEdit(Command):
    kind: str = Field(pattern=KIND_PATTERN)
    record_id: int
    values: dict[str, Any] = Field(default_factory=dict)
    hold: bool = True


class RecordRelease(Command):
    kind: str = Field(pattern=KIND_PATTERN)
    record_id: int
    columns: list[str] = Field(default_factory=list)


class RecordDelete(Command):
    kind: str = Field(pattern=KIND_PATTERN)
    record_id: int


class RaiseArmy(Command):
    community_id: int
    size: int = Field(ge=1, le=10_000_000)
    commander_id: int | None = None
    war_id: int | None = None
    name: str | None = Field(default=None, max_length=120)


class ArmyCommand(Command):
    army_id: int
    commander_id: int | None = None
    owner_id: int | None = None


class BattleAt(Command):
    war_id: int
    region_id: int | None = None


class SiegeStart(Command):
    war_id: int
    army_id: int
    settlement_id: int


class AimOrder(Command):
    kind: WarAimKind
    params: dict[str, int | str | bool] = Field(default_factory=dict)


class DeclareWar(Command):
    attacker_id: int
    defender_id: int
    cause: WarCause
    reason: str = Field(default="", max_length=400)
    aims: list[AimOrder] = Field(default_factory=list)


class TermOrder(Command):
    kind: PeaceTermKind
    params: dict[str, int | str | bool] = Field(default_factory=dict)


class PeaceBuild(Command):
    war_id: int
    victor_id: int | None = None
    terms: list[TermOrder] = Field(default_factory=list)


class VesselOrder(Command):
    owner_id: int
    name: str = Field(min_length=1, max_length=120)
    hull_class: HullClass = HullClass.BOAT
    armament: list[VesselArmament] | None = None
    hull_material: MaterialKind | None = None
    fabric_material: MaterialKind | None = None
    home_port_id: int | None = None
    captain_id: int | None = None
    crew: int | None = Field(default=None, ge=0)


class VesselRefit(Command):
    vessel_id: int
    hull_class: HullClass
    armament: list[VesselArmament] | None = None
    hull_material: MaterialKind | None = None
    fabric_material: MaterialKind | None = None


class VesselTarget(Command):
    vessel_id: int


class CaptiveTake(Command):
    captor_id: int
    mortal_id: int
    war_id: int | None = None


class Ordeal(Command):
    first_id: int
    second_id: int
    context: DuelContext = DuelContext.HONOUR
    war_id: int | None = None


@player_action("military:create", ActionKind.EDIT_RECORD)
async def create(scope: PlayerScope, command: RecordCreate) -> Effect:
    row = await records.create_record(await scope.context("military_create"), command.kind, command.values)
    kind = records.kind_of(command.kind)
    scope_id = getattr(row, kind.scope) if kind.scope is not None else None
    return Effect(f"A new {kind.label.lower()} is set down.", scope_id if isinstance(scope_id, int) else None)


@player_action("military:edit", ActionKind.EDIT_RECORD)
async def edit(scope: PlayerScope, command: RecordEdit) -> Effect:
    row = await records.edit_record(await scope.context("military_edit"), command.kind, command.record_id, command.values, hold=command.hold)
    kind = records.kind_of(command.kind)
    held = " and held" if command.hold and hasattr(row, "locked") else ""
    scope_id = getattr(row, kind.scope) if kind.scope is not None else None
    return Effect(f"The {kind.label.lower()} is changed{held}.", scope_id if isinstance(scope_id, int) else None)


@player_action("military:release", ActionKind.EDIT_RECORD)
async def release(scope: PlayerScope, command: RecordRelease) -> Effect:
    row = await records.release_record(await scope.context("military_release"), command.kind, command.record_id, command.columns)
    kind = records.kind_of(command.kind)
    scope_id = getattr(row, kind.scope) if kind.scope is not None else None
    return Effect(f"The world may change the {kind.label.lower()} again.", scope_id if isinstance(scope_id, int) else None)


@player_action("military:delete", ActionKind.EDIT_RECORD)
async def delete(scope: PlayerScope, command: RecordDelete) -> Effect:
    scope_id = await records.delete_record(await scope.context("military_delete"), command.kind, command.record_id)
    return Effect(f"The {records.kind_of(command.kind).label.lower()} is struck out.", scope_id)


@player_action("army:raise", ActionKind.EDIT_RECORD)
async def raise_army(scope: PlayerScope, command: RaiseArmy) -> Effect:
    ctx = await scope.context("army_raise")
    army = await orders.raise_standing_army(
        ctx, command.community_id, command.size, commander_id=command.commander_id, war_id=command.war_id, name=command.name
    )
    return Effect(f"{army.name} is raised.", army.id, created_ids=(army.id,))


@player_action("army:assign", ActionKind.EDIT_RECORD)
async def assign(scope: PlayerScope, command: ArmyCommand) -> Effect:
    row = await orders.set_commander(await scope.context("army_assign"), command.army_id, command.commander_id, command.owner_id)
    return Effect("The army has new leadership." if row.commander_entity_id is not None else "The army marches without a commander.", command.army_id)


@player_action("war:battle_at", ActionKind.EDIT_RECORD)
async def battle_at(scope: PlayerScope, command: BattleAt) -> Effect:
    report = await force_battle(await scope.context("battle_at"), command.war_id, command.region_id)
    return Effect(f"{report.summary}.", report.winner.id)


@player_action("siege:start", ActionKind.EDIT_RECORD)
async def siege_start(scope: PlayerScope, command: SiegeStart) -> Effect:
    siege = await orders.start_siege(await scope.context("siege_start"), command.war_id, command.army_id, command.settlement_id)
    return Effect("The siege lines are drawn.", siege.besieged_entity_id)


@player_action("war:declare", ActionKind.EDIT_RECORD)
async def declare(scope: PlayerScope, command: DeclareWar) -> Effect:
    ctx = await scope.context("war_declare")
    aims = [(aim.kind, dict(aim.params)) for aim in command.aims]
    war = await orders.declare_with_cause(ctx, command.attacker_id, command.defender_id, command.cause, reason=command.reason or "by decree", aims=aims)
    return Effect(f"War is declared: {command.cause.value.replace('_', ' ')}.", war.event_entity_id, created_ids=(war.event_entity_id,))


@player_action("war:peace", ActionKind.EDIT_RECORD)
async def peace(scope: PlayerScope, command: PeaceBuild) -> Effect:
    terms = [(term.kind, dict(term.params)) for term in command.terms]
    settlement = await orders.build_peace(await scope.context("war_peace_build"), command.war_id, command.victor_id, terms)
    return Effect(f"Peace is made. {' '.join(settlement.notes)}".strip(), command.victor_id)


@player_action("vessel:create", ActionKind.EDIT_RECORD)
async def vessel_create(scope: PlayerScope, command: VesselOrder) -> Effect:
    order = Commission(
        hull=command.hull_class,
        armament=command.armament,
        hull_material=command.hull_material,
        fabric_material=command.fabric_material,
        home_port_id=command.home_port_id,
        captain_id=command.captain_id,
        crew=command.crew,
    )
    vessel = await orders.create_vessel(await scope.context("vessel_create"), command.owner_id, command.name, order)
    return Effect(f"{vessel.name} is laid down.", vessel.id, created_ids=(vessel.id,))


@player_action("vessel:refit", ActionKind.EDIT_RECORD)
async def vessel_refit(scope: PlayerScope, command: VesselRefit) -> Effect:
    ctx = await scope.context("vessel_refit")
    vessel = await living_entity(ctx.session, command.vessel_id)
    if vessel is None:
        return Effect("No such vessel afloat.", command.vessel_id)
    order = Commission(hull=command.hull_class, armament=command.armament, hull_material=command.hull_material, fabric_material=command.fabric_material)
    await commission(ctx.session, ctx.rules, vessel, order)
    return Effect(f"{vessel.name} is refitted as a {command.hull_class.value.replace('_', ' ')}.", vessel.id)


@player_action("vessel:repair", ActionKind.EDIT_RECORD)
async def vessel_repair(scope: PlayerScope, command: VesselTarget) -> Effect:
    gain = await orders.repair_vessel(await scope.context("vessel_repair"), command.vessel_id)
    return Effect(f"The shipwrights restored {gain} points of the hull.", command.vessel_id)


@player_action("captive:take", ActionKind.EDIT_RECORD)
async def captive_take(scope: PlayerScope, command: CaptiveTake) -> Effect:
    row = await orders.take_named_captive(await scope.context("captive_take"), command.captor_id, command.mortal_id, command.war_id)
    return Effect("The prisoner is led away.", row.captive_entity_id)


@player_action("war:ordeal", ActionKind.EDIT_RECORD)
async def ordeal(scope: PlayerScope, command: Ordeal) -> Effect:
    ctx = await scope.context("ordeal")
    first, second = await living_entity(ctx.session, command.first_id), await living_entity(ctx.session, command.second_id)
    if first is None or second is None or command.context not in DUEL_CONTEXTS:
        return Effect("A duel needs two living fighters.", command.first_id)
    theatre = await Theatre.load(ctx)
    text = (await duel(ctx, theatre, first, second, war=None, anchor_id=None, context=command.context)).strip()
    return Effect(text, first.id)
